# NexusDesk Portfolio Case Study

## Problem

A basic help desk prototype can demonstrate CRUD functionality, but it does not necessarily demonstrate production engineering.

NexusDesk was expanded from a local Flask application into a deployable portfolio system that addresses:

- application architecture
- authentication and authorization
- data integrity
- automated testing
- PostgreSQL migration
- Docker
- CI
- cloud deployment
- transactional email
- monitoring
- synthetic demonstration data

## Engineering Goals

The project was intentionally treated as a complete systems-development exercise rather than a collection of isolated features.

Primary goals were:

1. preserve the useful original help desk workflows
2. improve architecture without unnecessary rewrites
3. harden security-critical paths
4. prove PostgreSQL compatibility
5. make deployment repeatable
6. create automated release gates
7. keep the final public demo understandable to recruiters and reviewers

## Major Engineering Work

### Stabilization

The project was separated into Blueprints, services, and database helpers. Environment-loading order and schema initialization were corrected so configuration was deterministic.

### Security

Authentication was hardened with:

- password hashing
- lockout logic
- rate limiting
- CSRF
- role authorization
- MFA
- secure cookies
- reset-token expiration and one-time usage
- browser security headers

Security-sensitive behavior was covered by automated tests.

### PostgreSQL Migration

The production database path was migrated from SQLite-oriented behavior to PostgreSQL.

The migration process uncovered real referential-integrity issues, including orphan attachment metadata. Rather than bypassing foreign keys, the invalid metadata was identified and repaired before the production migration continued.

### Docker and Deployment

The application and PostgreSQL workflows were tested through Docker Compose.

Gunicorn, dynamic platform ports, reverse-proxy behavior, health checks, and production configuration validation were added before cloud deployment.

### Transactional Email

Local SMTP behavior was retained as a fallback, while the cloud deployment uses the Brevo HTTPS API to avoid free-host SMTP restrictions.

The same email service supports MFA and password reset.

### Synthetic Demo Data

A deterministic seed creates realistic support operations without publishing real private data.

The seeder is idempotent and includes a marker so redeploying cannot continually duplicate the portfolio dataset.

### Acceptance Testing

The final public deployment was tested for:

- HTTPS
- PostgreSQL health
- security headers
- secure cookies
- CSRF
- protected-route behavior
- disabled TRACE
- authentication/MFA
- password reset
- ticket workflows
- admin workflows
- knowledge-base workflows
- mobile browser usability

## Production Acceptance Results

The final automated public acceptance gate completed with:

- 22 automated public checks passing
- 0 automated failures
- PostgreSQL healthy
- local Docker/PostgreSQL regression passing
- full Python test suite passing

The one pre-release advisory was the favicon path, which is corrected in the v1.0.0 polish phase.

## Technical Tradeoffs

### Why Flask?

Flask makes the route/service/database boundaries visible and keeps the project understandable without introducing framework complexity unrelated to the portfolio goals.

### Why PostgreSQL?

PostgreSQL better represents a production relational database than a local SQLite file and exposes integrity/SQL compatibility issues that lightweight prototypes can hide.

### Why Render?

Render provides an accessible way to demonstrate a live Dockerized application with PostgreSQL and HTTPS without turning the portfolio project into a cloud-billing exercise.

### Why synthetic data?

A public portfolio should show realistic product behavior without exposing real users, ticket history, or private organizational information.

## What v1.0.0 Demonstrates

NexusDesk v1.0.0 demonstrates the ability to take an application through:

**planning → implementation → testing → migration → security hardening → deployment → production acceptance → release**

The final result is intentionally frozen as a completed portfolio product rather than continuously expanding the feature list.
