import sqlite3

from database.db import get_db_connection


def run():
    connection = get_db_connection()
    cursor = connection.cursor()

    for column in [
        "resolution_time TEXT DEFAULT ''",
        "sla_met TEXT DEFAULT ''"
    ]:
        try:
            cursor.execute(
                f"ALTER TABLE tickets ADD COLUMN {column}"
            )
        except sqlite3.OperationalError:
            pass

    connection.commit()
    connection.close()