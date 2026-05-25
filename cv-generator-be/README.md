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
`OPENAI_API_KEY`, `FRONTEND_URL`, `STRIPE_SECRET_KEY`,
`STRIPE_WEBHOOK_SECRET`, and `STRIPE_PRO_PRICE_ID`.

Copy `.env.example` to `.env` and fill in real local/test values.

## Stripe billing locally

Use Stripe test mode locally.

1. Create or reuse a Stripe test Product with a recurring Price.
2. Put the test Price ID in backend `.env` as `STRIPE_PRO_PRICE_ID`.
3. Put the test secret key in backend `.env` as `STRIPE_SECRET_KEY`.
4. Put `FRONTEND_URL=http://localhost:5173` in backend `.env`.
5. Start the local webhook listener:

```bash
stripe listen \
  --forward-to 127.0.0.1:8000/billing/webhook \
  --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed
```

Copy the printed `whsec_...` into backend `.env` as
`STRIPE_WEBHOOK_SECRET`, then restart the backend.

The frontend must call this API directly with:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

After checkout, Stripe webhooks create or update the `subscriptions` row. The
return URL is only for UI refresh; it is not the source of paid access.

Test checkout with Stripe's test card `4242 4242 4242 4242`, a future expiry,
and any CVC/ZIP.

## Tests

```bash
uv run pytest
```

`tests/test_openai_client.py` makes live OpenAI calls and needs
`OPENAI_API_KEY` plus network access; the rest run offline.
