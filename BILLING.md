# Stripe Billing

## Runtime flow

1. The user signs in with Clerk and opens the Subscription tab.
2. The frontend calls `GET /billing/subscription/` through `authFetch`.
   `VITE_API_BASE_URL` points directly at FastAPI, so there is no proxy.
3. If the user is not active, Subscribe calls
   `POST /billing/checkout_session/`.
4. The backend validates the Clerk bearer token, gets the app `User`, creates
   a Stripe Customer if needed, and creates a Stripe subscription Checkout
   Session for `STRIPE_PRO_PRICE_ID`.
5. The frontend mounts Stripe Embedded Checkout with the returned
   `client_secret`.
6. Stripe redirects back to
   `${FRONTEND_URL}/app?tab=subscription&checkout_session_id=...` for UI
   refresh.
7. Paid access is not granted from that redirect. Stripe sends signed webhook
   events to `POST /billing/webhook`.
8. The backend verifies `Stripe-Signature`, retrieves/syncs the Stripe
   subscription, and upserts the `subscriptions` row.
9. `active=true` only for Stripe statuses `active` and `trialing`.
10. CV quota code treats `users.is_unlimited` or an active subscription as paid
    access.

Stripe references:

- https://docs.stripe.com/billing/subscriptions/build-subscriptions
- https://docs.stripe.com/billing/subscriptions/webhooks
- https://docs.stripe.com/webhooks
- https://docs.stripe.com/customer-management/integrate-customer-portal

## Local setup

Backend:

```bash
cd cv-generator-be
cp .env.example .env
```

Fill:

```text
FRONTEND_URL=http://localhost:5173
STRIPE_SECRET_KEY=sk_test_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
STRIPE_PRO_PRICE_ID=price_xxx
```

Frontend:

```bash
cd cv-generator-fe
cp .env.example .env
```

Fill:

```text
VITE_API_BASE_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_xxx
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_xxx
```

Run:

```bash
cd cv-generator-be
make db-up
make migrate
make dev
```

In a separate terminal, force IPv4 and forward only the billing events the app
handles:

```bash
stripe listen \
  --forward-to 127.0.0.1:8000/billing/webhook \
  --events checkout.session.completed,customer.subscription.created,customer.subscription.updated,customer.subscription.deleted,invoice.paid,invoice.payment_failed
```

Copy the printed `whsec_...` into backend `.env`, restart the backend, then run:

```bash
cd cv-generator-fe
npm run dev
```

Test checkout with card `4242 4242 4242 4242`, a future expiry, and any
CVC/ZIP. Confirm one row appears in `subscriptions`, the Subscription tab shows
active, and `/cv/quota` returns paid limits.

## Production setup

Backend deploy:

```bash
cd cv-generator-be/infra
cdk deploy \
  --parameters FrontendUrl=https://hireable.vericodehq.com \
  --parameters StripeProPriceId=price_live_xxx
```

AWS Secrets Manager must contain:

```text
cv-generator/clerk-secret-key=sk_live_xxx
cv-generator/clerk-jwt-key=<Clerk JWT public key>
cv-generator/openai-api-key=sk-proj_xxx
cv-generator/stripe-secret-key=sk_live_xxx
cv-generator/stripe-webhook-secret=whsec_xxx
```

Cloudflare frontend build variables:

```text
VITE_API_BASE_URL=https://api.vericodehq.com
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxx
```

Stripe live webhook endpoint:

```text
https://api.vericodehq.com/billing/webhook
```

Subscribe it to:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

## You still need to do manually

- Create the Stripe test and live Product/Price.
- Configure Stripe Customer Portal in test and live mode.
- Copy the local Stripe CLI `whsec_...` into backend `.env`.
- Put live Stripe and Clerk secrets into AWS Secrets Manager.
- Put frontend `VITE_*` values into Cloudflare before building.
- Create the live Stripe webhook endpoint and copy its `whsec_...` into AWS.
- Run one local checkout and one production checkout, then verify the
  `subscriptions` row and paid quota access.
