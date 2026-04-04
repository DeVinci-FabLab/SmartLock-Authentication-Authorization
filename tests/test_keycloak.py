import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Force Python à inclure la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

# Charger le fichier .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from src.core.keycloak_admin import (
    get_admin_token,
    list_users,
    get_user,
    get_user_groups,
    get_user_effective_roles,
    list_groups,
    find_user_by_card_id,
)

async def run_tests():
    print("🚀 Démarrage des tests de LECTURE (Read-Only) Keycloak...\n")

    # --- TEST 1 : Récupération du token Admin ---
    print("🟢 TEST 1 : get_admin_token()")
    try:
        token = await get_admin_token()
        print(f"  ✅ Succès ! Token obtenu.")
    except Exception as e:
        print(f"  ❌ Échec : {e}")
        return

    # --- TEST 2 : Liste de tous les utilisateurs ---
    print("\n🟢 TEST 2 : list_users()")
    first_user_id = None
    try:
        users = await list_users(max_results=5) # On limite à 5 pour le test
        print(f"  ✅ Succès ! {len(users)} utilisateur(s) récupéré(s).")
        if users:
            first_user_id = users[0]["id"]
            print(f"  👤 Premier de la liste : {users[0].get('username')}")
    except Exception as e:
        print(f"  ❌ Échec : {e}")

    # Tests nécessitant un ID utilisateur existant
    if first_user_id:
        # --- TEST 3 : Détails d'un utilisateur ---
        print(f"\n🟢 TEST 3 : get_user({first_user_id})")
        try:
            user_details = await get_user(first_user_id)
            print(f"  ✅ Succès ! Nom complet : {user_details.get('firstName', '')} {user_details.get('lastName', '')}")
        except Exception as e:
            print(f"  ❌ Échec : {e}")

        # --- TEST 4 : Groupes de l'utilisateur ---
        print(f"\n🟢 TEST 4 : get_user_groups({first_user_id})")
        try:
            user_groups = await get_user_groups(first_user_id)
            noms_groupes = [g["name"] for g in user_groups]
            print(f"  ✅ Succès ! Appartient aux groupes : {noms_groupes if noms_groupes else 'Aucun'}")
        except Exception as e:
            print(f"  ❌ Échec : {e}")

        # --- TEST 5 : Rôles effectifs de l'utilisateur ---
        print(f"\n🟢 TEST 5 : get_user_effective_roles({first_user_id})")
        try:
            roles = await get_user_effective_roles(first_user_id)
            print(f"  ✅ Succès ! Rôles finaux : {roles}")
        except Exception as e:
            print(f"  ❌ Échec : {e}")
    else:
        print("\n🟡 TESTS 3, 4 et 5 ignorés : Aucun utilisateur trouvé dans Keycloak.")

    # --- TEST 6 : Arborescence de tous les groupes ---
    print("\n🟢 TEST 6 : list_groups()")
    try:
        groups = await list_groups()
        print(f"  ✅ Succès ! {len(groups)} groupe(s) parent(s) au total.")
        if groups:
            print(f"  📁 Exemple : {groups[0].get('name')}")
    except Exception as e:
        print(f"  ❌ Échec : {e}")

    # --- TEST 7 : Recherche par Card ID ---
    fake_card_id = "04:AB:CD:12:34:56:78"
    print(f"\n🟢 TEST 7 : find_user_by_card_id('{fake_card_id}')")
    try:
        user = await find_user_by_card_id(fake_card_id)
        if user:
            print(f"  ✅ Succès (Inattendu) ! Utilisateur trouvé : {user.get('username')}")
        else:
            print(f"  ✅ Succès ! Recherche effectuée, aucun utilisateur (Normal pour un faux badge).")
    except Exception as e:
        print(f"  ❌ Échec : {e}")

    print("\n🏁 Fin de l'audit Keycloak.")

if __name__ == "__main__":
    asyncio.run(run_tests())