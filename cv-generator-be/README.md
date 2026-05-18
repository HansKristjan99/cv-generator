# cv-generator-be

FastAPI backend for AI-assisted CV generation. It turns a candidate's source
material and a target job description into a tailored, LaTeX-rendered CV PDF,
maintains a per-user profile ("memory"), and drafts answers to clarifying
questions.

## Layout

```
app/
  main.py        FastAPI app, request-tracing middleware, logging setup
  config.py      Settings (env vars) + the OpenAI MODEL constant
  db.py          SQLAlchemy engine, session factory, get_db dependency
  models.py      ORM models (the persisted user profile)
  schemas.py     Pydantic models for structured LLM input/output
  api/           HTTP routers — cv, users, memory
  services/      Core logic — auth, openai_client, latex, user_data, prompts
  alembic/       Database migrations
  tests/         Pytest suite
```

## Running locally

```bash
make db-up      # start Postgres + Adminer via docker compose
make migrate    # apply Alembic migrations
make dev        # run uvicorn with reload
```

Configuration is read from `.env` (see `app/config.py`): `DATABASE_URL`,
`LOG_LEVEL`, `CLERK_SECRET_KEY`, `CLERK_JWT_KEY`, `CLERK_AUTHORIZED_PARTIES`,
and `OPENAI_API_KEY`.

## Tests

```bash
uv run pytest
```

`tests/test_openai_client.py` makes live OpenAI calls and needs
`OPENAI_API_KEY` plus network access; the rest run offline.
