from database.config import DATABASE_URL


def db_placeholder():
    if DATABASE_URL.startswith("postgresql://"):
        return "%s"

    return "?"

def is_postgres():
    return DATABASE_URL.startswith("postgresql://")
