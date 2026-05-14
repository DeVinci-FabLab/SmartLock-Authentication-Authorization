import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.base import Base
from src.models.role import Role

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

def test_role_model_fields():
    db = SessionLocal()
    role = Role(name="test_role", label="Test Role", tier=1, is_system=False,
                is_manager=False, is_role_admin=False, capacities=[])
    db.add(role)
    db.commit()
    db.refresh(role)
    assert role.id is not None
    assert role.name == "test_role"
    assert role.tier == 1
    assert role.is_system is False
    assert role.capacities == []
    db.close()

def test_role_name_unique():
    db = SessionLocal()
    db.add(Role(name="dup", label="A", tier=0, is_system=False, is_manager=False, is_role_admin=False, capacities=[]))
    db.commit()
    db.add(Role(name="dup", label="B", tier=0, is_system=False, is_manager=False, is_role_admin=False, capacities=[]))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
    db.close()
