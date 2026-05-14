from sqlalchemy.orm import Session
from src.models.role import Role
from src.schemas.role import RoleUpdate


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.query(Role).filter(Role.name == name).first()


def list_roles(db: Session) -> list[Role]:
    return db.query(Role).order_by(Role.tier.desc(), Role.name).all()


def get_roles_for_names(db: Session, names: list[str]) -> list[Role]:
    return db.query(Role).filter(Role.name.in_(names)).all()


def create_role(
    db: Session,
    name: str,
    label: str,
    tier: int,
    is_manager: bool,
    is_role_admin: bool,
    capacities: list[str],
    is_system: bool = False,
) -> Role:
    role = Role(
        name=name, label=label, tier=tier,
        is_system=is_system, is_manager=is_manager,
        is_role_admin=is_role_admin, capacities=capacities,
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(db: Session, role: Role, data: RoleUpdate) -> Role:
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(role, key, val)
    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role: Role) -> None:
    db.delete(role)
    db.commit()
