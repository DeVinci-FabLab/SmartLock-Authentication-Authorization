import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.base import Base
from src.models.role import Role
from src.crud.crud_role import (
    get_role_by_name, list_roles, create_role, update_role, delete_role,
    get_roles_for_names,
)
from src.schemas.role import RoleUpdate

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture()
def db():
    conn = engine.connect()
    tx = conn.begin()
    session = Session(bind=conn)
    yield session
    session.close()
    tx.rollback()
    conn.close()

def _seed_role(db, name="testrole", tier=1, is_system=False, is_manager=False, is_role_admin=False):
    r = Role(name=name, label=name.title(), tier=tier, is_system=is_system,
             is_manager=is_manager, is_role_admin=is_role_admin, capacities=[])
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

def test_get_role_by_name(db):
    _seed_role(db, "myrole")
    r = get_role_by_name(db, "myrole")
    assert r is not None
    assert r.name == "myrole"

def test_get_role_by_name_missing(db):
    assert get_role_by_name(db, "ghost") is None

def test_list_roles_empty(db):
    assert list_roles(db) == []

def test_list_roles_returns_all(db):
    _seed_role(db, "r1")
    _seed_role(db, "r2")
    assert len(list_roles(db)) == 2

def test_create_role(db):
    r = create_role(db, name="new", label="New Role", tier=1,
                    is_manager=False, is_role_admin=False, capacities=["audit_log_full"])
    assert r.id is not None
    assert r.name == "new"
    assert r.capacities == ["audit_log_full"]
    assert r.is_system is False

def test_update_role_label(db):
    r = _seed_role(db, "updatable")
    updated = update_role(db, r, RoleUpdate(label="New Label"))
    assert updated.label == "New Label"

def test_update_role_false_boolean(db):
    r = _seed_role(db, "booltest", is_manager=True)
    updated = update_role(db, r, RoleUpdate(is_manager=False))
    assert updated.is_manager is False

def test_delete_role(db):
    r = _seed_role(db, "deletable")
    delete_role(db, r)
    assert get_role_by_name(db, "deletable") is None

def test_get_roles_for_names(db):
    _seed_role(db, "a")
    _seed_role(db, "b")
    results = get_roles_for_names(db, ["a", "b", "ghost"])
    assert len(results) == 2
