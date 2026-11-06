# Changelog

## 1.2.0
- New MITRE ATT&CK endpoints under `/api/mitre` (catalog, summary, technique detail, daily, linked commands/IPs/sessions).
- `technique` filter on `/api/sessions`, `/api/ips`, `/api/commands/groups`.
- `techniques` (optional array of ids) on sessions, attackers, commands and command groups.
- Backwards compatible: new fields and parameters are optional.

## 1.1.0
- Lists are paged, filtered and sorted on the server: `/api/sessions` and `/api/ips` gain `q`, `date_from`,
  `date_to`, `sort`, `order` (plus `login` and `date_field`) and return `X-Total-Count`.
- New: `/api/stats/top-countries`, `/api/geo/points` (over all IPs), `/api/commands/groups`
  (+ `/{key}`, `/{key}/occurrences`).
- `command-list` rows carry `cmd_key`. Ingest accepts `duration_ms`.
- Existing 1.0.0 consumers keep working (the new parameters are optional).

## 1.0.0
- First split of the project into backend / frontend / assets / contracts.
- Describes the API as of: PyMongo async backend, `/api/geo/status`, `ip_intel.geo`, `raw_events` retention
  default 7 days.
