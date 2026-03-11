# Keycloak Service Account Test Guide

Test that the API can authenticate as a service account and retrieve a user's `card_id` and roles.

**Assumptions:** Keycloak is running, you can reach the admin console, and the `master` realm already exists. You have the initial admin account.

---

## 1. Create Realm Roles

Navigate to the `master` realm (top-left dropdown).

Left menu → **Realm roles** → **Create role**

Create these two roles (one at a time):

| Nom du rôle      | Description                          |
| ---------------- | ------------------------------------ |
| `membre`         | Rôle de base pour tous les adhérents |
| `membre-atelier` | Accès aux casiers de l'atelier bois  |

Steps for each:

1. Role name → fill in → **Save**
2. No further config needed

---

## 2. Create Groups

Keycloak supports child groups that **inherit roles from their parent**. Use this instead of manually assigning base roles to every sub-group.

Structure to create:

```plain
Adhérents          (rôle : membre)
└── Atelier        (rôle : membre-atelier)
```

A user added to `Atelier` automatically gets `membre` (from the parent) + `membre-atelier` (from the child). Adding new workshops later only requires assigning their specific role — `membre` propagates for free.

### Create the parent group

Left menu → **Groups** → **Create group**

- Name: `Adhérents` → **Create**
- Click `Adhérents` → **Role mapping** tab → **Assign role** → select `membre` → **Assign**

### Create the child group

- Click `Adhérents` → **Sub groups** tab → **Create group**
- Name: `Atelier` → **Create**
- Click `Atelier` → **Role mapping** tab → **Assign role** → select `membre-atelier` → **Assign**

> Do **not** assign `membre` to `Atelier` — it is inherited from `Adhérents` automatically.

---

## 3. Add the `card_id` User Attribute

Left menu → **Realm settings** → **User profile** tab → **Create attribute**

- Attribute name: `card_id`
- Display name: `Card ID`
- Leave everything else as default
- **Save**

> This makes `card_id` a proper user profile field that appears in the admin UI and is searchable via the Admin REST API.

---

## 4. Create a Test User

Left menu → **Users** → **Create new user**

Fill in:

- Username: `alice`
- Email: `alice@fablab.local`
- First name: `Alice`
- **Create**

Then on the user page:

### Set a password

- **Credentials** tab → **Set password**
- Password: `test1234` (or anything)
- Temporary: **Off**
- **Save**

### Set the card_id attribute

- **Attributes** tab
- Key: `card_id` / Value: `04:AB:CD:12:34:56:78`
- **Save**

### Add to group

- **Groups** tab → **Join Group**
- Select `Atelier` → **Join**

---

## 5. Create the `smartlock-api` Client

This is the service account the Python code will use to query Keycloak.

Left menu → **Clients** → **Create client**

### Step 1 — General settings

- Client type: `OpenID Connect`
- Client ID: `smartlock-api`
- **Next**

### Step 2 — Capability config

- Client authentication: **On** (makes it confidential)
- Authentication flow: uncheck everything **except** `Service accounts roles`
- **Next → Save**

### Get the client secret

- **Credentials** tab → copy the `Client secret` value — you'll need it in the Python script

### Assign Admin API permissions to the service account

- **Service account roles** tab → **Assign role**
- Filter by: `Filter by clients` → search `realm-management`
- Select these roles:
  - `query-users`
  - `view-users`
  - `query-groups`
  - `view-realm`
- **Assign**

---

## 6. Python Test Script

The script lives at `sandbox/test_keycloak.py`.

### Dependencies and .env file

Install dependencies:

```bash
pip install httpx python-dotenv
```

Create `sandbox/.env`:

```bash
cd sandbox
cp .env.example .env
```

The script tests two card IDs in sequence: one registered (should find alice) and one unknown (should return denied).

### Run it

```bash
python test_keycloak.py
```

### Expected output

```plain
[1] Token obtenu (40 premiers caractères) : eyJhbGciOiJSUzI1NiIsInR5cCIgOi...

──────────────────────────────────────────────────
Recherche du card_id : 04:AB:CD:12:34:56:78
──────────────────────────────────────────────────
[2] Utilisateur trouvé : id=<uuid>  username=alice
    card_id : ['04:AB:CD:12:34:56:78']
[3] Rôles effectifs : ['default-roles-master', 'membre', 'membre-atelier']
[4] Groupes : ['Adhérents/Atelier']

── Résultat ────────────────────────────
  Utilisateur : Alice  (alice)
  Rôles       : ['default-roles-master', 'membre', 'membre-atelier']
  Groupes     : ['Adhérents/Atelier']
  Permissions (simulation casier 1) : {'can_open': True, 'can_view': True, 'can_take': True}

──────────────────────────────────────────────────
Recherche du card_id : FF:FF:FF:FF:FF:FF:FF
──────────────────────────────────────────────────
[2] Aucun utilisateur trouvé avec card_id=FF:FF:FF:FF:FF:FF:FF
Résultat : carte non enregistrée — accès refusé
```

---

## 7. Common Errors

| Erreur                                        | Cause                                               | Correction                                                                    |
| --------------------------------------------- | --------------------------------------------------- | ----------------------------------------------------------------------------- |
| `401 Unauthorized` on token request           | Wrong `CLIENT_SECRET`                               | Re-copy from Clients → smartlock-api → Credentials tab                        |
| `403 Forbidden` on Admin API call             | Service account missing roles                       | Re-check step 5 — Service account roles tab                                   |
| Empty `[]` on user search                     | `card_id` attribute not searchable                  | Re-check step 3 — attribute must be saved in User Profile                     |
| Empty `[]` on user search                     | Value has whitespace or wrong case                  | Copy the exact string set in step 4                                           |
| `400 Bad Request` on token                    | `Service accounts roles` not enabled on client      | Re-check step 5 capability config                                             |
| Roles list only has `default-roles-master`    | User not in a group, or group has no roles assigned | Re-check steps 2 and 4                                                        |
| `membre` missing but `membre-atelier` present | Used `/realm` instead of `/realm/composite`         | The script uses `/composite` — double-check the URL in `get_user_realm_roles` |
