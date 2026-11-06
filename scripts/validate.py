"""
Checks the contracts against their own fixtures.

  pip install jsonschema
  python scripts/validate.py

1. Every schema must itself be a valid JSON Schema.
2. Every fixture in fixtures/valid must validate against its schema.
3. Every fixture in fixtures/invalid must be REJECTED by its schema.
4. A batch of 201 events must be rejected (the API's 200-event limit).

This proves the schemas and fixtures agree with each other. It does not talk to
a running API; to check the API against the contract, validate real responses
with the same schemas (see README, "Checking a live API").
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent


def load(path: Path):
    with path.open() as f:
        return json.load(f)


def main() -> int:
    failures = []
    validators = {}
    for p in sorted((ROOT / "schemas").rglob("*.schema.json")):
        schema = load(p)
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"schema {p.relative_to(ROOT)} is not valid: {exc}")
            continue
        validators[f"{p.parent.name}/{p.name[:-len('.schema.json')]}"] = Draft202012Validator(schema)
    print(f"{len(validators)} schemas are valid JSON Schema")

    manifest = load(ROOT / "fixtures" / "manifest.json")
    ok = 0
    for kind in ("valid", "invalid"):
        for name, key in manifest[kind].items():
            if key not in validators:
                failures.append(f"{kind}/{name}: unknown schema '{key}'")
                continue
            errors = list(validators[key].iter_errors(load(ROOT / "fixtures" / kind / name)))
            if kind == "valid" and errors:
                failures.append(f"valid/{name} should pass {key} but: {errors[0].message}")
            elif kind == "invalid" and not errors:
                failures.append(f"invalid/{name} should FAIL {key} but passed")
            else:
                ok += 1
    on_disk = {k: {p.name for p in (ROOT / "fixtures" / k).glob("*.json")} for k in ("valid", "invalid")}
    for kind in on_disk:
        for stray in sorted(on_disk[kind] - set(manifest[kind])):
            failures.append(f"fixtures/{kind}/{stray} is not listed in manifest.json")
    print(f"{ok} fixtures behave as expected")

    event = load(ROOT / "fixtures" / "valid" / "event-connect.json")
    if not list(validators["ingest/batch-request"].iter_errors([event] * 201)):
        failures.append("a batch of 201 events should be rejected")
    if list(validators["ingest/batch-request"].iter_errors([event] * 200)):
        failures.append("a batch of 200 events should be accepted")

    for f in failures:
        print("FAIL:", f)
    print("OK" if not failures else f"{len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
