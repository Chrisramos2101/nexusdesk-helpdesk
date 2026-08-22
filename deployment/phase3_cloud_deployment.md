# Phase 3 Cloud Deployment Gate

Phase 3 uses one container image everywhere:

1. Local verification: Docker + PostgreSQL
2. Production: the same Docker image + managed PostgreSQL
3. Public HTTPS endpoint: used from desktop and phone

## Production requirements

Before the public deployment is considered complete:

- Managed PostgreSQL is provisioned.
- `DATABASE_URL` points to PostgreSQL.
- `SECRET_KEY` is a strong random value.
- SMTP credentials are stored only in provider secrets/environment variables.
- HTTPS is enabled.
- `/healthz` returns HTTP 200 and reports `postgresql`.
- The application survives a container restart.
- Upload storage is persistent for the chosen hosting platform.
- Database backups are enabled.
- A production smoke test passes from both desktop and phone.

## Provider selection

Do not create a second architecture. Choose a container-capable platform that provides:
- HTTPS
- environment/secrets management
- managed PostgreSQL or access to one
- persistent storage for uploads

The verified Docker image from this phase is the deployment artifact.
