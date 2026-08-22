# Changelog

All notable NexusDesk release milestones are documented here.

## [1.0.0] - 2026-08-22

### Added

- Modular Flask Blueprints and service-layer architecture
- PostgreSQL production database support
- Docker and Docker Compose development/production workflows
- Gunicorn production server
- Render infrastructure-as-code deployment
- GitHub Actions CI
- Health-check endpoint with database verification
- Employee and administrator portals
- Ticket submission, categories, priorities, assignments, notes, SLA tracking, and resolution workflow
- User management
- Knowledge base, article views, and feedback
- File attachment workflow
- Audit logging and security monitoring
- Login rate limiting and account lockout
- Email MFA challenges
- Password reset with expiring one-time tokens
- Brevo HTTPS transactional email integration
- Secure browser headers and production session configuration
- Deterministic/idempotent synthetic portfolio dataset
- Automated PostgreSQL smoke tests
- Automated public HTTPS acceptance testing

### Fixed

- SQLite/PostgreSQL compatibility issues
- PostgreSQL insert-ID handling
- Referential-integrity issues discovered during production migration
- Legacy orphan attachment metadata
- Environment-loading order
- Missing MFA tables and schema drift
- Case-sensitive password-reset email lookup
- GitHub Actions Python module resolution
- Render dynamic-port and proxy configuration
- Favicon filename/empty-file issue
- UTF-8 BOM in `routes/auth.py`

### Security

- Removed local database and environment secrets from Git tracking/history
- Added CSRF protection
- Added rate limiting
- Added MFA attempt limits and challenge invalidation
- Added secure production cookies
- Added HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and Permissions-Policy
- Added audit logging and security cleanup support

### Deployment

The v1.0.0 portfolio release is designed for a Dockerized Flask/Gunicorn application backed by PostgreSQL. The current public demonstration runs on Render and uses Brevo for HTTPS transactional email.

## Pre-1.0 development

Earlier commits contain the staged stabilization, security, PostgreSQL migration, Docker productionization, Render deployment, and public acceptance work that led to v1.0.0.
