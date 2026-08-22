NexusDesk PostgreSQL Migration Notes

Current database:
- SQLite
- DATABASE_URL=helpdesk.db

Production target:
- PostgreSQL
- DATABASE_URL=postgresql://username:password@host:5432/database_name

Required future changes:
1. Replace SQLite connection logic with PostgreSQL connection logic.
2. Replace SQLite placeholders (?) with PostgreSQL placeholders (%s).
3. Replace AUTOINCREMENT with SERIAL or IDENTITY.
4. Move schema creation to migrations.
5. Test all routes against PostgreSQL before deployment.