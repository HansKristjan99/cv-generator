# Deploying the frontend to Cloudflare Pages

## How requests work in production

```
Browser → https://cv-generator.pages.dev/api/cv/generate/
              ↓  Pages Function (functions/api/[[path]].js)
          http://<ALB_DNS>/cv/generate/   ← AWS Fargate backend
```

All `/api/*` requests are proxied at the Cloudflare edge by the Pages Function.  
The browser only ever talks to your Pages domain — no CORS changes needed on the backend.

---

## Prerequisites

- AWS backend deployed (`cdk deploy` completed in `cv-generator-be/infra/`)
- A Cloudflare account
- Your Clerk publishable key (starts with `pk_live_` or `pk_test_`)

---


## Step 1 — Note the CDK outputs

After `cdk deploy` prints something like:

```
Outputs:
CvGeneratorBeStack.LoadBalancerDNS = CvGeneratorBeStack-ApiService-xxxx.eu-north-1.elb.amazonaws.com
CvGeneratorBeStack.DatabaseEndpoint = cvgenerator-database-xxxx.eu-north-1.rds.amazonaws.com
```

Save the `LoadBalancerDNS` value — that is your `BACKEND_URL`.

---

## Step 2 — Create the Cloudflare Pages project

1. Log in to [dash.cloudflare.com](https://dash.cloudflare.com)
2. **Workers & Pages → Create → Pages → Connect to Git**
3. Select your `cv-generator` repository
4. Set build configuration:

   | Setting | Value |
   |---|---|
   | Framework preset | Vite |
   | Build command | `npm run build` |
   | Build output directory | `dist` |
   | Root directory | `cv-generator-fe` |

5. Add environment variables (under **Environment variables → Production**):

   | Variable | Value |
   |---|---|
   | `VITE_CLERK_PUBLISHABLE_KEY` | Your Clerk publishable key |
   | `BACKEND_URL` | The `LoadBalancerDNS` value from Step 1 (no trailing slash) |

6. Click **Save and Deploy**.

Cloudflare will build the project and deploy it.  Note the `.pages.dev` URL it assigns — you need it for the next steps.

---

## Step 3 — Manual deploy via Wrangler CLI (alternative to Step 2)

If you prefer the CLI:

```bash
cd cv-generator-fe

# Build (Clerk key is embedded at build time)
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx npm run build

# First-time project creation + deploy
npx wrangler pages deploy dist --project-name cv-generator-fe

# Set BACKEND_URL as a secret (paste ALB DNS when prompted)
npx wrangler pages secret put BACKEND_URL --project-name cv-generator-fe
```

For subsequent deploys just run `npm run build && npx wrangler pages deploy dist --project-name cv-generator-fe`.

---

## Step 4 — Update Clerk settings

In your [Clerk dashboard](https://dashboard.clerk.com):

1. Open your application → **Domains**
2. Add your Pages URL, e.g. `https://cv-generator.pages.dev`

---

## Step 5 — Update CLERK_AUTHORIZED_PARTIES on the backend

The backend validates that JWT tokens come from allowed frontend origins.  
Now that you know the Pages URL, update the secret:

```bash
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-authorized-parties \
  --secret-string "https://cv-generator.pages.dev,http://localhost:5173" \
  --region eu-north-1 \
  --profile hans-admin
```

Then force a new ECS deployment so the container picks up the new value:

```bash
aws ecs update-service \
  --cluster CvGeneratorBeStack-ClusterEB0386A7-xxxx \
  --service CvGeneratorBeStack-ApiServicexxxx \
  --force-new-deployment \
  --region eu-north-1 \
  --profile hans-admin
```

(Find the exact cluster and service names in the ECS console or CloudFormation outputs.)

---

## Step 6 — Update the remaining placeholder secrets

The CDK stack created three secrets with `PLACEHOLDER` values.  
Set the real values before the app is usable:

```bash
# Clerk secret key  (Settings → API keys in the Clerk dashboard)
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-secret-key \
  --secret-string "sk_live_xxxx" \
  --region eu-north-1 --profile hans-admin

# Clerk JWT public key  (Settings → API keys → Show JWT public key)
aws secretsmanager update-secret \
  --secret-id cv-generator/clerk-jwt-key \
  --secret-string "-----BEGIN PUBLIC KEY-----\nMIIB..." \
  --region eu-north-1 --profile hans-admin

# OpenAI API key  (platform.openai.com → API keys)
aws secretsmanager update-secret \
  --secret-id cv-generator/openai-api-key \
  --secret-string "sk-proj-xxxx" \
  --region eu-north-1 --profile hans-admin
```

After updating all secrets, force another ECS deployment (Step 5 command above).

---

## Re-deploying the frontend

Every time you push to the connected branch Cloudflare rebuilds automatically.  
For a manual redeploy: make a commit, or click **Retry deployment** in the Pages dashboard.

---

## Switching your local dev to hit the deployed backend

```bash
# Create once (gitignored)
echo "API_BASE_URL=http://CvGeneratorBeStack-ApiService-xxxx.eu-north-1.elb.amazonaws.com" \
  > cv-generator-fe/.env.remote

# Then run:
cd cv-generator-fe && npm run dev:remote
```

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| API calls return 502/504 | `BACKEND_URL` wrong or ALB not reachable — check Pages Function logs |
| Clerk sign-in fails | Pages URL not in Clerk **Domains**, or `VITE_CLERK_PUBLISHABLE_KEY` wrong |
| Auth errors after sign-in | `CLERK_AUTHORIZED_PARTIES` not updated (Step 5) |
| `/app` returns 404 on hard refresh | `public/_redirects` not in the build output — confirm `dist/_redirects` exists |
| Backend starts but crashes | Secrets still have `PLACEHOLDER` values — complete Step 6 |
