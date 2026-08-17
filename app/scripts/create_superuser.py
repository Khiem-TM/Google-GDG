import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m app.scripts.create_superuser <email>")
    email = sys.argv[1].strip().lower()
    password = getpass.getpass("Password: ")
    if len(password) < 12:
        raise SystemExit("Password must be at least 12 characters")

    with SessionLocal.begin() as session:
        user = session.scalar(select(User).where(User.email == email))
        if user is None:
            session.add(User(email=email, password_hash=hash_password(password), is_superuser=True))
        else:
            user.password_hash = hash_password(password)
            user.is_superuser = True
            user.status = "active"
            user.token_version += 1


if __name__ == "__main__":
    main()
