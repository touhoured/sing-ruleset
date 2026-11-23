import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
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
        value, *suffix = value.rsplit(":@", 1)
        tags = [""]
        if suffix:
            tags.extend("@" + attr for attr in suffix[0].split(",@"))
        for tag in tags:
            fields = groups.setdefault(tag, {})
            fields.setdefault(FIELDS[kind], []).append(value)

    sources = []
    for tag, fields in groups.items():
        source = OUTPUT / f"{name}{tag}.json"
        ruleset = {"version": 2, "rules": [fields] if fields else []}
        source.write_text(json.dumps(ruleset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        sources.append(source)
    return name, sources


def git(*args, cwd=OUTPUT):
    return subprocess.check_output(["git", *args], cwd=cwd, text=True).strip()


def compile_srs(source):
    subprocess.run(["sing-box", "rule-set", "compile", source], check=True)
    return source.stem


def main():
    if not OUTPUT.exists():
        flags = [] if git("branch", "--list", "ruleset", cwd=ROOT) else ["--orphan"]
        git("worktree", "add", *flags, OUTPUT, cwd=ROOT)
    if git("branch", "--show-current") != "ruleset":
        raise RuntimeError(f"{OUTPUT} must be a ruleset branch worktree")

    with urlopen(URL, timeout=60) as response:
        lists = yaml.safe_load(response)["lists"]

    workers = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    with ThreadPoolExecutor(max_workers=workers) as pool:
        sources = []
        for index, (name, paths) in enumerate(pool.map(write_json, lists), start=1):
            sources.extend(paths)
            print(f"[{index}/{len(lists)}] Wrote JSON for {name}", flush=True)

        for index, name in enumerate(pool.map(compile_srs, sources), start=1):
            print(f"[{index}/{len(sources)}] Compiled SRS for {name}", flush=True)

    names = {source.stem for source in sources}
    for pattern in ("*.json", "*.srs"):
        for old in OUTPUT.glob(pattern):
            if old.stem not in names:
                old.unlink()
    git("add", "-A", "--", "*.json", "*.srs")
    if git("diff", "--cached", "--name-only"):
        git("commit", "-qm", "Update rule sets")


if __name__ == "__main__":
    main()
