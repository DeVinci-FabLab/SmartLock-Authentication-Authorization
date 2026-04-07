import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv

# Force Python à inclure la racine du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

# Charger le fichier .env
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from src.core.keycloak_admin import (  # noqa: E402
    find_user_by_card_id,
    get_admin_token,
    get_user,
    get_user_effective_roles,
    get_user_groups,
    list_groups,
    list_users,
)


async def run_tests():
    print("Demarrage des tests de LECTURE Keycloak...\n")

    # --- TEST 1 : Récupération du token Admin ---
    print("TEST 1 : get_admin_token()")
    try:
        await get_admin_token()
        print("  Succes ! Token obtenu.")
    except Exception as e:
        print(f"  Echec : {e}")
        return

    # --- TEST 2 : Liste de tous les utilisateurs ---
    print("\nTEST 2 : list_users()")
    first_user_id = None
    try:
        users = await list_users(max_results=5)
        print(f"  Succes ! {len(users)} utilisateur(s).")
        if users:
            first_user_id = users[0]["id"]
            print(
                f"  Premier : {users[0].get('username')}"
            )
    except Exception as e:
        print(f"  Echec : {e}")

    # Tests nécessitant un ID utilisateur existant
    if first_user_id:
        # --- TEST 3 : Détails d'un utilisateur ---
        print(f"\nTEST 3 : get_user({first_user_id})")
        try:
            user_details = await get_user(first_user_id)
            first = user_details.get("firstName", "")
            last = user_details.get("lastName", "")
            print(f"  Succes ! Nom : {first} {last}")
        except Exception as e:
            print(f"  Echec : {e}")

        # --- TEST 4 : Groupes de l'utilisateur ---
        print(
            f"\nTEST 4 : get_user_groups({first_user_id})"
        )
        try:
            user_groups = await get_user_groups(first_user_id)
            noms = [g["name"] for g in user_groups]
            print(
                f"  Succes ! Groupes : {noms or 'Aucun'}"
            )
        except Exception as e:
            print(f"  Echec : {e}")

        # --- TEST 5 : Rôles effectifs ---
        print(
            f"\nTEST 5 : get_user_effective_roles"
            f"({first_user_id})"
        )
        try:
            roles = await get_user_effective_roles(
                first_user_id
            )
            print(f"  Succes ! Roles : {roles}")
        except Exception as e:
            print(f"  Echec : {e}")
    else:
        print(
            "\nTESTS 3, 4, 5 ignores :"
            " Aucun utilisateur dans Keycloak."
        )

    # --- TEST 6 : Arborescence des groupes ---
    print("\nTEST 6 : list_groups()")
    try:
        groups = await list_groups()
        print(f"  Succes ! {len(groups)} groupe(s).")
        if groups:
            print(f"  Exemple : {groups[0].get('name')}")
    except Exception as e:
        print(f"  Echec : {e}")

    # --- TEST 7 : Recherche par Card ID ---
    fake_card_id = "04:AB:CD:12:34:56:78"
    print(
        f"\nTEST 7 : find_user_by_card_id('{fake_card_id}')"
    )
    try:
        user = await find_user_by_card_id(fake_card_id)
        if user:
            print(
                f"  Succes (Inattendu) !"
                f" Utilisateur : {user.get('username')}"
            )
        else:
            print(
                "  Succes ! Aucun utilisateur"
                " (Normal pour un faux badge)."
            )
    except Exception as e:
        print(f"  Echec : {e}")

    print("\nFin de l'audit Keycloak.")


if __name__ == "__main__":
    asyncio.run(run_tests())
