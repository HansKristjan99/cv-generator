# Deploying the frontend to Cloudflare

## How requests work

The browser calls the FastAPI backend directly with `VITE_API_BASE_URL`.

```
Browser -> https://hireable.vericodehq.com
Browser -> https://api.vericodehq.com/billing/checkout_session/
```

There is no Vite proxy, Cloudflare Pages Function proxy, or `BACKEND_URL`
runtime proxy in the current setup. Cloudflare only serves the built frontend
and the worker adds security headers plus SPA fallback.

## Prerequisites

- AWS backend deployed from `cv-generator-be/infra/`
- Public API domain available, currently `https://api.vericodehq.com`
- Frontend domain available, currently `https://hireable.vericodehq.com`
- Clerk publishable key
- Stripe publishable key for the same Stripe mode as the backend secret key

## Cloudflare environment variables

Set these under **Workers & Pages -> your project -> Settings -> Variables**.

| Variable | Production value |
| --- | --- |
| `VITE_API_BASE_URL` | `https://api.vericodehq.com` |
| `VITE_CLERK_PUBLISHABLE_KEY` | Clerk live publishable key |
| `VITE_STRIPE_PUBLISHABLE_KEY` | Stripe live publishable key |

These values are embedded at build time. Rebuild the frontend after changing
any of them.

## Pages setup

Use this build configuration:

| Setting | Value |
| --- | --- |
| Framework preset | Vite |
| Build command | `npm run build` |
| Build output directory | `dist` |
| Root directory | `cv-generator-fe` |

## Wrangler deploy

```bash
cd cv-generator-fe
npm run build
npx wrangler deploy
```

For a one-off build with explicit env values:

```bash
cd cv-generator-fe
VITE_API_BASE_URL=https://api.vericodehq.com \
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx \
VITE_STRIPE_PUBLISHABLE_KEY=pk_live_xxx \
npm run build
npx wrangler deploy
```

## Backend settings production must match

The backend container must have:

| Variable | Production value |
| --- | --- |
| `FRONTEND_URL` | `https://hireable.vericodehq.com` |
| `CLERK_AUTHORIZED_PARTIES` | `http://localhost:5173,https://hireable.vericodehq.com` |
| `STRIPE_PRO_PRICE_ID` | Stripe live recurring `price_...` |

The backend also needs these AWS Secrets Manager values:

| Secret | Value |
| --- | --- |
| `cv-generator/clerk-secret-key` | Clerk live secret key |
| `cv-generator/clerk-jwt-key` | Clerk JWT public key |
| `cv-generator/openai-api-key` | OpenAI API key |
| `cv-generator/stripe-secret-key` | Stripe live secret key |
| `cv-generator/stripe-webhook-secret` | Stripe live webhook signing secret |

## Stripe setup

In Stripe live mode:

1. Create the Pro product and a recurring price.
2. Copy the live `price_...` into the backend CDK deploy parameter
   `StripeProPriceId`.
3. Configure the Customer Portal.
4. Create a webhook endpoint at:

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

Copy the endpoint signing secret, `whsec_...`, into
`cv-generator/stripe-webhook-secret`.

## Deploy order

1. Deploy the backend so migrations run and the API has the live Stripe config.
2. Deploy the frontend with the production `VITE_*` variables.
3. Sign in, open `/app?tab=subscription`, complete one checkout, and confirm
   the `subscriptions` row plus `/cv/quota` paid access.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Browser calls the frontend domain for API requests | `VITE_API_BASE_URL` was missing at build time |
| Billing says publishable key is not configured | `VITE_STRIPE_PUBLISHABLE_KEY` missing at build time |
| Checkout creation returns 500 | Backend missing `STRIPE_SECRET_KEY` or `STRIPE_PRO_PRICE_ID` |
| Checkout succeeds but app stays free | Stripe webhook missing, wrong `whsec_...`, or backend not deployed with migration |
| Portal open fails | Stripe Customer Portal is not configured in that Stripe mode |
| Auth errors after sign-in | `CLERK_AUTHORIZED_PARTIES` does not include the frontend origin |
