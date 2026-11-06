# Configuration contract: environment variables and values that must match across repos

## Backend (`backend/.env.example`, or the API host's environment)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `MONGO_URI` | yes | none | Atlas string; user needs `readWrite` on `honeypot` only |
| `DB_NAME` | no | `honeypot` | |
| `INGEST_API_KEY` | yes | none | >= 32 chars, not a placeholder; **must differ** from `JWT_SECRET_KEY` |
| `JWT_SECRET_KEY` | yes | none | >= 32 chars, not a placeholder |
| `JWT_EXPIRE_MINUTES` | no | `60` | |
| `CORS_ALLOWED_ORIGIN` | no | `http://localhost:5173` | exact dashboard origin, no trailing slash, never `*` |
| `TRUSTED_PROXY_HOPS` | no | `0` | proxies in front of the API that append to `X-Forwarded-For`; see below |
| `RAW_EVENT_RETENTION_DAYS` | no | `7` | `0` = keep raw events forever |
| `ENABLE_API_DOCS` | no | `false` | `/docs`, `/redoc`, `/openapi.json` |

The API refuses to start when a required value is missing, a secret is short or a placeholder, or the two
secrets are equal.

## Honeypot shipper (`backend/cowrie-vps/.env`)

| Variable | Required | Default | Notes |
|---|---|---|---|
| `INGEST_URL` | yes | none | `https://<api>/ingest`; plain HTTP is refused unless `ALLOW_INSECURE_HTTP=1` (dev only) |
| `INGEST_API_KEY` | yes | none | same value as the API's |
| `INGEST_BATCH_URL` | no | `<INGEST_URL>/batch` | |
| `SHIPPER_STATE_PATH` | no | `/state/offset.json` | |

## Frontend (`frontend/.env`, read at **build** time)

| Variable | Notes |
|---|---|
| `VITE_API_BASE_URL` | the API base URL, no trailing slash; baked into the bundle, so rebuild after changing it |

## Values that must agree across repos

| What | Where it lives | Must equal |
|---|---|---|
| Ingest key | backend `INGEST_API_KEY` | backend shipper (`cowrie-vps`) `INGEST_API_KEY` |
| Ingest endpoint | backend shipper (`cowrie-vps`) `INGEST_URL` | backend `POST /ingest` on its public HTTPS URL |
| Dashboard origin | backend `CORS_ALLOWED_ORIGIN` | the URL where the frontend is hosted (for example `https://<project>.web.app`) |
| API URL (twice in the frontend) | frontend `VITE_API_BASE_URL` **and** `firebase.json` CSP `connect-src` | the backend's public URL |
| Event fields | Cowrie version pinned in `backend/cowrie-vps/cowrie/Dockerfile` | what `schemas/ingest/cowrie-event.schema.json` and backend `CowrieEvent` accept |
| Response shapes | backend routers | `schemas/api/*` and the frontend `src/lib/normalize.js` |
| Location attribution | frontend footer link to `https://db-ip.com` | required by DB-IP's licence while DB-IP data is used |

## `TRUSTED_PROXY_HOPS`

Controls how the rate limiter finds the client IP. `0` uses the direct TCP peer. `N` uses the Nth entry
from the right of `X-Forwarded-For`. Behind a platform load balancer with `0`, every visitor shares one
rate-limit bucket. With `N` greater than the real number of proxies, clients can forge the header and dodge
limits. Deploy, call `GET /api/debug/client-ip`, and pick the smallest `N` for which `rate_limit_key`
equals your real public IP.
