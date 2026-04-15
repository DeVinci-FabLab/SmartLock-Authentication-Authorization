"""
Seed script — inserts realistic test data into the SmartLock database.
Run from the project root after `docker compose up -d`:

    python scripts/seed.py

The script is idempotent: it skips rows that already exist.
By default it connects to localhost:5432 (the mapped Docker port).
Override with: DATABASE_URL=... python scripts/seed.py
"""

import os
import sys
from pathlib import Path

# Allow running from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ── Connection ────────────────────────────────────────────────────────────────
# Default: hit the Docker container from the host.
# Change POSTGRES_* vars or override DATABASE_URL entirely.
POSTGRES_USER = os.getenv("POSTGRES_USER", "username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "smartlock")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}",
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


# ── Helpers ───────────────────────────────────────────────────────────────────
def upsert_locker(db, locker_type: str, is_active: bool = True):
    row = db.execute(
        text("SELECT id FROM lockers WHERE locker_type = :t"),
        {"t": locker_type},
    ).fetchone()
    if row:
        print(f"  [skip] locker '{locker_type}' already exists (id={row[0]})")
        return row[0]
    result = db.execute(
        text(
            "INSERT INTO lockers (locker_type, is_active) VALUES (:t, :a) RETURNING id"
        ),
        {"t": locker_type, "a": is_active},
    )
    db.commit()
    lid = result.fetchone()[0]
    print(f"  [ok]   locker '{locker_type}' created (id={lid})")
    return lid


def upsert_category(db, name: str):
    row = db.execute(
        text("SELECT id FROM categories WHERE name = :n"), {"n": name}
    ).fetchone()
    if row:
        print(f"  [skip] category '{name}' already exists (id={row[0]})")
        return row[0]
    result = db.execute(
        text("INSERT INTO categories (name) VALUES (:n) RETURNING id"), {"n": name}
    )
    db.commit()
    cid = result.fetchone()[0]
    print(f"  [ok]   category '{name}' created (id={cid})")
    return cid


def upsert_item(db, name: str, reference: str, description: str, category_id: int):
    row = db.execute(
        text("SELECT id FROM items WHERE reference = :r"), {"r": reference}
    ).fetchone()
    if row:
        print(f"  [skip] item '{reference}' already exists (id={row[0]})")
        return row[0]
    result = db.execute(
        text(
            "INSERT INTO items (name, reference, description, category_id)"
            " VALUES (:n, :r, :d, :c) RETURNING id"
        ),
        {"n": name, "r": reference, "d": description, "c": category_id},
    )
    db.commit()
    iid = result.fetchone()[0]
    print(f"  [ok]   item '{name}' ({reference}) created (id={iid})")
    return iid


def upsert_stock(db, item_id: int, locker_id: int, quantity: int, unit: str = "pcs"):
    row = db.execute(
        text(
            "SELECT id FROM stock WHERE item_id = :i AND locker_id = :l"
        ),
        {"i": item_id, "l": locker_id},
    ).fetchone()
    if row:
        print(
            f"  [skip] stock item_id={item_id} locker_id={locker_id} already exists"
        )
        return row[0]
    result = db.execute(
        text(
            "INSERT INTO stock (item_id, locker_id, quantity, unit_measure)"
            " VALUES (:i, :l, :q, :u) RETURNING id"
        ),
        {"i": item_id, "l": locker_id, "q": quantity, "u": unit},
    )
    db.commit()
    sid = result.fetchone()[0]
    print(
        f"  [ok]   stock item_id={item_id} × {quantity} {unit} in locker {locker_id} (id={sid})"
    )
    return sid


def upsert_permission(
    db,
    locker_id: int,
    subject_type: str,
    role_name: str | None,
    user_id: str | None,
    can_view=False,
    can_open=False,
    can_edit=False,
    can_take=False,
    can_manage=False,
):
    row = db.execute(
        text(
            "SELECT id FROM locker_permissions"
            " WHERE locker_id = :l AND role_name IS NOT DISTINCT FROM :r"
            " AND user_id IS NOT DISTINCT FROM :u"
        ),
        {"l": locker_id, "r": role_name, "u": user_id},
    ).fetchone()
    target = role_name or user_id
    if row:
        print(
            f"  [skip] permission locker={locker_id} target='{target}' already exists"
        )
        return row[0]
    result = db.execute(
        text(
            "INSERT INTO locker_permissions"
            " (locker_id, subject_type, role_name, user_id,"
            "  can_view, can_open, can_edit, can_take, can_manage)"
            " VALUES (:l, :st, :rn, :ui, :cv, :co, :ce, :ct, :cm)"
            " RETURNING id"
        ),
        {
            "l": locker_id,
            "st": subject_type,
            "rn": role_name,
            "ui": user_id,
            "cv": can_view,
            "co": can_open,
            "ce": can_edit,
            "ct": can_take,
            "cm": can_manage,
        },
    )
    db.commit()
    pid = result.fetchone()[0]
    print(
        f"  [ok]   permission locker={locker_id} '{target}'"
        f" view={can_view} open={can_open} edit={can_edit} take={can_take} manage={can_manage}"
        f" (id={pid})"
    )
    return pid


# ── Seed ──────────────────────────────────────────────────────────────────────
def seed():
    db = Session()
    try:
        # -- Verify connection --
        db.execute(text("SELECT 1"))
        print(f"\nConnected to: {DATABASE_URL.split('@')[-1]}\n")

        # ── Lockers ───────────────────────────────────────────────────────────
        print("=== Lockers ===")
        l1 = upsert_locker(db, "standard")
        l2 = upsert_locker(db, "grande")
        l3 = upsert_locker(db, "sécurisée")
        l4 = upsert_locker(db, "atelier", is_active=False)

        # ── Categories ────────────────────────────────────────────────────────
        print("\n=== Categories ===")
        c_elec = upsert_category(db, "Électronique")
        c_meca = upsert_category(db, "Mécanique")
        c_outi = upsert_category(db, "Outillage")

        # ── Items ─────────────────────────────────────────────────────────────
        print("\n=== Items ===")
        # Électronique
        i_ard = upsert_item(db, "Arduino Uno R3", "REF-ARD-001", "Carte microcontrôleur ATmega328P", c_elec)
        i_rpi = upsert_item(db, "Raspberry Pi 4 (4GB)", "REF-RPI-004", "Ordinateur monocarte 4GB RAM", c_elec)
        i_cbl = upsert_item(db, "Câbles USB-C (lot 5)", "REF-CBL-001", "Câbles USB-C 1m de charge rapide", c_elec)
        i_esp = upsert_item(db, "ESP32 DevKit", "REF-ESP-032", "Module WiFi+BT pour IoT", c_elec)
        # Mécanique
        i_vis = upsert_item(db, "Vis M3 × 16mm", "REF-VIS-M3-16", "Vis à tête cylindrique M3 inox", c_meca)
        i_ecr = upsert_item(db, "Écrous M3 hexagonaux", "REF-ECR-M3", "Écrous hexagonaux M3 inox", c_meca)
        i_rlm = upsert_item(db, "Roulements 608ZZ", "REF-RLM-608", "Roulements à billes 8×22×7mm", c_meca)
        # Outillage
        i_trn = upsert_item(db, "Tournevis cruciforme PH2", "REF-TRN-PH2", "Tournevis Philips PH2 manche ergonomique", c_outi)
        i_mlt = upsert_item(db, "Multimètre numérique", "REF-MLT-001", "Multimètre True RMS 6000 points", c_outi)
        i_fer = upsert_item(db, "Fer à souder 60W", "REF-FER-060", "Station de soudage température réglable", c_outi)

        # ── Stock ─────────────────────────────────────────────────────────────
        print("\n=== Stock ===")
        # Casier standard (l1) — électronique + outillage commun
        upsert_stock(db, i_ard, l1, 5)
        upsert_stock(db, i_rpi, l1, 3)
        upsert_stock(db, i_esp, l1, 8)
        upsert_stock(db, i_trn, l1, 4)
        # Grande armoire (l2) — consommables
        upsert_stock(db, i_cbl, l2, 20)
        upsert_stock(db, i_vis, l2, 200, "pcs")
        upsert_stock(db, i_ecr, l2, 200, "pcs")
        # Armoire sécurisée (l3) — matériel de valeur
        upsert_stock(db, i_rlm, l3, 12)
        upsert_stock(db, i_mlt, l3, 2)
        upsert_stock(db, i_fer, l3, 1)

        # ── Locker Permissions (role-based) ───────────────────────────────────
        print("\n=== Locker Permissions ===")

        # Casier standard (l1): membre peut voir, codir peut ouvrir/prendre, admin tout
        upsert_permission(db, l1, "role", "membre",      None, can_view=True)
        upsert_permission(db, l1, "role", "materialiste", None, can_view=True, can_open=True, can_take=True)
        upsert_permission(db, l1, "role", "codir",       None, can_view=True, can_open=True, can_take=True, can_edit=True)
        upsert_permission(db, l1, "role", "admin",       None, can_view=True, can_open=True, can_edit=True, can_take=True, can_manage=True)

        # Grande armoire (l2): membre peut voir, materialiste peut gérer
        upsert_permission(db, l2, "role", "membre",      None, can_view=True)
        upsert_permission(db, l2, "role", "materialiste", None, can_view=True, can_open=True, can_take=True, can_edit=True)
        upsert_permission(db, l2, "role", "codir",       None, can_view=True, can_open=True, can_take=True, can_edit=True)
        upsert_permission(db, l2, "role", "admin",       None, can_view=True, can_open=True, can_edit=True, can_take=True, can_manage=True)

        # Armoire sécurisée (l3): codir+ seulement
        upsert_permission(db, l3, "role", "codir",       None, can_view=True, can_open=True, can_manage=True)
        upsert_permission(db, l3, "role", "admin",       None, can_view=True, can_open=True, can_edit=True, can_take=True, can_manage=True)

        print("\n✅ Seed complete.\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seed failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
