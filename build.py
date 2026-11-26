import json
import subprocess
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import urlopen

import yaml

URL = "https://github.com/v2fly/domain-list-community/releases/latest/download/dlc.dat_plain.yml"
OUT = Path("ruleset")
FIELDS = {
    "full": "domain",
    "domain": "domain_suffix",
    "keyword": "domain_keyword",
    "regexp": "domain_regex",
}


def parse(entry):
    kind, value = entry.split(":", 1)
    tags = [""]
    if ":@" in value:
        value, attrs = value.rsplit(":@", 1)
        tags += ["@" + attr for attr in attrs.split(",@")]
    return FIELDS[kind], value, tags


def group_by_tag(entries):
    groups = defaultdict(lambda: defaultdict(list))
    for entry in entries:
        field, value, tags = parse(entry)
        for tag in tags:
            groups[tag][field].append(value)
    return groups


def build(item):
    for tag, fields in group_by_tag(item["rules"]).items():
        path = OUT / f"{item['name']}{tag}.json"
        path.write_text(json.dumps({"version": 2, "rules": [fields]}))
        subprocess.run(["sing-box", "rule-set", "compile", path], check=True)


def clean():
    for path in [*OUT.glob("*.json"), *OUT.glob("*.srs")]:
        path.unlink()


def main():
    clean()
    with urlopen(URL) as response:
        lists = yaml.safe_load(response)["lists"]
    with ThreadPoolExecutor() as pool:
        list(pool.map(build, lists))


if __name__ == "__main__":
    main()