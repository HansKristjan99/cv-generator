
# CV Generator Backend Infrastructure

CDK stack for the FastAPI backend, RDS Postgres, ECS Fargate service, and
Secrets Manager placeholders.

## Deploy

Deploy with the live Stripe Price ID and frontend URL:

```bash
cd cv-generator-be
./scripts/deploy.sh
```

The service runs Alembic before starting Uvicorn, so deploying the backend
applies the `subscriptions` migration automatically.

The deploy wrapper accepts these optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AWS_PROFILE` | `hans-admin` | AWS CLI profile used for deployment |
| `AWS_REGION` | `eu-north-1` | AWS region used for deployment |
| `FRONTEND_URL` | `https://hireable.vericodehq.com` | Frontend origin used for auth and Stripe return URLs |
| `PRODUCT_ID` | Live Pro price | Stripe recurring Price ID |

## Cost reduction rollout

The stack keeps the public ALB but removes the NAT Gateway. The API task runs in
public subnets with a public IP for outbound access; its security group still
accepts port `8000` traffic only from the ALB. RDS remains private on a
protected `db.t4g.micro` Postgres instance with 20 GiB of gp3 storage and seven
days of backups.

Check `/health`, ALB target health, sign-in, and a representative three-page PDF
generation after the deployment. The API task is intentionally trialing
`0.25 vCPU / 0.5 GiB`; revert it to `0.5 vCPU / 1 GiB` if rendering becomes
unreliable.

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
