import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import Role, User
from app.services.exceptions import InvalidCredentialsError

logger = logging.getLogger(__name__)


def create_user(db: Session, email: str, password: str, role: Role = Role.VIEWER) -> User:
    user = User(email=email, password_hash=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> str:
    """Verify credentials and return a signed access token."""
    user = db.execute(select(User).where(User.email == email)).scalar_one_or_none()
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        logger.info("login failed for email=%s", email)
        raise InvalidCredentialsError("invalid email or password")
    logger.info("login succeeded for user_id=%s", user.id)
    return create_access_token(subject=user.id, role=user.role.value)
