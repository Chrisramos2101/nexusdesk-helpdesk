# NexusDesk v1.0.0 Release Checklist

## Code / quality

- [ ] Phase 4 local verifier passes
- [ ] Full pytest suite passes
- [ ] Python compile passes
- [ ] Docker/PostgreSQL health passes
- [ ] PostgreSQL application smoke passes
- [ ] No UTF-8 BOM remains in `routes/auth.py`
- [ ] `static/favicon.ico` exists and is non-empty
- [ ] obsolete zero-byte `static/favion.ico` is removed
- [ ] Git working tree is clean after release commit

## Public deployment

- [ ] Render deploys the release commit successfully
- [ ] `/healthz` returns HTTP 200
- [ ] production health reports PostgreSQL
- [ ] `/favicon.ico` returns HTTP 200
- [ ] login works
- [ ] Brevo MFA works
- [ ] password reset works
- [ ] demo data remains idempotent
- [ ] dashboard/ticket/admin/knowledge workflows remain healthy

## Security

- [ ] previously exposed API keys have been rotated
- [ ] previously exposed passwords have been changed
- [ ] no `.env` file is tracked
- [ ] no local database is tracked
- [ ] no real secret is present in README/docs/source
- [ ] public screenshots contain no secrets

## Documentation

- [ ] root README reflects Render/PostgreSQL/Brevo deployment
- [ ] architecture document present
- [ ] security document present
- [ ] portfolio case study present
- [ ] changelog present

## Release

- [ ] create final release commit
- [ ] push `main`
- [ ] wait for GitHub Actions
- [ ] wait for Render deployment
- [ ] run Phase 4 public verifier
- [ ] create annotated tag `v1.0.0`
- [ ] push tag
- [ ] optionally create GitHub Release from `v1.0.0`
- [ ] freeze project scope

After `v1.0.0`, new ideas should be tracked separately rather than reopening the completed release unless there is a real bug or security issue.
