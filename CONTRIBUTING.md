# Contributing

## Local setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; source .venv/bin/activate elsewhere
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm ci
npm run dev                    # http://localhost:5173, proxies /api to :8000
```

A fresh database is empty. Either register the first administrator in the UI, or enable the
demonstration dataset with `SEED_ON_STARTUP=true`, `SEED_DEMO_DATA=true`, `DEMO_MODE=true` in
`backend/.env` (see `.env.example`).

## Making a change

1. Work on a feature branch. Do not rewrite shared history.
2. Keep the backend layering: routers handle HTTP, `app/services/` holds derived logic, models own
   persistence. New schema changes require an Alembic revision — never edit a migrated database by
   hand.
3. Enforce authorisation on the server. The React app may hide controls, but the API must decide.
4. Never introduce fabricated customer records into a production path. Demonstration data belongs
   in `app/seed/` and test fixtures, and must be identifiable as synthetic.
5. If you add an outbound integration, follow the contract in `docs/integration.md`; nothing may
   contact a customer automatically.

## Checks before committing

```bash
cd backend && python -m pytest -q
cd frontend && npm run typecheck && npm run build
```

Run the Playwright suite when you touched a primary screen or the session flow. Test data is
synthetic; do not point a test at a real database.

## Commit style

One line, conventional-commit prefix, no body, no attribution:

```
feat(evidence): preserve provenance across edits
fix(exports): surface the server error on a failed download
test(auth): cover first-run registration
docs(api): document session requirements
```

Commit a completed unit, not a work-in-progress checkpoint. Do not stage local databases, `.env`
files, virtual environments, `node_modules` or build output.

## Documentation

`docs/` holds both the original discovery set (`01-…`–`20-…`) and the canonical set (`prd.md`,
`architecture.md`, `auth.md`, …). Update the canonical document when behaviour changes; a
document that describes the implementation inaccurately is a defect.
