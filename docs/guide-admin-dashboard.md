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

Les permissions definissent quel role peut acceder a quel casier. Chaque permission est **par role uniquement** (plus de surcharge par utilisateur individuel).

Trois niveaux disponibles, ordonnes par privilege croissant :

| `permission_level` | Acces physique | Peut modifier le contenu |
|---|---|---|
| `can_view` | Non | Non |
| `can_open` | **Oui** | Non |
| `can_edit` | **Oui** | Oui |

```javascript
// Voir les permissions d'un casier
const perms = await api("GET", `/lockers/${lockerId}/permissions`);
// => [{ id, locker_id, role_name, permission_level, valid_until, created_at }]

// Ajouter une permission
await api("POST", `/lockers/${lockerId}/permissions`, {
  locker_id: lockerId,
  role_name: "bureau",
  permission_level: "can_open",
  valid_until: "2025-12-31T23:59:59", // optionnel — acces temporaire
});

// Modifier le niveau d'acces
await api("PUT", `/lockers/permissions/${permId}`, {
  permission_level: "can_edit",
});

// Supprimer
await api("DELETE", `/lockers/permissions/${permId}`);
```

Le champ `(locker_id, role_name)` est unique : un role ne peut avoir qu'une seule entree par casier. Pour changer le niveau, utiliser PUT.

### Logique de resolution des permissions

Lors d'un scan de badge (`POST /auth/locker/{id}/check`), le systeme :

1. Identifie l'utilisateur via le `card_id` dans Keycloak
2. Recupere ses roles Keycloak
3. Prend le `permission_level` **le plus eleve** parmi tous ses roles (hierarchie : `can_view` < `can_open` < `can_edit`)
4. L'acces physique est autorise si le niveau effectif est `can_open` ou `can_edit`

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

## 9. Utilisateurs et groupes

### Lecture

```javascript
// Lister les utilisateurs (pagination)
const users = await api("GET", "/users?max_results=50");

// Rechercher un utilisateur par nom / email
const results = await api("GET", "/users?search=alice");

// Detail d'un utilisateur
const user = await api("GET", "/users/keycloak-uuid");

// Roles actuels d'un utilisateur
const roles = await api("GET", "/users/keycloak-uuid/roles");
// => ["membre", "bureau"]

// Lister les groupes
const groups = await api("GET", "/groups");
```

### Cycle de vie (revocation / suppression)

Ces actions modifient le compte Keycloak directement via l'API :

```javascript
// Revoquer un compte (desactiver — l'utilisateur ne peut plus s'authentifier)
// Requis : role lifecycle_manager (codir, presidence, admin)
await api("POST", `/users/${userId}/revoke`);

// Restaurer un compte revoqu
// Requis : role lifecycle_manager
await api("POST", `/users/${userId}/restore`);

// Supprimer definitivement un compte (irreversible)
// Requis : role lifecycle_admin (presidence, admin uniquement)
await api("DELETE", `/users/${userId}`);
```

| Action | Role requis | Reversible |
|---|---|---|
| revoke | `codir`, `presidence` ou `admin` | Oui (via restore) |
| restore | `codir`, `presidence` ou `admin` | — |
| delete | `presidence` ou `admin` | **Non** |

Un utilisateur revoqu verrait son badge refus avec la raison `account_revoked` a la borne physique.

Pour la creation de comptes et l'assignation de badges : utiliser l'interface d'administration Keycloak directement.

---

## 10. Gestion des roles

Les roles controlent qui peut acceder a quoi et qui peut gerer d'autres utilisateurs. Il existe des **roles systeme** (non supprimables, seedes en base) et des **roles custom** crees par les admins.

### Roles systeme

| Nom | Tier | is_manager | is_role_admin | Capacites |
|---|---|---|---|---|
| `admin` | T5 | oui | oui | create_lockers, configure_system, audit_log_full |
| `presidence` | T4 | oui | oui | audit_log_full, cascade_delete_role |
| `codir` | T3 | oui | oui | audit_log_full |
| `tresorerie` | T3 | non | non | purchase_orders, manage_suppliers |
| `bureau` | T2 | oui | non | — |
| `membre` | T0 | non | non | — |

### Lister les roles

```javascript
// Accessible a tout utilisateur authentifie
const roles = await api("GET", "/roles");
// => [{ id, name, label, tier, is_system, is_manager, is_role_admin, capacities }]
```

### Creer un role custom

Requis : `is_role_admin=true` dans le token. Le tier du nouveau role ne peut pas depasser le tier du createur.

```javascript
const newRole = await api("POST", "/roles", {
  name: "agent_fdm",
  label: "Agent FDM",
  tier: 1,
  is_manager: false,
  is_role_admin: false,
  capacities: [],
});
// => 201 Created + objet RoleResponse
```

Capacites disponibles : `create_lockers`, `configure_system`, `audit_log_full`, `purchase_orders`, `manage_suppliers`, `cascade_delete_role`, `validate_catalog`, `manage_stock_thresholds`.

### Modifier un role

```javascript
// Pour les roles custom : label, is_manager, is_role_admin, capacities
// Pour les roles systeme : label uniquement
await api("PUT", `/roles/${roleName}`, {
  label: "Agent Impression 3D",
  is_manager: true,
});
```

### Supprimer un role custom

```javascript
// Echoue avec 409 si des utilisateurs ont encore ce role (sauf cascade=true)
await api("DELETE", `/roles/${roleName}`);

// Cascade : retire le role de tous les utilisateurs avant suppression
// Requis : presidence ou admin
await api("DELETE", `/roles/${roleName}?cascade=true`);
```

Erreurs possibles :

| Code | Detail | Signification |
|---|---|---|
| `403` | `system_role_not_deletable` | Impossible de supprimer un role systeme |
| `409` | `role_in_use` | Des utilisateurs ont encore ce role — utiliser `?cascade=true` |
| `403` | `self_destruction_forbidden` | L'appelant ne peut pas supprimer son seul role `is_role_admin` |

---

## 11. Attribution des roles aux utilisateurs

L'attribution d'un role a un utilisateur suit la **hierarchie de tier** : l'appelant doit avoir `is_manager=true` ET un tier **strictement superieur** a celui du role cible (exception : T5 peut gerer T5).

```javascript
// Attribuer un role
// => 204 No Content (idempotent : si l'utilisateur a deja le role, no-op silencieux)
await api("POST", `/users/${userId}/roles/${roleName}`);

// Revoquer un role
// => 204 No Content
await api("DELETE", `/users/${userId}/roles/${roleName}`);
```

Exemples de controles d'acces :

| Appelant | Role cible | Resultat |
|---|---|---|
| `admin` (T5, is_manager) | `codir` (T3) | Autorise |
| `codir` (T3, is_manager) | `bureau` (T2) | Autorise |
| `codir` (T3, is_manager) | `tresorerie` (T3) | **Refuse** — meme tier |
| `bureau` (T2, is_manager) | `membre` (T0) | Autorise |
| `membre` (T0, pas is_manager) | n'importe quel role | **Refuse** |

---

## 12. Gestion des erreurs

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
