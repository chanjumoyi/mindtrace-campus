#!/usr/bin/env python3
"""Run C-owned verification without touching A/B endpoints or business code.

Code-only checks are mandatory. Maven backend tests and live E2E are executed when
available/requested and are reported explicitly instead of being silently treated as passed.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPORT = ROOT / "deliverables/test-report/c-verification-report.json"


def run_check(name: str, command: list[str], *, required: bool = True, cwd: pathlib.Path = ROOT) -> dict[str, Any]:
    started = time.time()
    print("+", " ".join(command))
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return {
        "name": name,
        "status": "PASSED" if completed.returncode == 0 else "FAILED",
        "required": required,
        "exitCode": completed.returncode,
        "durationMs": round((time.time() - started) * 1000),
        "command": command,
        "stdoutTail": completed.stdout[-4000:],
        "stderrTail": completed.stderr[-4000:],
    }


def skipped(name: str, reason: str, *, required: bool) -> dict[str, Any]:
    return {"name": name, "status": "SKIPPED", "required": required, "reason": reason}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live-e2e", action="store_true", help="run tests/e2e/run_c_e2e.py against XINJI_BASE_URL")
    parser.add_argument("--require-backend", action="store_true", help="fail when Maven is unavailable or backend tests fail")
    parser.add_argument("--require-live-e2e", action="store_true", help="require and run live E2E")
    args = parser.parse_args()
    if args.require_live_e2e:
        args.live_e2e = True

    checks: list[dict[str, Any]] = []
    checks.append(run_check("Generate C assets", [sys.executable, "kingdee/tools/build_c_assets.py"]))
    checks.append(run_check("Contract and security static acceptance", [sys.executable, "tests/run_c_static_acceptance.py"]))
    checks.append(run_check("Java 8 plugin core self-test", ["bash", "kingdee/java-plugin/scripts/verify-java8.sh"]))
    checks.append(run_check("KWC build, unit tests and package", ["npm", "run", "package"], cwd=ROOT / "kingdee/kwc-common"))

    mvn = shutil.which("mvn")
    if mvn:
        checks.append(run_check("Spring Boot integration tests", [mvn, "-f", "local/backend/pom.xml", "test"], required=args.require_backend))
    else:
        checks.append(skipped("Spring Boot integration tests", "mvn is not installed; run on a Maven-enabled machine or CI", required=args.require_backend))

    if args.live_e2e:
        checks.append(run_check("Live C E2E", [sys.executable, "tests/e2e/run_c_e2e.py"], required=args.require_live_e2e))
    else:
        checks.append(skipped("Live C E2E", "not requested; start Docker/tenant environment and rerun with --live-e2e", required=args.require_live_e2e))

    required_failures = [c for c in checks if c.get("required") and c["status"] != "PASSED"]
    executed_failures = [c for c in checks if c["status"] == "FAILED"]
    report = {
        "suite": "C complete verification",
        "generatedAtEpochMs": int(time.time() * 1000),
        "scope": "C public foundation, AI gateway reliability, KWC, Kingdee adapter and deployment assets only",
        "codeChecksPassed": not executed_failures,
        "fullEnvironmentVerified": all(c["status"] == "PASSED" for c in checks),
        "checks": checks,
        "requiredFailures": [c["name"] for c in required_failures],
        "note": "SKIPPED is never equivalent to PASSED. Tenant-native export and clean-tenant installation require authenticated platform actions."
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(REPORT)
    return 1 if required_failures or executed_failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
