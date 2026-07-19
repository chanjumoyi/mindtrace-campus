#!/usr/bin/env python3
"""Build deterministic, C-only Kingdee import worksheets and Agent tool registration files."""
from __future__ import annotations
import csv, hashlib, json, pathlib, sys
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
DOMAIN_SOURCE = ROOT / "kingdee/domain-models/common-foundation-models.yaml"
TOOL_SOURCE = ROOT / "kingdee/agent-tools/tool-registration.yaml"
DOMAIN_OUT = ROOT / "kingdee/domain-models/generated"
TOOL_OUT = ROOT / "kingdee/agent-tools/generated"

def dump_json(path: pathlib.Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    domain = yaml.safe_load(DOMAIN_SOURCE.read_text(encoding="utf-8"))
    if domain.get("owner") != "C": raise SystemExit("domain source must be owned by C")
    models = domain.get("models") or []
    codes = [m["code"] for m in models]
    if len(codes) != len(set(codes)): raise SystemExit("duplicate model code")
    DOMAIN_OUT.mkdir(parents=True, exist_ok=True)
    TOOL_OUT.mkdir(parents=True, exist_ok=True)
    for stale in DOMAIN_OUT.glob("*"):
        if stale.is_file(): stale.unlink()
    for stale in TOOL_OUT.glob("*.registration.json"):
        stale.unlink()
    dump_json(DOMAIN_OUT / "common-foundation-models.import.json", domain)
    with (DOMAIN_OUT / "model-fields.import.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["model_code","model_name","source_table","field_code","field_type","length","required","unique","enum_values","data_level","owner"])
        for model in models:
            for field in model.get("fields", []):
                w.writerow([model["code"], model["name"], model.get("sourceTable", ""), field["code"], field["type"],
                            field.get("length", ""), field.get("required", False), field.get("unique", False),
                            "|".join(str(x) for x in field.get("values", [])), model.get("dataLevel", ""), "C"])
    with (DOMAIN_OUT / "role-permissions.import.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["model_code","role_code","permission"])
        for model in models:
            for role, permissions in (model.get("permissions") or {}).items():
                for permission in permissions: w.writerow([model["code"], role, permission])

    tools = yaml.safe_load(TOOL_SOURCE.read_text(encoding="utf-8"))
    c_tools = [t for t in tools.get("tools", []) if t.get("owner") == "C"]
    for tool in c_tools:
        schema_path = ROOT / tool["schemaFile"]
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        dump_json(TOOL_OUT / (tool["name"] + ".registration.json"), {
            "name": tool["name"], "description": tool["purpose"], "method": tool["method"],
            "path": tool["path"], "permission": tool["permission"], "idempotencyRequired": tool.get("idempotencyRequired", False),
            "inputSchema": schema,
        })
    schema_paths = sorted(ROOT / t["schemaFile"] for t in c_tools)
    manifest_paths = [DOMAIN_SOURCE, DOMAIN_OUT / "common-foundation-models.import.json", DOMAIN_OUT / "model-fields.import.csv",
                      DOMAIN_OUT / "role-permissions.import.csv", TOOL_SOURCE] + schema_paths + sorted(TOOL_OUT.glob("*.json"))
    manifest = {str(p.relative_to(ROOT)): sha256(p) for p in manifest_paths}
    dump_json(ROOT / "kingdee/generated-assets-manifest.json", manifest)
    print(f"Built {len(models)} C models and {len(c_tools)} C Agent tools")
    return 0

if __name__ == "__main__": sys.exit(main())
