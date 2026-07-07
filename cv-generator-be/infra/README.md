
# CV Generator Backend Infrastructure

CDK stack for the FastAPI backend, RDS Postgres, ECS Fargate service, and
Secrets Manager placeholders.

## Architecture (cost-optimized)

The stack is deliberately built around the cheapest components that can still
run the app 24/7:

- **No ALB.** Ingress is a Cloudflare Tunnel: a `cloudflared` sidecar in the
  Fargate task makes an outbound connection to Cloudflare, which terminates
  TLS for `api.vericodehq.com` and forwards requests to the API container
  over `localhost:8000`. Nothing in the VPC accepts inbound traffic.
- **No NAT gateway.** The task runs in a public subnet with a public IP for
  outbound calls (OpenAI, Stripe, Clerk, ECR, Secrets Manager). Its security
  group has no inbound rules.
- **Fargate Spot**, one 0.25 vCPU / 1 GB task. Spot is ~70% cheaper; if AWS
  reclaims the task, ECS starts a replacement within a couple of minutes.
- **RDS `db.t4g.micro`** (Graviton) on gp3 storage, single-AZ, in isolated
  private subnets reachable only from the ECS tasks and CloudShell.

Approximate monthly cost (eu-north-1): ~$3 Fargate Spot, ~$4 public IPv4,
~$12 RDS instance, ~$9 RDS storage (100 GB gp3), ~$3 Secrets Manager —
roughly **$30/month**, versus ~$100 for the previous ALB + NAT + on-demand
design.

> Storage note: the database was created with CDK's default 100 GB and RDS
> cannot shrink volumes in place. If you ever recreate the database (pg_dump,
> destroy, restore), set `allocated_storage=20` on the `DatabaseInstance` to
> save another ~$7/month.

## One-time Cloudflare Tunnel setup

The API is only reachable once the tunnel token is configured:

1. In the Cloudflare dashboard (Zero Trust → Networks → Tunnels) create a
   tunnel named e.g. `cv-generator-api` and copy its token (`eyJ...`).
2. Deploy the stack (below), then store the token:

   ```bash
   aws secretsmanager update-secret \
     --secret-id cv-generator/cloudflare-tunnel-token \
     --secret-string "eyJ..." \
     --region eu-north-1 \
     --profile hans-admin
   ```

3. In the tunnel's **Public Hostname** config add:
   `api.vericodehq.com` → service `http://localhost:8000`.
   Cloudflare creates the DNS record for you — delete any old CNAME pointing
   at the retired load balancer first.
4. Restart the service so it picks up the token:

   ```bash
   aws ecs update-service --cluster <ClusterName output> \
     --service <ServiceName output> --force-new-deployment \
     --region eu-north-1 --profile hans-admin
   ```

The Stripe webhook URL (`https://api.vericodehq.com/billing/webhook`) and the
frontend `VITE_API_BASE_URL` are unchanged — only the path behind the
hostname changed.

## Deploy

Deploy with the live Stripe Price ID and frontend URL:

```bash
cd cv-generator-be/infra
cdk deploy \
  --parameters FrontendUrl=https://hireable.vericodehq.com \
  --parameters StripeProPriceId=price_live_xxx
```

The service runs Alembic before starting Uvicorn, so deploying the backend
applies migrations automatically. The `cloudflared` sidecar only starts
forwarding once the API container reports healthy, so rolling deployments
don't route traffic to a task that isn't ready.

### Migrating from the ALB/NAT version of this stack

The first deploy of this design deletes the load balancer and NAT gateway and
moves the ECS tasks to the public subnets. The RDS instance, its subnets, and
all existing secrets are kept in place (the instance class change to
`db.t4g.micro` causes a short DB restart). Expect API downtime from the moment
the ALB is removed until steps 1–4 above are completed, so have the tunnel
token ready before deploying.

## Required Secrets Manager values

Update these generated placeholder secrets before using production:

| Secret | Value |
| --- | --- |
| `cv-generator/clerk-secret-key` | Clerk live secret key |
| `cv-generator/clerk-jwt-key` | Clerk JWT public key |
| `cv-generator/openai-api-key` | OpenAI API key |
| `cv-generator/stripe-secret-key` | Stripe live secret key |
| `cv-generator/stripe-webhook-secret` | Stripe live webhook endpoint signing secret |
| `cv-generator/cloudflare-tunnel-token` | Cloudflare Tunnel token for `api.vericodehq.com` |

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
