import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

import yaml

URL = "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat_plain.yml"
ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "ruleset"
FIELDS = {
    "full": "domain",
    "domain": "domain_suffix",
    "keyword": "domain_keyword",
    "regexp": "domain_regex",
}


def write_json(item):
    name = item["name"]
    groups = {"": {}}
    for entry in item["rules"]:
        kind, value = entry.split(":", 1)
        parts = value.rsplit(":@", 1)
        value = parts[0]
        tags = [""]
        if len(parts) == 2:
            tags.extend("@" + attr for attr in parts[1].split(",@"))
        for tag in tags:
            fields = groups.setdefault(tag, {})
            fields.setdefault(FIELDS[kind], []).append(value)

    sources = []
    for tag, fields in groups.items():
        source = OUTPUT / f"{name}{tag}.json"
        ruleset = {"version": 2, "rules": [fields] if fields else []}
        source.write_text(json.dumps(ruleset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sources.append(source)
    return sources


def main():
    if not OUTPUT.exists():
        exists = subprocess.run(["git", "show-ref", "--verify", "--quiet", "refs/heads/ruleset"], cwd=ROOT)
        args = [OUTPUT, "ruleset"] if exists.returncode == 0 else ["--orphan", OUTPUT]
        subprocess.run(["git", "worktree", "add", *args], cwd=ROOT, check=True)
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=OUTPUT, text=True).strip()
    if branch != "ruleset":
        raise RuntimeError(f"{OUTPUT} must be a ruleset branch worktree")

    with urlopen(URL, timeout=60) as response:
        lists = yaml.safe_load(response)["lists"]

    sources = []
    for index, item in enumerate(lists, start=1):
        sources.extend(write_json(item))
        print(f"[{index}/{len(lists)}] Wrote JSON for {item['name']}", flush=True)

    for index, source in enumerate(sources, start=1):
        subprocess.run(["sing-box", "rule-set", "compile", source], check=True)
        print(f"[{index}/{len(sources)}] Compiled SRS for {source.stem}", flush=True)

    generated = set(sources) | {source.with_suffix(".srs") for source in sources}
    for pattern in ("*.json", "*.srs"):
        for old in OUTPUT.glob(pattern):
            if old not in generated:
                old.unlink()
    subprocess.run(["git", "add", "-A", "--", "*.json", "*.srs"], cwd=OUTPUT, check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=OUTPUT).returncode == 1:
        subprocess.run(["git", "commit", "-m", "Update rule sets"], cwd=OUTPUT, check=True)


if __name__ == "__main__":
    main()
