from app.db.seed import seed_demo_catalog
from app.db.session import SessionLocal


def main() -> None:
    with SessionLocal.begin() as session:
        seed_demo_catalog(session)


if __name__ == "__main__":
    main()
