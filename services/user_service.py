from database.db import get_db_connection
from database.sql_helpers import db_placeholder


def get_user_by_username(username):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT *
        FROM users
        WHERE username = {placeholder}
    """, (username,))

    user = cursor.fetchone()

    connection.close()

    return user


def get_all_users():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id,
               full_name,
               username,
               email,
               department,
               role,
               last_login,
               last_logout
        FROM users
        ORDER BY role DESC, username ASC
    """)

    users = cursor.fetchall()

    connection.close()

    return users


def update_user(user_id, full_name, email, department, role):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        UPDATE users
        SET full_name = {placeholder},
            email = {placeholder},
            department = {placeholder},
            role = {placeholder}
        WHERE id = {placeholder}
    """, (full_name, email, department, role, user_id))

    connection.commit()
    connection.close()


def delete_user_by_id(user_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"DELETE FROM password_reset_tokens WHERE user_id = {placeholder}", (user_id,))
    cursor.execute(f"""
        DELETE FROM users
        WHERE id = {placeholder}
    """, (user_id,))

    connection.commit()
    connection.close()


def create_user_account(full_name, username, email, department, password_hash, role):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        INSERT INTO users 
        (full_name, username, email, department, password_hash, role)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})
    """, (
        full_name,
        username,
        email,
        department,
        password_hash,
        role
    ))

    connection.commit()
    connection.close()


def get_technicians():
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT username
        FROM users
        WHERE role = 'admin'
        ORDER BY username
    """)

    technicians = cursor.fetchall()

    connection.close()

    return technicians


def get_user_email_by_username(username):
    connection = get_db_connection()
    cursor = connection.cursor()
    placeholder = db_placeholder()

    cursor.execute(f"""
        SELECT email
        FROM users
        WHERE username = {placeholder}
    """, (username,))

    user = cursor.fetchone()
    connection.close()

    if user:
        return user["email"]

    return None