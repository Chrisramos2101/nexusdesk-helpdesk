# Security Policy

## Project Scope

NexusDesk is a portfolio-focused IT help desk and ticket management application developed to demonstrate software engineering, secure application design, database management, and IT support workflows.

The application is designed for educational and demonstration purposes using synthetic data. It is not intended to store or process real confidential business, customer, financial, medical, authentication, or other regulated information.

NexusDesk should not be considered a commercially certified or independently security-audited application.

## Security Controls

NexusDesk incorporates multiple layers of security controls to reduce common application risks.

### Authentication & Access Control

- Werkzeug password hashing
- Role-based access control for employee and administrator accounts
- Email-based multi-factor authentication (MFA)
- Expiring MFA challenges with attempt limits
- Login rate limiting and failed-login account lockout
- One-time, expiring password-reset tokens
- Case-insensitive account recovery lookup

### Application & Session Security

- Cross-site request forgery (CSRF) protection
- Secure session cookie configuration for production environments
- HTTP security headers, including Content Security Policy (CSP), HSTS, anti-framing, and MIME-sniffing protection
- HTTPS/TLS support through the configured deployment platform

### Monitoring & Configuration

- Security-related audit logging
- Production configuration validation
- Application and database health-check functionality
- Environment-based configuration of application secrets

These controls are intended to strengthen application security but do not eliminate all potential vulnerabilities.

## Secrets & Credential Management

Real credentials and sensitive configuration values must never be committed to the repository.

Examples include:

- `SECRET_KEY`
- `DATABASE_URL` containing credentials
- Transactional email API keys
- SMTP passwords
- Bootstrap account credentials
- Password-reset tokens
- MFA verification codes

Sensitive values should be supplied through environment variables or deployment-platform secret management.

Local `.env` files containing secrets must be excluded from Git tracking.

If sensitive information is accidentally exposed in source code, commits, screenshots, logs, or documentation, affected credentials should be revoked or rotated immediately.

Removing a secret from the latest commit does not automatically remove it from Git history.

## Demonstration Data

NexusDesk supports synthetic demonstration data to showcase IT support workflows without exposing real employee or customer information.

Synthetic accounts use the `demo_` username prefix and `example.com` email addresses.

Demonstration data must not contain genuine credentials, confidential business records, or personally identifiable customer information.

## File Uploads & Storage

The configured free-tier cloud environment uses ephemeral file storage. Uploaded files may be lost during service restarts, redeployments, or container replacement.

This configuration is intended for portfolio demonstrations and is not suitable for persistent business document storage.

Do not upload confidential, sensitive, or regulated files to a public demonstration environment.

## Reporting Security Vulnerabilities

If you discover a potential vulnerability in NexusDesk, please report it responsibly.

- Do not publicly disclose vulnerabilities before they can be reviewed.
- Do not include real credentials, tokens, or confidential information in a public GitHub issue.
- Where available, use GitHub's private vulnerability reporting feature to submit security findings.
- Include a description of the issue, affected functionality, and reproducible steps using non-sensitive test data.

Security reports will be reviewed as part of the project's maintenance process. No formal response-time or remediation SLA is guaranteed.

## Responsible Testing

Security testing must be performed only against environments and accounts you own or have explicit authorization to test.

Do not:

- Attempt to access accounts belonging to other individuals
- Use stolen or unauthorized credentials
- Perform disruptive testing against public infrastructure
- Upload sensitive information to demonstration environments
- Attempt to extract private information from other users

Use local development environments and synthetic accounts for security testing whenever possible.

## Production Hardening Considerations

Before NexusDesk could be considered for real organizational deployment, additional controls and operational capabilities would need to be evaluated, including:

- Persistent, managed object storage for attachments
- Private networking and infrastructure access controls
- Organizational SSO and identity provider integration
- Centralized secrets management
- Managed database backups and point-in-time recovery
- Automated dependency and vulnerability scanning
- Web application firewall (WAF) and edge-level rate limiting
- Centralized observability, monitoring, and alerting
- Formal incident response, retention, and recovery policies
- Security testing and independent assessment appropriate to the deployment

These considerations are outside the current portfolio demonstration scope.

## Security Documentation

For additional implementation details, see:

- [Project README](README.md)
- [Architecture Documentation](docs/ARCHITECTURE.md)
- [Portfolio Case Study](docs/PORTFOLIO_CASE_STUDY.md)
