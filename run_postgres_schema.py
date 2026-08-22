from database.db import get_db_connection


def run_schema_file():
    connection = get_db_connection()
    cursor = connection.cursor()

    with open("database/postgres_schema.sql", "r", encoding="utf-8") as file:
        sql_script = file.read()

    cursor.execute(sql_script)

    connection.commit()
    connection.close()

    print("PostgreSQL schema applied successfully.")


if __name__ == "__main__":
    run_schema_file()