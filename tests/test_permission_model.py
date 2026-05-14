import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from src.database.base import Base
from src.models.lockers import Lockers
from src.models.locker_permission import Locker_Permission

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

@pytest.fixture()
def db():
    conn = engine.connect()
    tx = conn.begin()
    s = Session(bind=conn)
    yield s
    s.close(); tx.rollback(); conn.close()

def test_permission_has_level_field(db):
    locker = Lockers(locker_type="fdm")
    db.add(locker); db.flush()
    perm = Locker_Permission(locker_id=locker.id, role_name="agent_fdm", permission_level="can_open")
    db.add(perm); db.commit(); db.refresh(perm)
    assert perm.permission_level == "can_open"
    assert not hasattr(perm, "can_view") or perm.can_view is None  # old bool columns gone

def test_permission_unique_per_role_locker(db):
    locker = Lockers(locker_type="fdm")
    db.add(locker); db.flush()
    db.add(Locker_Permission(locker_id=locker.id, role_name="r1", permission_level="can_view"))
    db.commit()
    db.add(Locker_Permission(locker_id=locker.id, role_name="r1", permission_level="can_open"))
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
