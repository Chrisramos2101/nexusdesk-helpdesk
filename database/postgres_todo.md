PostgreSQL Migration Checklist

SQLite Incompatibilities To Replace:

1. AUTOINCREMENT
   Replace with SERIAL

2. Question Mark Placeholders
   SQLite:
       WHERE id = ?

   PostgreSQL:
       WHERE id = %s

3. sqlite3.Row
   Replace with RealDictCursor

4. SQLite Imports
   Replace with psycopg2

Files To Audit:

services/user_service.py
services/ticket_service.py
services/password_reset_service.py
services/attachment_service.py
services/audit_service.py
routes/auth.py
routes/tickets.py
routes/admin.py
routes/dashboard.py