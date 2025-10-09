import json
import sys
from pathlib import Path

REPORT = Path("pip-audit-report.json")


def main() -> int:
    if not REPORT.exists():
        print("pip-audit did not produce a valid report (see pip-audit-report.json)")
        return 0
    try:
        data = json.loads(REPORT.read_text())
    except Exception:
        print("pip-audit did not produce a valid report (see pip-audit-report.json)")
        return 0

    vulns = 0
    pkgs = 0

    if isinstance(data, dict) and "dependencies" in data:
        for dep in data.get("dependencies", []) or []:
            vlist = dep.get("vulns") or dep.get("vulnerabilities") or []
            if vlist:
                pkgs += 1
                vulns += len(vlist)
    elif isinstance(data, dict) and "vulnerabilities" in data:
        vlist = [v for v in (data.get("vulnerabilities") or []) if isinstance(v, dict)]
        vulns = len(vlist)
        names = set()
        for v in vlist:
            pkg = (v.get("package") or v.get("dependency") or {}).get("name")
            if pkg:
                names.add(pkg)
        pkgs = len(names)
    else:
        print("no vulnerabilities found (see pip-audit-report.json)")
        return 0

    if vulns > 0:
        print(f"Found {vulns} known vulnerabilities in {pkgs} packages (see {REPORT.name})")
        return 1
    else:
        print(f"no vulnerabilities found (see {REPORT.name})")
        return 0


if __name__ == "__main__":
    sys.exit(main())

