# Deploying the frontend to Cloudflare Pages

## How requests work in production

```
Browser → https://hireable.vericodehq.com  (Cloudflare Worker, static assets)
       → https://api.vericodehq.com        (Cloudflare proxy → HTTP ALB → Fargate)
```

`VITE_API_BASE_URL` is baked into the build via `.env.production` —
no environment variables need to be set in the Cloudflare dashboard.
Cloudflare terminates TLS for `api.vericodehq.com` for free; the ALB
stays plain HTTP internally.

---

## Step 1 — Add the API subdomain in Cloudflare DNS

In **dash.cloudflare.com → vericodehq.com → DNS → Records → Add record**:

| Type | Name | Target | Proxy |
|---|---|---|---|
| CNAME | `api` | `<LoadBalancerDNS from cdk deploy output>` | **Proxied** (orange cloud) |

The orange cloud is required — Cloudflare issues the TLS cert for
`api.vericodehq.com` and forwards traffic to the HTTP ALB internally.

---

## Step 2 — Deploy the backend (`cdk deploy`)

```bash
cd cv-generator-be/infra
uv run cdk deploy --profile hans-admin
```

Note the `LoadBalancerDNS` output and use it as the CNAME target in Step 1.

---

## Step 3 — Update Clerk secrets in AWS

```bash
# Clerk secret key  (Configure → API keys in the Clerk dashboard)
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-secret-key \
  --secret-string "sk_live_xxxx" \
  --region eu-north-1 --profile hans-admin

# Clerk JWT public key  (Configure → API keys → Show JWT public key)
# Leave empty to use network verification via the secret key instead
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-jwt-key \
  --secret-string "" \
  --region eu-north-1 --profile hans-admin

# OpenAI API key
aws secretsmanager update-secret \
  --secret-id cv-generator/openai-api-key \
  --secret-string "sk-proj-xxxx" \
  --region eu-north-1 --profile hans-admin

# Allowed frontend origins for Clerk JWT validation
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-authorized-parties \
  --secret-string "https://hireable.vericodehq.com,http://localhost:5173" \
  --region eu-north-1 --profile hans-admin
```

Then force a new ECS deployment to pick up the updated secrets:

```bash
cluster=$(aws ecs list-clusters --region eu-north-1 --profile hans-admin \
  --query 'clusterArns[0]' --output text)
service=$(aws ecs list-services --cluster $cluster --region eu-north-1 \
  --profile hans-admin --query 'serviceArns[0]' --output text)
aws ecs update-service --cluster $cluster --service $service \
  --force-new-deployment --region eu-north-1 --profile hans-admin
```

---

## Step 4 — Create the Cloudflare Worker project

1. **dash.cloudflare.com → Workers & Pages → Create → Worker → Connect to Git**
2. Select the `cv-generator` repository
3. Set build configuration:

   | Setting | Value |
   |---|---|
   | Build command | `npm run build` |
   | Deploy command | `npx wrangler deploy` |
   | Root directory | `cv-generator-fe` |

4. Add one environment variable (build-time):

   | Variable | Value |
   |---|---|
   | `VITE_CLERK_PUBLISHABLE_KEY` | Your Clerk publishable key (`pk_live_...`) |

   No `BACKEND_URL` or `VITE_API_BASE_URL` needed — the backend URL is
   baked into the bundle via `.env.production`.

5. Click **Save and Deploy**.

---

## Step 5 — Add Clerk domain

In your [Clerk dashboard](https://dashboard.clerk.com) → **Domains** →
add `https://hireable.vericodehq.com`.

---

## Re-deploying

Push to `main` — Cloudflare rebuilds and deploys automatically.

---

## Local development

```bash
# Hit local Docker Compose backend
cd cv-generator-fe && npm run dev

# Hit the deployed backend at api.vericodehq.com
cd cv-generator-fe && npm run dev:remote
# (requires .env.remote with API_BASE_URL=https://api.vericodehq.com)
```

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| API calls fail with CORS error | `clerk-authorized-parties` secret missing `https://hireable.vericodehq.com` |
| `api.vericodehq.com` not reachable | CNAME not added or Cloudflare proxy not enabled (orange cloud) |
| Clerk sign-in fails | Domain not added in Clerk dashboard, or secrets still have `PLACEHOLDER` |
| `/app` returns 404 on hard refresh | Worker SPA fallback not working — check `worker.js` is deployed |
| Backend starts but crashes | Secrets still have `PLACEHOLDER` values — complete Step 3 |
