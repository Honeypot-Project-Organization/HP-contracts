# HTTP API contract

Source of truth for the shapes: `schemas/`. Source of truth for behaviour: the backend repo
(`app/routers/*.py`). This page was written by reading that code and the backend tests; it was not
generated from a running server.

Base URL: the API host (for example `https://<name>.fastapicloud.dev`). All bodies are JSON.
Datetimes are ISO 8601 strings, UTC.

## Authentication

| Surface | How | Failure |
|---|---|---|
| Honeypot shipper -> `/ingest*` | header `X-Ingest-Key: <INGEST_API_KEY>` (constant-time compare) | wrong key: `401 {"detail":"Invalid ingest key"}`; header missing: `422` |
| Dashboard -> `/api/*` | header `Authorization: Bearer <JWT>` from `POST /login` | `401 {"detail":"Could not validate credentials"}` |

JWT: HS256, issuer `honeypot-api`, audience `honeypot-dashboard`, claims `sub iat exp iss aud`, lifetime
`JWT_EXPIRE_MINUTES` (default 60). A token stops working if the admin account is deleted, or re-created
(`create_admin.py`) after the token was issued. The dashboard keeps the token in `sessionStorage` and
clears it on any `401`.

## Routes

| Method & path | Auth | Request | Success response |
|---|---|---|---|
| `GET /health` | none | | `200` / `503` `health` |
| `POST /login` | none, **10/min per client IP** | `login-request` | `200` `login-response`; bad credentials `401 {"detail":"Invalid username or password"}` |
| `POST /ingest` | ingest key, 120/min | one `cowrie-event` | `202` `event-response`; malformed `422 {"detail":"<summary>"}` |
| `POST /ingest/batch` | ingest key, 120/min | `batch-request` (<=200 events) | `202` `batch-response`; >200 events `413` |
| `GET /api/stats` | JWT | | `stats` |
| `GET /api/stats/daily?days=30` | JWT | `days` 1-365 | `daily-stats` |
| `GET /api/stats/top-credentials?limit=10` | JWT | `limit` 1-100 | `top-credentials` |
| `GET /api/stats/top-countries?limit=10` | JWT | `limit` 1-50 | `top-countries` (computed over ALL IPs) |
| `GET /api/geo/points` | JWT | | `geo-points` (all located IPs, grouped into 0.5-degree cells) |
| `GET /api/sessions` | JWT | `limit` 1-500 (50), `skip` 0-100000, `q` (IP contains), `login` `all`/`granted`/`denied`, `date_from`, `date_to` (ISO 8601; no zone = UTC; applied to `start_time`), `sort` (`start_time` default, `src_ip`, `duration_seconds`, `login_success`, `username`, `command_count`), `order` `asc`/`desc` | `session-list`; filters apply to ALL sessions; **`X-Total-Count`** = matches |
| `GET /api/sessions/{id}` | JWT | `id` matches `^[A-Za-z0-9_-]{1,64}$` | `session`; unknown `404 {"detail":"Session not found"}` |
| `GET /api/sessions/{id}/commands?limit=500` | JWT | | `command-list` (oldest first) |
| `GET /api/ips` | JWT | `limit` 1-500 (100), `skip`, `q` (IP contains), `date_from`, `date_to`, `date_field` `last_seen` (default) / `first_seen`, `sort` (`last_seen` default, `ip`, `total_sessions`, `successful_logins`, `total_auth_attempts`, `total_commands`, `first_seen`), `order` | `attacker-list`; filters apply to ALL IPs; **`X-Total-Count`** = matches |
| `GET /api/ips/{ip}` | JWT | `ip` matches `^[0-9A-Fa-f:.]{2,45}$` | `attacker`; unknown `404 {"detail":"IP not found"}` |
| `GET /api/ips/{ip}/sessions` | JWT | `limit`, `skip` | `session-list` |
| `GET /api/ips/{ip}/commands` | JWT | `limit`, `skip` | `command-list` (newest first) |
| `GET /api/commands?limit=100&skip=0` | JWT | | `command-list` (newest first); `X-Total-Count` = all commands |
| `GET /api/commands/groups` | JWT | `limit`, `skip`, `q` (text contains, case-insensitive), `sort` (`count` default, `ip_count`, `session_count`, `last_ts`, `first_ts`, `text`), `order` | `command-group-list`; grouping done in MongoDB over ALL commands; `X-Total-Count` = distinct commands |
| `GET /api/commands/groups/{key}` | JWT | `key` matches `^[0-9a-f]{24}$` | `command-group`; unknown `404 {"detail":"Command not found"}` |
| `GET /api/commands/groups/{key}/occurrences` | JWT | `limit`, `skip` | `command-list` (newest first); `X-Total-Count` |
| `GET /api/mitre/catalog` | JWT | | `mitre-catalog` (every technique the rules can produce) |
| `GET /api/mitre/summary` | JWT | | `mitre-summary` (`total_ids` = total occurrences, `unique_ids`, `top`, `top_event`, `top_command`, all rows ranked by occurrences then IPs) |
| `GET /api/mitre/{id}` | JWT | `id` matches `^T\d{4}(\.\d{3})?$` | `mitre-technique` (rules/regex, counts, first/last seen); unknown and never seen `404` |
| `GET /api/mitre/{id}/daily?days=30` | JWT | `days` 1-365 | `mitre-daily` |
| `GET /api/mitre/{id}/commands`, `/ips`, `/sessions` | JWT | `limit`, `skip` | `command-list` / `attacker-list` / `session-list`; `X-Total-Count` |
| `GET /api/geo/status` | JWT | | `geo-status` |
| `GET /api/debug/client-ip` | JWT | | `client-ip-debug` (for choosing `TRUSTED_PROXY_HOPS`) |

**MITRE filter.** `/api/sessions`, `/api/ips` and `/api/commands/groups` accept `technique` (an ATT&CK id) and return only rows tagged with it. Tags are heuristic (regex rules on command text, plus connection/login events) and are not confirmed techniques.

**Paging.** List endpoints that take filters return the number of matching rows in the `X-Total-Count` response
header (exposed to browsers through CORS). Dates are UTC, inclusive at both ends. `date_from` later than `date_to`
is a `422`; an unknown `sort` is a `422`. Search text is matched literally (never as a regular expression).

Path or query values that fail validation return `422` (FastAPI's `detail` array). `/docs`, `/redoc` and
`/openapi.json` exist only when `ENABLE_API_DOCS=true`.

## Limits that clients must respect

- Request body <= 1,000,000 bytes -> otherwise `413 {"detail":"Payload too large"}` (also for chunked uploads).
- Batch <= 200 events. The shipper sends batches; the single-event route exists for testing.
- Rate limits are per client IP (see `TRUSTED_PROXY_HOPS` in `environment.md`): login 10/min, ingest 120/min.
  Exceeding them returns `429`.
- Free-text event fields are truncated to 4096 characters (plus `...[truncated]`), not rejected.
- Re-sending an event is safe: events are de-duplicated by a SHA-256 of their content
  (`duplicate` / `duplicates` in the responses).

## Which events change what

| `eventid` | Effect |
|---|---|
| `cowrie.session.connect` | creates/updates the session, counts a session on the IP, **looks up the IP's location once** |
| `cowrie.client.version` | sets `client_version` on the session |
| `cowrie.login.failed` / `cowrie.login.success` | adds an auth attempt; success also marks the session `login_success`, `username`, `password` |
| `cowrie.command.input` / `cowrie.command.failed` | adds a command, increments `command_count` |
| `cowrie.session.file_upload` / `cowrie.session.file_download` | adds a download, increments `download_count` |
| `cowrie.session.closed` | `status:"closed"`, `end_time`, `duration_seconds` from `duration` (seconds) or `duration_ms` / 1000; if neither is sent, closing time minus `start_time` |
| anything else matching `^cowrie\.[a-z0-9_.]{1,64}$` | stored only in `raw_events` |

Event ids containing a hyphen (for example `cowrie.direct-tcpip.request`) do not match that pattern and
are rejected with 422. The honeypot disables port forwarding, so Cowrie should not emit them.
An event without a `session` is stored in `raw_events` only.

## Response conventions

- `_id` is renamed: `id` for sessions and commands, `ip` for attackers.
- These are raw MongoDB documents; the API adds no response model, so extra fields can appear.
  Consumers must ignore unknown fields and treat everything except the identifier as optional.
- Every string that came from the honeypot (usernames, passwords, commands, client versions, URLs,
  file names) was typed by an attacker. Render as text only.
- `attacker.geo` is absent until the IP was looked up. `geo.found=false` means looked up but unknown.
