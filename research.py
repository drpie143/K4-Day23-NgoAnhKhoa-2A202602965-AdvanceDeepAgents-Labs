"""research.py - STUDENT IMPLEMENTS.  The main script.   Guide: GUIDE.md, part 3.

Usage:  python research.py "survey about world model"
Result: reports/<slug>.md   reports/<slug>.sources.json   reports/<slug>.meta.json
"""
import json  # noqa: F401
import os  # noqa: F401
import re  # noqa: F401
import sys
import time  # noqa: F401
from collections import Counter  # noqa: F401
from pathlib import Path

from agents import FINALIZER_PATH, REPORT_PATH, SOURCES_PATH, VALIDATOR_PATH, WORKDIR, build_lead_agent  # noqa: F401
from model import make_model  # noqa: F401
from sandbox import download, open_sandbox, upload  # noqa: F401

ROOT = Path(__file__).parent
REPORTS = ROOT / "reports"
VALIDATOR_SOURCE = ROOT / "check_citations.py"
FINALIZER_SOURCE = ROOT / "finalize_citations.py"   # provided: uploaded next to your validator


def slugify(topic):
    """Turn a topic into a safe file name: lower case, runs of non-word characters become one "-", max 60 chars,
    never empty (fall back to "topic"). The topic is user input: "../../x" must not escape reports/."""
    s = re.sub(r"[^\w]+", "-", str(topic).strip().lower()).strip("-")
    s = s[:60].strip("-")
    return s if s else "topic"


def build_prompt(topic):
    """The user message sent to the lead agent."""
    return f"Write a comprehensive survey report on the following topic: {topic}"


def summarize(messages, elapsed, model_name):
    """Return {"model", "elapsed_s", "subagent_calls", "tool_calls": {name: count}, "tokens": {"input", "output"}}.

    PSEUDO-CODE: walk the lead's messages; for every message with tool_calls count call["name"] (subagent_calls = the
    count of "task"); add the input/output token counts from each message's usage_metadata when present.
    (Lead messages only: subagent tokens are not included, so this undercounts the real cost.)
    elapsed_s rounded to 0.1.
    """
    subagent_calls = 0
    tool_calls = Counter()
    input_tokens = 0
    output_tokens = 0

    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for call in msg.tool_calls:
                name = call.get("name")
                if name:
                    tool_calls[name] += 1
                    if name == "task":
                        subagent_calls += 1
        if hasattr(msg, "usage_metadata") and msg.usage_metadata:
            usage = msg.usage_metadata
            input_tokens += usage.get("input_tokens", 0)
            output_tokens += usage.get("output_tokens", 0)

    return {
        "model": model_name,
        "elapsed_s": round(elapsed, 1),
        "subagent_calls": subagent_calls,
        "tool_calls": dict(tool_calls),
        "tokens": {"input": input_tokens, "output": output_tokens},
    }


def save_outputs(backend, topic, messages, elapsed, model_name, reports_dir=REPORTS):
    """Download the report from the sandbox and write the three files into reports_dir. Return the report path.

    PSEUDO-CODE:
      files = download(backend, [REPORT_PATH, SOURCES_PATH])
      if the report is missing/empty or sources.json is missing/invalid JSON: raise RuntimeError and WRITE NOTHING
          (a failed run must never leave an empty or half-written report behind)
      write <slug>.sources.json, <slug>.meta.json (topic + summarize(...) + n_sources + source_families: the sorted
      distinct "source" values of sources.json) and <slug>.md
    """
    files = download(backend, [REPORT_PATH, SOURCES_PATH])
    
    report_content = files.get(REPORT_PATH)
    sources_content = files.get(SOURCES_PATH)
    
    if not report_content or not report_content.strip():
        raise RuntimeError("Report is missing or empty")
    
    if not sources_content:
        raise RuntimeError("sources.json is missing")
    
    try:
        sources = json.loads(sources_content.decode("utf-8") if isinstance(sources_content, bytes) else sources_content)
    except Exception as e:
        raise RuntimeError(f"sources.json is invalid JSON: {e}")
        
    slug = slugify(topic)
    reports_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = reports_dir / f"{slug}.md"
    sources_path_out = reports_dir / f"{slug}.sources.json"
    meta_path = reports_dir / f"{slug}.meta.json"
    
    n_sources = len(sources)
    source_families = sorted(list(set(s.get("source") for s in sources if isinstance(s, dict) and s.get("source"))))
    
    meta_data = summarize(messages, elapsed, model_name)
    meta_data["topic"] = topic
    meta_data["n_sources"] = n_sources
    meta_data["source_families"] = source_families
    
    report_path.write_text(report_content.decode("utf-8") if isinstance(report_content, bytes) else report_content, encoding="utf-8")
    sources_path_out.write_text(sources_content.decode("utf-8") if isinstance(sources_content, bytes) else sources_content, encoding="utf-8")
    meta_path.write_text(json.dumps(meta_data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    return report_path


def main(topic):
    """Return the process exit code (0 ok, 1 failed run, 2 no topic).

    PSEUDO-CODE:
      empty topic -> print usage to stderr, return 2
      model = make_model(); start = time.monotonic()
      with open_sandbox() as backend:                # the sandbox is always cleaned up, even on errors
          backend.execute("mkdir -p <WORKDIR>/research/notes <WORKDIR>/report")
          upload(backend, {VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(), FINALIZER_PATH: FINALIZER_SOURCE.read_bytes()})
          agent = build_lead_agent(backend, model)
          result = agent.invoke({"messages": [{"role": "user", "content": build_prompt(topic)}]},
                                config={"recursion_limit": 1000})
          save_outputs(...); on RuntimeError print "FAILED: ..." to stderr and return 1
      print where the report was saved; return 0
    """
    if not topic or not str(topic).strip():
        print("Usage: python research.py <topic>", file=sys.stderr)
        return 2
        
    model = make_model()
    model_name = getattr(model, "model_name", getattr(model, "model", "unknown"))
    start = time.monotonic()
    
    try:
        with open_sandbox() as backend:
            backend.execute(f"mkdir -p {WORKDIR}/research/notes {WORKDIR}/report")
            upload(backend, {
                VALIDATOR_PATH: VALIDATOR_SOURCE.read_bytes(),
                FINALIZER_PATH: FINALIZER_SOURCE.read_bytes()
            })
            
            agent = build_lead_agent(backend, model)
            result = agent.invoke(
                {"messages": [{"role": "user", "content": build_prompt(topic)}]},
                config={"recursion_limit": 1000}
            )
            
            elapsed = time.monotonic() - start
            messages = result.get("messages", [])
            
            report_path = save_outputs(backend, topic, messages, elapsed, model_name)
            print(f"Report saved to: {report_path}")
            return 0
    except RuntimeError as e:
        print(f"FAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"FAILED with unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(" ".join(sys.argv[1:])))
