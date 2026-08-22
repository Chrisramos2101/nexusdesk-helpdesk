import os
import sys


def main():
    database_url = os.getenv("DATABASE_URL", "")

    if database_url.startswith("postgresql://"):
        from run_postgres_schema import run_schema_file
        print("Applying idempotent PostgreSQL schema...")
        run_schema_file()

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
