# Changelog

All notable NexusDesk release milestones are documented here.

## [1.1.0] - 2026-10-08

### Added

- Business-hour SLA calculation using Monday-Friday, 8:00 AM-5:00 PM support hours
- Final SLA targets of 4 business hours for High, 1 business day for Medium, and 3 business days for Low priority tickets
- Temporary 30-minute MFA browser trust after successful verification
- MFA verification-code resend workflow
- Administrator support-request submission workflow
- Administrator knowledge-base feedback review
- Expanded employee ticket tracking and ticket-detail experience
- Enhanced operational analytics and technician workload reporting
- Branded HTML transactional emails with plain-text fallbacks
- Professional NexusDesk ticket references

### Improved

- Employee and administrator portal UX
- User-management interface and department labeling
- Ticket status, SLA, and resolution presentation
- Analytics chart responsiveness and automatic scaling
- Ticket filtering and dashboard navigation
- Knowledge-base feedback workflow
- MFA and password-recovery email presentation
- Ticket submission, assignment, resolution, and mention notifications

### Security

- Preserved MFA trust only for the original temporary trust window
- Maintained rate limiting for login, MFA, and password-recovery workflows
- Hardened Docker build context to exclude environment files and local runtime data
- Continued protection of secrets through Git and Docker ignore rules

### Demo / Portfolio

- Expanded realistic local demo data for product demonstrations
- Refined administrator and employee workflows for portfolio presentation
- Completed final UI, analytics, notification, and account-management polish

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
