# V2Fly to sing-box

With Python 3, sing-box 1.10+, and Git supporting `worktree add --orphan` on your PATH, run:

```sh
python3 -m pip install -r requirements.txt
python3 convert.py
```

The script downloads the latest V2Fly domain lists and commits `<name>.json` and `<name>.srs` at the root of the local `ruleset` branch. The `ruleset/` directory is a separate Git worktree for generated files.

Each attribute also gets its own pair. For example, `ruleset/google@cn.json` and `ruleset/google@cn.srs` contain the Google entries tagged `@cn`. A rule with multiple tags appears in each matching subset and in the complete list.
