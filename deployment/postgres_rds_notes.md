NexusDesk RDS PostgreSQL Notes

Production Database:
Use Amazon RDS PostgreSQL.

Recommended Settings:
- PostgreSQL engine
- Free tier if available
- Public access: No for real production
- Backups enabled
- Storage autoscaling enabled
- Strong master password
- Security group only allows app access

DATABASE_URL format:
postgresql://username:password@rds-endpoint.amazonaws.com:5432/database_name

After RDS is created:
- Add DATABASE_URL to Elastic Beanstalk environment variables
- Run postgres_schema.sql against RDS
- Confirm users/tickets tables exist