NexusDesk PostgreSQL Test Plan

Goal:
Confirm NexusDesk can run against PostgreSQL instead of SQLite.

Steps:
1. Start PostgreSQL locally using Docker.
2. Create a nexusdesk database.
3. Update DATABASE_URL to PostgreSQL.
4. Run database/postgres_schema.sql.
5. Seed admin and employee users.
6. Test login.
7. Test ticket creation.
8. Test dashboard.
9. Test attachments.
10. Test password reset.
11. Test audit logs.
12. Test system dashboard.

Pass Criteria:
- App starts without SQLite.
- Users can log in.
- Tickets can be created and managed.
- Audit logs are written.
- System dashboard loads.
- No SQLite-specific errors appear.