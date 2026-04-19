# Guide Frontend - Dashboard Administrateur

Ce guide explique comment integrer le dashboard d'administration web avec l'API SmartLock.

## Architecture

```
[Admin Web App] --Bearer JWT--> [API SmartLock] ---> [PostgreSQL]
                                       |
                                       +--> [Keycloak] (users, groups, roles)
```

Le dashboard utilise un token utilisateur obtenu via le grant `password` (ou implicitement via un flux OIDC frontend). L'utilisateur doit avoir le role `admin` dans Keycloak.

---

## 1. Authentification

### Option A : Password grant (applications internes)

```javascript
async function login(username, password) {
  const resp = await fetch(
    `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "password",
        client_id: "smartlock-dashboard",
        username,
        password,
      }),
    }
  );
  const data = await resp.json();
  return {
    accessToken: data.access_token,
    refreshToken: data.refresh_token,
    expiresIn: data.expires_in,
  };
}
```

### Option B : Authorization Code Flow (recommande pour le web)

Utiliser une librairie OIDC comme `oidc-client-ts` ou `keycloak-js` :

```javascript
import Keycloak from "keycloak-js";

const keycloak = new Keycloak({
  url: KEYCLOAK_URL,
  realm: REALM,
  clientId: "smartlock-dashboard",
});

await keycloak.init({ onLoad: "login-required" });
const token = keycloak.token;
```

### Renouvellement du token

```javascript
async function refreshToken(refreshToken) {
  const resp = await fetch(
    `${KEYCLOAK_URL}/realms/${REALM}/protocol/openid-connect/token`,
    {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        client_id: "smartlock-dashboard",
        refresh_token: refreshToken,
      }),
    }
  );
  return await resp.json();
}
```

### Helper pour les appels API

```javascript
const API_URL = "https://api.smartlock.devinci-fablab.fr";

async function api(method, path, body = null) {
  const options = {
    method,
    headers: {
      Authorization: `Bearer ${getToken()}`,
      "Content-Type": "application/json",
    },
  };
  if (body) options.body = JSON.stringify(body);

  const resp = await fetch(`${API_URL}${path}`, options);
  if (resp.status === 401) {
    await refreshOrRedirectToLogin();
    return api(method, path, body); // retry
  }
  if (!resp.ok) {
    const err = await resp.json();
    throw new Error(err.detail || "Erreur API");
  }
  if (resp.status === 204) return null;
  return await resp.json();
}
```

---

## 2. Gestion des categories

```javascript
// Lister
const categories = await api("GET", "/categories/");

// Creer
const newCat = await api("POST", "/categories/", {
  name: "Electronique",
});

// Modifier
await api("PUT", `/categories/${id}`, { name: "Nouveau nom" });

// Supprimer
await api("DELETE", `/categories/${id}`);
```

---

## 3. Gestion des items (outils/materiels)

```javascript
// Lister (avec pagination)
const items = await api("GET", "/items/?skip=0&limit=50");

// Creer
const newItem = await api("POST", "/items/", {
  name: "Perceuse",
  reference: "P-01",
  description: "Perceuse sans fil",
  category_id: 1,
});

// Modifier
await api("PUT", `/items/${id}`, { name: "Perceuse Pro" });

// Supprimer
await api("DELETE", `/items/${id}`);
```

---

## 4. Gestion des casiers

```javascript
// Lister
const lockers = await api("GET", "/lockers/");

// Creer
const locker = await api("POST", "/lockers/", {
  locker_type: "standard",
  is_active: true,
});

// Voir le stock d'un casier
const stock = await api("GET", `/lockers/${id}/stock`);

// Desactiver un casier
await api("PUT", `/lockers/${id}`, { is_active: false });

// Supprimer (cascade: stock, permissions, logs)
await api("DELETE", `/lockers/${id}`);
```

---

## 5. Gestion du stock

```javascript
// Lister tout le stock
const allStock = await api("GET", "/stock/");

// Ajouter du stock
const entry = await api("POST", "/stock/", {
  item_id: 1,
  locker_id: 1,
  quantity: 10,
  unit_measure: "units",
});

// Mettre a jour la quantite
await api("PUT", `/stock/${id}`, { quantity: 8 });

// Supprimer
await api("DELETE", `/stock/${id}`);
```

**Note** : La combinaison `(item_id, locker_id)` doit etre unique. L'API retourne une erreur si un doublon existe.

---

## 6. Gestion des permissions de casier

Les permissions definissent qui peut acceder a quel casier. Il y a deux types :

- **role** : s'applique a tous les utilisateurs ayant ce role Keycloak
- **user** : s'applique a un utilisateur specifique (surcharge les permissions role)

```javascript
// Voir les permissions d'un casier
const perms = await api(
  "GET",
  `/lockers/${lockerId}/permissions`
);

// Ajouter une permission par role
await api("POST", `/lockers/${lockerId}/permissions`, {
  locker_id: lockerId,
  subject_type: "role",
  role_name: "3D",
  can_view: true,
  can_open: true,
  can_edit: false,
  can_take: true,
  can_manage: false,
  valid_until: "2025-12-31T23:59:59", // optionnel
});

// Ajouter une permission par utilisateur
await api("POST", `/lockers/${lockerId}/permissions`, {
  locker_id: lockerId,
  subject_type: "user",
  user_id: "keycloak-uuid-here",
  can_view: true,
  can_open: true,
});

// Modifier
await api("PUT", `/lockers/permissions/${permId}`, {
  can_open: false,
});

// Supprimer
await api("DELETE", `/lockers/permissions/${permId}`);
```

### Logique de resolution des permissions

Lors d'un scan de badge (`POST /auth/locker/{id}/check`), le systeme :

1. Identifie l'utilisateur via le `card_id` dans Keycloak
2. Recupere ses roles Keycloak
3. Consolide toutes les permissions **role** correspondantes (OR logique)
4. Si une permission **user** specifique existe, elle **remplace** les permissions role
5. L'acces est autorise si `can_open` est `true`

---

## 7. Workflow des badges NFC

### Etapes

1. Un badge inconnu est scanne par la borne NFC -> `POST /badge/scan` (automatique)
2. L'admin consulte les badges en attente -> `GET /badge/pending`
3. L'admin assigne le badge a un utilisateur dans **l'interface Keycloak** (attribut `card_id`)
4. L'admin marque le badge comme assigne -> `PATCH /badge/{card_id}/assign`

```javascript
// Voir les badges en attente
const pending = await api("GET", "/badge/pending");
// => [{ id: 1, card_id: "AA:BB:CC:11:22", scanned_at: "...", status: "pending" }]

// Apres assignation dans Keycloak, marquer comme assigne
await api("PATCH", `/badge/${cardId}/assign`);
```

---

## 8. Historique d'acces (Audit Logs)

Chaque tentative d'ouverture de casier est enregistree.

```javascript
// Tous les logs
const logs = await api("GET", "/logs/");

// Filtrer par casier
const lockerLogs = await api(
  "GET",
  `/logs/?locker_id=${lockerId}`
);

// Avec pagination
const page = await api(
  "GET",
  `/logs/?skip=0&limit=50&locker_id=${lockerId}`
);
```

Chaque log contient :
- `card_id` : le badge scanne
- `user_id` / `username` : l'utilisateur identifie (si connu)
- `result` : `"allowed"` ou `"denied"`
- `reason` : raison du refus (`card_not_registered`, `keycloak_error`, `no_permission`)
- `can_open` / `can_view` : snapshot des permissions au moment du scan
- `timestamp` : date/heure

---

## 9. Utilisateurs et groupes (lecture seule)

La gestion des utilisateurs et groupes se fait **exclusivement via l'interface Keycloak**. L'API expose uniquement des endpoints de lecture :

```javascript
// Lister les utilisateurs
const users = await api("GET", "/users?max_results=50");

// Rechercher un utilisateur
const results = await api("GET", "/users?search=alice");

// Lister les groupes
const groups = await api("GET", "/groups");
```

Pour modifier un utilisateur (role, groupe, badge) : utiliser l'interface d'administration Keycloak directement.

---

## 10. Gestion des erreurs

```javascript
try {
  await api("POST", "/items/", { name: "Test", reference: "T-01", category_id: 999 });
} catch (err) {
  // err.message = "Category not found" (404)
}
```

| Code | Signification |
|---|---|
| `401` | Token invalide ou expire -> re-authentifier |
| `403` | L'utilisateur n'a pas le role `admin` |
| `404` | Ressource non trouvee (ou FK inexistante) |
| `409` | Conflit (badge deja enregistre, stock doublon) |
| `500` | Erreur serveur |
