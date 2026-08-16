# Deploying Powerful Notes

This is a standard Flask + gunicorn app with a `Procfile`, so it deploys as-is
to most PaaS hosts (Render, Railway, Fly.io, Heroku-style platforms). The
database layer runs on Postgres in production (via `psycopg[binary]`), falling
back to a local SQLite file only when `DATABASE_URL` is unset (local dev).

## Fastest path: Render Blueprint

`render.yaml` in this repo is a one-click Render Blueprint: it provisions a
free Postgres database and a free web service, wires `DATABASE_URL` between
them automatically, and generates `SECRET_KEY` for you.

1. Push this repo to GitHub.
2. In the Render dashboard: **New** → **Blueprint** → pick the repo.
3. Render reads `render.yaml` and provisions everything. First deploy takes a
   few minutes.

## Required environment variables (manual setup on other hosts)

Copy `.env.example` to `.env` locally, or set these directly in your host's
environment/secrets settings:

- `SECRET_KEY` — generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`. Never reuse the local dev value in production.
- `DATABASE_URL` — a Postgres connection string (`postgres://...` or `postgresql://...` are both accepted; the app rewrites either to the `psycopg` driver internally). Required for production — without it, the app falls back to a local SQLite file, which most PaaS hosts wipe on every deploy/restart, silently losing all client data.
- `SESSION_COOKIE_SECURE=true` — set this once the app is actually served over HTTPS (required for the login cookie to be marked secure).

## Before you have real, paying customers with real client data

The app enforces per-account data isolation and hashes passwords, but going
live with actual client PHI additionally needs, outside anything a code
change can provide:

1. **HTTPS** — most PaaS hosts give you this for free on their default domain; make sure it's actually on before real data flows through.
2. **A Business Associate Agreement (BAA)** with your hosting provider, if you intend to market this as HIPAA-compliant. Not every host will sign one — check before committing to a platform.
3. **Your own risk assessment and written policies** — who has database access, how backups are handled, breach notification procedure, etc. This is an organizational requirement, not a code one.
4. **Backups** — set up automated backups for whatever database you land on; nothing here does that for you yet.

## Not yet built (intentionally, per the current plan)

- Subscription billing (Stripe) — planned as the next phase once this is live.
- Password reset via email — needs an email-sending service decided first.
- Multi-user teams under one practice account.
