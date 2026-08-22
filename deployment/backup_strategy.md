NexusDesk Backup Strategy

Database:
- Daily PostgreSQL backup
- Weekly full backup
- Monthly archive backup

Files:
- S3 versioning enabled
- Daily attachment backup

Recovery Goals:
- Recovery Time Objective: < 1 hour
- Recovery Point Objective: < 24 hours

Testing:
- Quarterly restore testing