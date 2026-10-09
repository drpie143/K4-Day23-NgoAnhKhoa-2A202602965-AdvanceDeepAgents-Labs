"""check_citations.py - STUDENT IMPLEMENTS `check`.   Runs INSIDE the sandbox (standard library only).

research.py uploads this file to the sandbox and the lead agent runs it with the `execute` tool:
    python3 /tmp/work/research/check_citations.py [report.md] [sources.json]
It must exit 0 and print "OK: ..." when the report is consistent, else print each problem and exit 1.
"""
import json
import sys

REPORT = "/tmp/work/report/report.md"
SOURCES = "/tmp/work/research/sources.json"


import re

_GROUP = re.compile(r"\[(\d+(?:\s*[,–-]\s*\d+)*)\](?!\()")
_CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_REF_HEADING = re.compile(r"(?m)^##[ \t]+References[ \t]*$")


def _group_numbers(group):
    numbers = []
    for part in re.split(r"\s*,\s*", group):
        span = re.fullmatch(r"(\d+)\s*[–-]\s*(\d+)", part)
        if span:
            a, b = int(span.group(1)), int(span.group(2))
            numbers.extend(range(a, b + 1) if 0 <= b - a <= 200 else [a, b])
        else:
            numbers.append(int(part))
    return numbers


def check(report_text, sources):
    """Return a list of problem strings (empty list = OK)."""
    problems = []
    if not sources or not isinstance(sources, list):
        return ["no sources in sources.json"]

    seen_urls = {}
    valid_source_nums = set()
    source_by_n = {}

    for entry in sources:
        if not isinstance(entry, dict):
            problems.append(f"source entry {entry!r} is not an object")
            continue
        n = entry.get("n")
        if not isinstance(n, int):
            problems.append(f"source {entry!r}: n must be an integer")
        else:
            if n in valid_source_nums:
                problems.append(f"duplicate source number n={n}")
            valid_source_nums.add(n)
            source_by_n[n] = entry

        url = entry.get("url")
        if not isinstance(url, str) or not (url.startswith("http://") or url.startswith("https://")):
            problems.append(f"source n={n!r}: url must start with http:// or https:// (got {url!r})")
        else:
            if url in seen_urls:
                problems.append(f"duplicate url {url!r} appears in sources n={seen_urls[url]} and n={n}")
            else:
                seen_urls[url] = n

    ref_matches = list(_REF_HEADING.finditer(report_text))
    if not ref_matches:
        problems.append("missing heading '## References'")
        return problems

    body = report_text[:ref_matches[-1].start()]
    refs_section = report_text[ref_matches[-1].end():]

    # Find all [n] in body only, ignoring code spans
    cited = set()
    segments = _CODE.split(body)
    for i, seg in enumerate(segments):
        if i % 2 == 1:
            continue  # inside code
        for match in _GROUP.finditer(seg):
            for num in _group_numbers(match.group(1)):
                cited.add(num)

    for c in sorted(cited):
        if c not in valid_source_nums:
            problems.append(f"[{c}] cited in body but missing from sources.json")

    for sn in sorted(valid_source_nums):
        if sn not in cited:
            problems.append(f"source [{sn}] in sources.json never cited in report body")

    # Check References section
    ref_lines = {}
    for line in refs_section.splitlines():
        line_str = line.strip()
        m = re.match(r"^\[(\d+)\]\s*(.*)$", line_str)
        if m:
            num = int(m.group(1))
            if num in ref_lines:
                problems.append(f"duplicate reference entry for [{num}] in References")
            else:
                ref_lines[num] = (line_str, m.group(2))

    for sn in sorted(valid_source_nums):
        if sn not in ref_lines:
            problems.append(f"missing reference line for source [{sn}] in References")

    for num in sorted(ref_lines.keys()):
        if num not in valid_source_nums:
            problems.append(f"reference [{num}] in References does not exist in sources.json")
        else:
            line_str = ref_lines[num][0]
            raw_urls = re.findall(r"https?://\S+", line_str)
            urls = [u.rstrip(".,;\"'") for u in raw_urls]
            if len(urls) != 1:
                problems.append(f"reference line [{num}] must contain exactly one URL (found {len(urls)})")
            else:
                expected_url = source_by_n[num].get("url")
                if urls[0] != expected_url:
                    problems.append(f"reference line [{num}] URL mismatch: found {urls[0]!r}, expected {expected_url!r}")

    return problems


def main(argv):
    report_path = argv[1] if len(argv) > 1 else REPORT
    sources_path = argv[2] if len(argv) > 2 else SOURCES
    try:
        with open(report_path, encoding="utf-8") as f:
            report = f.read()
        with open(sources_path, encoding="utf-8") as f:
            sources = json.load(f)
    except (OSError, ValueError) as exc:
        print(f"cannot read inputs: {exc}")
        return 1
    problems = check(report, sources)
    if problems:
        print("\n".join(problems))
        return 1
    print(f"OK: {len(sources)} sources, all citations resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
