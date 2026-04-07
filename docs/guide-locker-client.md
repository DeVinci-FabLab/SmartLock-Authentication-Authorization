# Guide Frontend - Client Armoire (Raspberry Pi)

Ce guide explique comment integrer le Raspberry Pi (terminal physique d'un casier) avec l'API SmartLock.

## Architecture

```
[Badge NFC] --> [Module NFC] --> POST /badge/scan     (enregistrement)
[Badge NFC] --> [Raspberry Pi] --> POST /auth/locker/{id}/check  (ouverture)
```

Le Raspberry Pi utilise un **service account Keycloak** (`smartlock-lockers`) pour s'authentifier. Il n'a acces qu'a un seul endpoint : la verification d'acces.

Le module NFC (borne d'accueil) utilise un autre service account (`nfc-scanner`) pour enregistrer les nouveaux badges.

---

## 1. Configuration

Variables d'environnement necessaires sur le Raspberry Pi :

```env
API_URL=http://<serveur>:8000
KEYCLOAK_URL=https://auth.devinci-fablab.fr
KEYCLOAK_REALM=master
LOCKER_CLIENT_SECRET=<secret du client smartlock-lockers>
LOCKER_ID=1
```

---

## 2. Obtenir un token d'acces

Le Raspberry Pi obtient un token via le grant `client_credentials` :

```python
import httpx

async def get_locker_token() -> str:
    token_url = (
        f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
        "/protocol/openid-connect/token"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data={
            "grant_type": "client_credentials",
            "client_id": "smartlock-lockers",
            "client_secret": LOCKER_CLIENT_SECRET,
        })
        resp.raise_for_status()
        return resp.json()["access_token"]
```

Le token a une duree de vie limitee (par defaut 5 minutes). Il faut le renouveler avant expiration.

### Gestion du renouvellement

```python
import time
from jose import jwt

class TokenManager:
    def __init__(self):
        self._token = None
        self._expiry = 0

    async def get_token(self) -> str:
        if time.time() > self._expiry - 30:  # 30s de marge
            self._token = await get_locker_token()
            payload = jwt.get_unverified_claims(self._token)
            self._expiry = payload.get("exp", 0)
        return self._token

token_manager = TokenManager()
```

---

## 3. Verifier l'acces d'un badge

C'est l'endpoint principal utilise par le Raspberry Pi. Quand un badge NFC est scanne, le Pi envoie le `card_id` a l'API :

```python
async def check_access(card_id: str) -> dict:
    token = await token_manager.get_token()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/auth/locker/{LOCKER_ID}/check",
            headers={"Authorization": f"Bearer {token}"},
            json={"card_id": card_id},
        )
        resp.raise_for_status()
        return resp.json()
```

### Reponse

```json
{
  "allowed": true,
  "display_name": "Alice Dupont",
  "reason": null,
  "permissions": {
    "can_view": true,
    "can_open": true,
    "can_edit": false,
    "can_take": false,
    "can_manage": false
  }
}
```

### Logique de decision

```python
result = await check_access(card_id)

if result["allowed"]:
    # Ouvrir le casier (activer le relais / servo)
    open_locker()
    display_message(f"Bienvenue {result['display_name']}")
else:
    # Afficher le refus
    reason = result.get("reason", "unknown")
    if reason == "card_not_registered":
        display_message("Badge inconnu")
    elif reason == "keycloak_error":
        display_message("Erreur serveur, reessayez")
    else:
        display_message("Acces refuse")
```

### Valeurs possibles de `reason` (quand `allowed: false`)

| Reason | Signification | Action suggeree |
|---|---|---|
| `card_not_registered` | Le badge n'est associe a aucun utilisateur Keycloak | Afficher "Badge inconnu" |
| `keycloak_error` | Erreur de communication avec Keycloak | Reessayer apres quelques secondes |
| `no_permission` | L'utilisateur n'a pas la permission `can_open` sur ce casier | Afficher "Acces refuse" |

---

## 4. Exemple complet (boucle principale)

```python
import asyncio
import httpx

API_URL = "http://192.168.1.100:8000"
LOCKER_ID = 1

async def main():
    while True:
        card_id = await read_nfc_card()  # Votre code NFC

        try:
            result = await check_access(card_id)
            if result["allowed"]:
                await open_locker()
                print(f"Ouvert pour {result['display_name']}")
            else:
                print(f"Refuse: {result.get('reason')}")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token expire, forcer le renouvellement
                token_manager._expiry = 0
            print(f"Erreur HTTP: {e.response.status_code}")
        except httpx.ConnectError:
            print("Serveur injoignable")

        await asyncio.sleep(0.5)

asyncio.run(main())
```

---

## 5. Module NFC (borne d'accueil)

Le module NFC de la borne d'accueil a un role different : il enregistre les nouveaux badges dans le systeme.

```python
async def scan_new_badge(card_id: str) -> dict:
    token = await get_nfc_token()  # client_id=nfc-scanner
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{API_URL}/badge/scan",
            headers={"Authorization": f"Bearer {token}"},
            json={"card_id": card_id},
        )
        if resp.status_code == 409:
            return {"status": "already_registered"}
        resp.raise_for_status()
        return resp.json()
```

Apres le scan, un administrateur doit :
1. Aller dans l'interface Keycloak
2. Trouver l'utilisateur correspondant
3. Ajouter le `card_id` dans les attributs de l'utilisateur
4. Marquer le badge comme assigne via `PATCH /badge/{card_id}/assign`
