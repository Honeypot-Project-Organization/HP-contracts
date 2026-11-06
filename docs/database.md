# MongoDB contract (database `honeypot`, Atlas M0)

Owned by the backend repo (`app/database.py`, `app/routers/ingest.py`, `app/geo.py`, `app/models/`).
Other repos must not write to these collections. Indexes are created at API start (`create_indexes`).

| Collection | `_id` | Fields (besides `_id`) | Indexes | Lifetime |
|---|---|---|---|---|
| `sessions` | Cowrie session id (string) | `src_ip`, `src_port`, `dst_port`, `protocol` (`ssh`/`telnet`), `start_time`, `end_time`, `duration_seconds`, `login_success`, `username`, `password`, `command_count`, `download_count`, `client_version`, `status` (`open`/`closed`) | `src_ip`; `start_time` desc; `src_ip`+`start_time` desc | kept |
| `auth_attempts` | ObjectId | `session_id`, `src_ip`, `username`, `password`, `success`, `timestamp` | `session_id`; `src_ip`+`timestamp` desc | kept |
| `commands` | ObjectId | `session_id`, `src_ip`, `timestamp`, `input`, `cmd_key` (sha256 of the trimmed text, first 24 hex) | `session_id`+`timestamp`; `cmd_key`+`timestamp` desc; `src_ip`+`timestamp` desc; `timestamp` desc | kept |
| `downloads` | ObjectId | `session_id`, `src_ip`, `timestamp`, `url`, `filename`, `sha256`, `size_bytes` | `session_id`; `sha256`; `src_ip`+`timestamp` desc | kept |
| `ip_intel` | the IP address (string) | `first_seen`, `last_seen`, `total_sessions`, `total_commands`, `total_auth_attempts`, `successful_logins`, `threat_score`, `updated_at`, `geo` (optional) | `last_seen` desc; `first_seen` desc; `total_sessions` desc; `geo.country_code` | kept |
| `raw_events` | SHA-256 of the event content | `session_id`, `eventid`, `received_at`, `raw` (sanitized copy) | `session_id`; `eventid`; **TTL on `received_at`** | **expires after `RAW_EVENT_RETENTION_DAYS` (default 7)**; `0` keeps forever |
| `admins` | ObjectId | `username` (unique), `password_hash` (bcrypt), `created_at` | `username` unique | one document, created only by `scripts/create_admin.py` |
| `geoip_meta` | `"city"` or `"asn"` | `version`, `chunks`, `size`, `sha256`, `uploaded_at`, `source` | none | replaced on each upload |
| `geoip_chunks` | `"<kind>:<version>:<n>"` | `kind`, `version`, `n`, `data` (binary, <=4 MB) | none | old versions deleted after an upload |

Notes
- MITRE ATT&CK tags: `sessions.techniques`, `ip_intel.techniques` and `commands.techniques` (+ `commands.rules_version`)
  are arrays of technique ids (`^T\d{4}(\.\d{3})?$`). Names and tactics are not stored; they come from `app/mitre.py`
  (`CATALOG`). Indexes: `commands(techniques, timestamp desc)`, `sessions(techniques, start_time desc)`,
  `ip_intel(techniques, last_seen desc)`. Collection `app_meta` holds `{_id:"mitre", version}` so the backfill runs once
  per `RULES_VERSION`; `scripts/backfill.py --rebuild-mitre` drops all tags and recomputes them.
- Only `raw_events` expires. Sessions, commands, IPs and locations are kept.
- `ip_intel.geo` has the shape in `schemas/api/attacker.schema.json` (`$defs.geo`). It is written once per
  IP, on the IP's first `cowrie.session.connect` or when the dashboard first lists an older IP, and only if
  a location database was uploaded. `scripts/upload_geoip.py --relookup` removes every `geo` so IPs are
  looked up again.
- `threat_score` is stored (default 0.0) but nothing computes it yet.
- Timestamps are written as UTC datetimes. Older rows may hold ISO strings; `scripts/migrate_timestamps.py`
  converts them, and `/api/stats/daily` handles both.
- The IP-location databases themselves (`.mmdb`) are never committed to git: DB-IP Lite is CC BY, and the
  dashboard footer carries the required attribution link (`https://db-ip.com`).

`scripts/backfill.py` (also run in the background when the API starts) fills `commands.cmd_key`, missing
`sessions.duration_seconds` (closing time minus start time) and `ip_intel.geo` on rows stored by earlier versions.
