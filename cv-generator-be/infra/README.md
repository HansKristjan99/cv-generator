
# CV Generator Backend Infrastructure

CDK stack for the FastAPI backend, RDS Postgres, ECS Fargate service, and
Secrets Manager placeholders.

## Deploy

Deploy with the live Stripe Price ID and frontend URL:

```bash
cd cv-generator-be/infra
cdk deploy \
  --parameters FrontendUrl=https://hireable.vericodehq.com \
  --parameters StripeProPriceId=price_live_xxx
```

The service runs Alembic before starting Uvicorn, so deploying the backend
applies the `subscriptions` migration automatically.

## Required Secrets Manager values

Update these generated placeholder secrets before using production:

| Secret | Value |
| --- | --- |
| `cv-generator/clerk-secret-key` | Clerk live secret key |
| `cv-generator/clerk-jwt-key` | Clerk JWT public key |
| `cv-generator/openai-api-key` | OpenAI API key |
| `cv-generator/stripe-secret-key` | Stripe live secret key |
| `cv-generator/stripe-webhook-secret` | Stripe live webhook endpoint signing secret |

Example:

```bash
aws secretsmanager update-secret \
  --secret-id cv-generator/stripe-secret-key \
  --secret-string "sk_live_xxx" \
  --region eu-north-1 \
  --profile hans-admin
```

## Stripe webhook

Create the live webhook endpoint in Stripe:

```text
https://api.vericodehq.com/billing/webhook
```

Subscribe to:

- `checkout.session.completed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`

Copy the `whsec_...` signing secret into
`cv-generator/stripe-webhook-secret` and force a new ECS deployment if the
secret changed after the service was already running.
