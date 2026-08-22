NexusDesk AWS Final Checklist

Before Deployment:
- docker-compose.prod.yml exists
- .env.production exists locally
- .env.production is ignored by Git
- Docker build passes
- /healthz works
- PostgreSQL local test passed
- MFA works
- Ticket workflows work
- System Dashboard works

AWS Services Needed:
- Elastic Beanstalk
- RDS PostgreSQL
- CloudWatch Logs
- Optional S3 for attachments later

Deployment Order:
1. Push code to GitHub
2. Confirm GitHub Actions passes
3. Create RDS PostgreSQL database
4. Create Elastic Beanstalk Docker app
5. Add production environment variables
6. Deploy NexusDesk
7. Run PostgreSQL schema
8. Test login and MFA
9. Test tickets
10. Enable logs and monitoring