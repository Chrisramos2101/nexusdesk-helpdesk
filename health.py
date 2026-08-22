from flask import jsonify

from database.db import get_db_connection
from database.config import DATABASE_URL


def register_health_route(app):
    @app.route("/healthz")
    def health_check():
        connection = None
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            database_name = "postgresql" if DATABASE_URL.startswith("postgresql://") else "sqlite"
            return jsonify({
                "status": "healthy",
                "application": "NexusDesk",
                "database": database_name
            }), 200
        except Exception:
            return jsonify({
                "status": "unhealthy",
                "application": "NexusDesk",
                "database": "unavailable"
            }), 503
        finally:
            if connection is not None:
                connection.close()
