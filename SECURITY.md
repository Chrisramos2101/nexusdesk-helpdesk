# Security Policy

## Scope

NexusDesk is a portfolio/demo help desk application. The public deployment is intended to demonstrate software engineering, security controls, cloud deployment, and IT support workflows using synthetic data.

It should not be used to store real confidential business, customer, authentication, financial, medical, or regulated information.

## Security Controls

The v1.0.0 application includes:

- Werkzeug password hashing
- CSRF protection
- role-based access control
- secure production session cookies
- login rate limiting
- failed-login lockout
- email MFA
- expiring MFA challenges with attempt limits
- expiring one-time password reset tokens
- case-insensitive account recovery lookup
- audit logging
- restrictive security headers
- HTTPS/HSTS in production
- production configuration validation
- database-backed health checks

## Secrets

Real values for the following must never be committed:

- `SECRET_KEY`
- `DATABASE_URL`
- email API keys
- SMTP passwords
- bootstrap passwords
- reset tokens
- MFA codes

Use cloud environment variables and `.env` files excluded by `.gitignore`.

If a credential is exposed in a screenshot, terminal transcript, repository, or message, revoke/rotate it.

## Demo Data

The seeded public portfolio dataset is fictional.

Synthetic usernames use the `demo_` prefix and synthetic addresses use `example.com`.

## File Uploads

The free public deployment uses ephemeral upload storage. Uploaded files may disappear after service restart or redeployment. This is intentionally documented and is not appropriate for durable production file storage.

## Responsible Testing

Do not test NexusDesk using another person's credentials, identity, or email address without authorization.

Do not upload sensitive files to the public demo.

## Production Hardening Beyond Portfolio Scope

A real organizational rollout should additionally consider:

- managed persistent object storage for attachments
- private networking
- organization SSO/identity provider integration
- centralized secrets management
- dedicated transactional email domain
- managed backups and point-in-time recovery
- vulnerability/dependency scanning
- WAF/rate limiting at the edge
- formal incident response and retention policies
- observability/alerting service integration
