import json
import subprocess
from pathlib import Path
from urllib.request import urlopen

import yaml

URL = "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat_plain.yml"
OUTPUT = Path(__file__).resolve().parent / "output"
FIELDS = {
    "full": "domain",
    "domain": "domain_suffix",
    "keyword": "domain_keyword",
    "regexp": "domain_regex",
}


def main():
    with urlopen(URL, timeout=60) as response:
        lists = yaml.safe_load(response)["lists"]

    OUTPUT.mkdir(exist_ok=True)
    for index, item in enumerate(lists, start=1):
        name = item["name"]
        print(f"[{index}/{len(lists)}] Converting {name}", flush=True)
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

        for tag, fields in groups.items():
            source = OUTPUT / f"{name}{tag}.json"
            ruleset = {"version": 2, "rules": [fields] if fields else []}
            source.write_text(json.dumps(ruleset, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            subprocess.run(["sing-box", "rule-set", "compile", source], check=True)


if __name__ == "__main__":
    main()
