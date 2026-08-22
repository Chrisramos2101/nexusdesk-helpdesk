NexusDesk AWS Deployment Plan

Target Architecture:
- AWS Elastic Beanstalk or ECS for Flask application
- Amazon RDS PostgreSQL for production database
- Amazon S3 for file attachments
- Amazon CloudWatch for logs and monitoring
- GitHub Actions for CI/CD deployment

Required Production Environment Variables:
- SECRET_KEY
- DATABASE_URL
- MAIL_SERVER
- MAIL_PORT
- MAIL_USE_TLS
- MAIL_USERNAME
- MAIL_PASSWORD
- MAIL_DEFAULT_SENDER
- APP_BASE_URL
- UPLOAD_FOLDER
- MAX_UPLOAD_MB
- FLASK_ENV=production

Pre-Deployment Checklist:
- Docker builds successfully
- PostgreSQL works locally
- Login works on PostgreSQL
- Tickets work on PostgreSQL
- Health endpoint works
- Logs are generated
- .env is ignored by Git
- .env.production.example exists
- CI pipeline exists

AWS Deployment Steps:
1. Create AWS account IAM user/role for deployment.
2. Create production RDS PostgreSQL database.
3. Create S3 bucket for attachments.
4. Deploy Flask app container to Elastic Beanstalk or ECS.
5. Set production environment variables.
6. Connect app to RDS PostgreSQL.
7. Run production database schema.
8. Configure HTTPS/domain.
9. Enable CloudWatch logs.
10. Test login, tickets, attachments, email, and monitoring.