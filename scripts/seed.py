"""
Seed script — inserts realistic data into the SmartLock database.
Run from the project root after `docker compose up -d`:

    python scripts/seed.py

The script is idempotent: it skips rows that already exist.
By default it connects to localhost:5432 (the mapped Docker port).
Override with: DATABASE_URL=... python scripts/seed.py
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

POSTGRES_USER = os.getenv("POSTGRES_USER", "username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB = os.getenv("POSTGRES_DB", "smartlock")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5432/{POSTGRES_DB}",
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def upsert_locker(db, locker_type: str, is_active: bool = True):
    row = db.execute(
        text("SELECT id FROM lockers WHERE locker_type = :t"),
        {"t": locker_type},
    ).fetchone()
    if row:
        print(f"  [skip] locker '{locker_type}' already exists (id={row[0]})")
        return row[0]
    result = db.execute(
        text("INSERT INTO lockers (locker_type, is_active) VALUES (:t, :a) RETURNING id"),
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
        text("SELECT id FROM stock WHERE item_id = :i AND locker_id = :l"),
        {"i": item_id, "l": locker_id},
    ).fetchone()
    if row:
        print(f"  [skip] stock item_id={item_id} locker_id={locker_id} already exists")
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
    print(f"  [ok]   stock item_id={item_id} × {quantity} {unit} in locker {locker_id} (id={sid})")
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
        print(f"  [skip] permission locker={locker_id} target='{target}' already exists")
        return row[0]
    result = db.execute(
        text(
            "INSERT INTO locker_permissions"
            " (locker_id, subject_type, role_name, user_id,"
            "  can_view, can_open, can_edit, can_manage)"
            " VALUES (:l, :st, :rn, :ui, :cv, :co, :ce, :cm)"
            " RETURNING id"
        ),
        {
            "l": locker_id, "st": subject_type, "rn": role_name, "ui": user_id,
            "cv": can_view, "co": can_open, "ce": can_edit, "cm": can_manage,
        },
    )
    db.commit()
    pid = result.fetchone()[0]
    print(
        f"  [ok]   permission locker={locker_id} '{target}'"
        f" view={can_view} open={can_open} edit={can_edit} manage={can_manage}"
        f" (id={pid})"
    )
    return pid


def seed():
    db = Session()
    try:
        db.execute(text("SELECT 1"))
        print(f"\nConnected to: {DATABASE_URL.split('@')[-1]}\n")

        # ── Lockers ───────────────────────────────────────────────────────────
        print("=== Lockers ===")
        l_3d    = upsert_locker(db, "3D")
        l_elec  = upsert_locker(db, "Electronique")
        l_text  = upsert_locker(db, "Textile")
        l_bureau = upsert_locker(db, "Bureau")

        # ── Categories ────────────────────────────────────────────────────────
        print("\n=== Categories ===")
        c_elec = upsert_category(db, "Électronique")
        c_3d   = upsert_category(db, "Impression 3D")
        c_text = upsert_category(db, "Textile")
        c_bur  = upsert_category(db, "Bureau")

        # ── Items ─────────────────────────────────────────────────────────────
        print("\n=== Items ===")
        i_ard  = upsert_item(db, "Arduino Uno R3",       "REF-ARD-001",  "Carte microcontrôleur ATmega328P",        c_elec)
        i_esp  = upsert_item(db, "ESP32 DevKit",          "REF-ESP-032",  "Module WiFi+BT pour IoT",                 c_elec)
        i_rpi  = upsert_item(db, "Raspberry Pi 4 (4GB)", "REF-RPI-004",  "Ordinateur monocarte 4GB RAM",            c_elec)
        i_fil  = upsert_item(db, "Filament PLA 1kg",      "REF-FIL-PLA",  "Filament PLA 1.75mm blanc",               c_3d)
        i_res  = upsert_item(db, "Résine UV 500ml",       "REF-RES-UV",   "Résine photopolymère transparente",       c_3d)
        i_tis  = upsert_item(db, "Tissu coton 2m",        "REF-TIS-COT",  "Coton blanc 150cm de large",              c_text)
        i_fil2 = upsert_item(db, "Fil à coudre (lot)",    "REF-FIL-COU",  "Assortiment fils couleurs",               c_text)
        i_cis  = upsert_item(db, "Ciseaux de coupe",      "REF-CIS-001",  "Ciseaux professionnels 25cm",             c_text)
        i_sty  = upsert_item(db, "Stylos (lot 10)",       "REF-STY-001",  "Stylos bille bleus",                      c_bur)
        i_pap  = upsert_item(db, "Ramette papier A4",     "REF-PAP-A4",   "500 feuilles 80g/m²",                     c_bur)

        # ── Stock ─────────────────────────────────────────────────────────────
        print("\n=== Stock ===")
        upsert_stock(db, i_ard,  l_3d,    5)
        upsert_stock(db, i_esp,  l_3d,    8)
        upsert_stock(db, i_fil,  l_3d,    10)
        upsert_stock(db, i_res,  l_3d,    4)
        upsert_stock(db, i_rpi,  l_elec,  3)
        upsert_stock(db, i_ard,  l_elec,  5)
        upsert_stock(db, i_esp,  l_elec,  6)
        upsert_stock(db, i_tis,  l_text,  8)
        upsert_stock(db, i_fil2, l_text,  20)
        upsert_stock(db, i_cis,  l_text,  3)
        upsert_stock(db, i_sty,  l_bureau, 10)
        upsert_stock(db, i_pap,  l_bureau, 5)

        # ── Locker Permissions ────────────────────────────────────────────────
        # can_view   = consulter les stocks
        # can_open   = ouvrir l'armoire + déclarer prise/dépôt
        # can_edit   = modifier le catalogue (types d'items)
        # can_manage = gérer les ACL de ce locker

        print("\n=== Locker Permissions ===")

        # Armoire 3D
        print("\n-- Armoire 3D --")
        upsert_permission(db, l_3d, "role", "membre",       None, can_view=True)
        upsert_permission(db, l_3d, "role", "3d",           None, can_view=True, can_open=True)
        upsert_permission(db, l_3d, "role", "electronique", None, can_view=True)
        upsert_permission(db, l_3d, "role", "textile",      None, can_view=True)
        upsert_permission(db, l_3d, "role", "materialiste", None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_3d, "role", "codir",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_3d, "role", "admin",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)

        # Armoire Electronique
        print("\n-- Armoire Electronique --")
        upsert_permission(db, l_elec, "role", "membre",       None, can_view=True)
        upsert_permission(db, l_elec, "role", "3d",           None, can_view=True)
        upsert_permission(db, l_elec, "role", "electronique", None, can_view=True, can_open=True)
        upsert_permission(db, l_elec, "role", "textile",      None, can_view=True)
        upsert_permission(db, l_elec, "role", "materialiste", None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_elec, "role", "codir",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_elec, "role", "admin",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)

        # Armoire Textile
        print("\n-- Armoire Textile --")
        upsert_permission(db, l_text, "role", "membre",       None, can_view=True)
        upsert_permission(db, l_text, "role", "3d",           None, can_view=True)
        upsert_permission(db, l_text, "role", "electronique", None, can_view=True)
        upsert_permission(db, l_text, "role", "textile",      None, can_view=True, can_open=True)
        upsert_permission(db, l_text, "role", "materialiste", None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_text, "role", "codir",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_text, "role", "admin",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)

        # Armoire Bureau
        print("\n-- Armoire Bureau --")
        upsert_permission(db, l_bureau, "role", "materialiste", None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_bureau, "role", "codir",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)
        upsert_permission(db, l_bureau, "role", "admin",        None, can_view=True, can_open=True, can_edit=True, can_manage=True)

        print("\n✅ Seed complete.\n")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seed failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed()
