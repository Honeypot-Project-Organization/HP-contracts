# Honeypot contracts

The agreements between the four parts of the honeypot project. Nothing here runs in production; it is
the shared reference that the other repos are checked against.

| Repo | What it is |
|---|---|
| `backend` | FastAPI API: ingest, login, dashboard routes, IP geolocation |
| `frontend` | React dashboard (Firebase Hosting) |
| `assets` | Honeypot deployment: Cowrie image, log shipper, firewall, bait files, dev compose, setup guide, security notes |
| `contracts` | **this repo** |

Suggested layout on your machine (the dev compose file in `assets` expects `../backend`):
```
honeypot/
  backend/  frontend/  assets/  contracts/
```

## What is in here

- `schemas/ingest/` JSON Schemas for what the shipper sends to the API and what the API answers.
- `schemas/api/` JSON Schemas for login and every dashboard response.
- `docs/api.md` routes, authentication, limits, and which event changes what.
- `docs/database.md` MongoDB collections, fields, indexes and lifetimes.
- `docs/environment.md` every environment variable, and the values that must match across repos.
- `fixtures/` sample payloads (`valid/` must pass, `invalid/` must be rejected), listed in `manifest.json`.
- `scripts/validate.py` checks the schemas and fixtures against each other.

```
pip install jsonschema
python scripts/validate.py
```

## What this does and does not prove

`validate.py` shows the schemas are valid and agree with the fixtures. The schemas and docs were written by
reading the backend code and tests; they were not generated from a running API, and nothing yet checks the
backend against them automatically.

### Checking a live API
Fetch a real response and validate it, for example:
```
python - <<'PY'
import json, sys, urllib.request
from jsonschema import Draft202012Validator
req = urllib.request.Request("https://<api>/api/stats", headers={"Authorization": "Bearer <token>"})
data = json.load(urllib.request.urlopen(req))
schema = json.load(open("schemas/api/stats.schema.json"))
errors = list(Draft202012Validator(schema).iter_errors(data))
print("OK" if not errors else errors)
PY
```

## Changing a contract
1. Edit the schema/doc and add or update a fixture (and `manifest.json`).
2. Run `python scripts/validate.py`.
3. Change the backend, then the frontend (`src/lib/normalize.js`) and anything in `assets` that depends on it.
4. Add a line to `CHANGELOG.md`.
