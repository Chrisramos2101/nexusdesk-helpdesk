import os


def _normalize_database_environment() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()

    if database_url.startswith("postgres://"):
        database_url = "postgresql://" + database_url[len("postgres://"):]
        os.environ["DATABASE_URL"] = database_url

    return database_url


def main():
    database_url = _normalize_database_environment()

    from services.production_config import (
        prepare_runtime_directories,
        validate_production_environment,
    )

    validate_production_environment()
    prepare_runtime_directories()

    if database_url.startswith("postgresql://"):
        from run_postgres_schema import run_schema_file

        print("Applying idempotent PostgreSQL schema...", flush=True)
        run_schema_file()
        print("PostgreSQL schema applied successfully.", flush=True)

        from services.bootstrap_service import bootstrap_portfolio_admin
        bootstrap_portfolio_admin()

        if os.getenv("SEED_DEMO_DATA", "false").strip().lower() == "true":
            from scripts.seed_demo_portfolio import seed_demo_data
            seed_demo_data()

    os.execvp(
        "gunicorn",
        [
            "gunicorn",
            "-c",
            "gunicorn.conf.py",
            "app:app",
        ],
    )


if __name__ == "__main__":
    main()
