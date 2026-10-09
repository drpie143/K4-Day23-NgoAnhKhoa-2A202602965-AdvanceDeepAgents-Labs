"""tools.py - STUDENT IMPLEMENTS.  Source tools for the research agents.   Guide: GUIDE.md, part 1.

Rules for every tool:
  * runs on the HOST (not in the sandbox): API keys must never enter the sandbox;
  * returns a STRING (JSON text of compact records) and NEVER raises:
        "NO RESULTS"  when the source answers with nothing,
        "ERROR: ..."  when the source keeps failing after the retries (the agent then tries another source);
  * the docstring is the tool description the LLM reads: keep it precise (what it does, what it returns, when to use it).
Try your tools without any agent:   python tools.py
"""
import json  # noqa: F401
import os  # noqa: F401
import time  # noqa: F401
import xml.etree.ElementTree  # noqa: F401  (arXiv answers with Atom XML)

import httpx  # noqa: F401
from langchain_core.tools import tool

# ---- constants (given) ----
ARXIV_URL = "https://export.arxiv.org/api/query"  # https only: http answers 301
HF_DAILY_URL = "https://huggingface.co/api/daily_papers"
HF_SEARCH_URL = "https://huggingface.co/api/papers/search"
EXA_URL = "https://mcp.exa.ai/mcp"


class RetryableError(Exception):
    """Given. Raise it inside a call to ask with_retry to wait and try again (retry_after in seconds, optional)."""

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


import random
import re

_LAST_ARXIV_CALL = 0.0


def _throttle_arxiv():
    global _LAST_ARXIV_CALL
    now = time.time()
    elapsed = now - _LAST_ARXIV_CALL
    if elapsed < 3.0:
        time.sleep(3.0 - elapsed)
    _LAST_ARXIV_CALL = time.time()


def _redact_key(text: str) -> str:
    key = os.getenv("EXA_API_KEY", "").strip()
    if key and key in text:
        text = text.replace(key, "[REDACTED]")
    return text


# ---- TODO 1: retry helper ----
def with_retry(fn, *, attempts=5, base=1.0, cap=30.0):
    """Call fn(); when it raises RetryableError, wait and call it again.

    PSEUDO-CODE:
      for attempt in 0 .. attempts-1:
          try: return fn()
          except RetryableError as e:
              if this was the last attempt: raise
              delay = e.retry_after if the server told us, else exponential backoff base * 2**attempt
              cap the delay at `cap` seconds; add random jitter to the exponential case
              sleep(delay)
    Use it to wrap EVERY network call below. Also treat these as retryable: HTTP 429/500/502/503/504,
    httpx.TransportError (timeouts, connection resets). Read the Retry-After header when present.
    """
    for attempt in range(attempts):
        try:
            return fn()
        except (RetryableError, httpx.TransportError, httpx.HTTPStatusError) as e:
            if attempt == attempts - 1:
                raise
            retry_after = None
            if isinstance(e, RetryableError):
                retry_after = e.retry_after
            elif isinstance(e, httpx.HTTPStatusError):
                if e.response.status_code not in (429, 500, 502, 503, 504):
                    raise
                ra = e.response.headers.get("Retry-After")
                if ra:
                    try:
                        retry_after = float(ra)
                    except ValueError:
                        retry_after = None
            elif isinstance(e, httpx.TransportError):
                pass

            if retry_after is not None:
                delay = retry_after
            else:
                delay = base * (2 ** attempt) + random.uniform(0.0, 0.5)
            delay = min(delay, cap)
            time.sleep(delay)


# ---- TODO 2: arXiv ----
@tool
def arxiv_search(query: str, max_results: int = 10) -> str:
    """Search arXiv papers by keywords, newest first. Returns a JSON list of {id, url, published, title, summary}."""
    try:
        terms = re.findall(r"[\w\-]+", query)
        if not terms:
            return "NO RESULTS"
        search_query = " AND ".join(f"all:{t}" for t in terms)
        max_res = max(1, min(int(max_results), 30))

        def _fetch():
            _throttle_arxiv()
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    ARXIV_URL,
                    params={
                        "search_query": search_query,
                        "sortBy": "submittedDate",
                        "sortOrder": "descending",
                        "max_results": max_res,
                    },
                )
                if resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    retry_after = float(ra) if ra and ra.isdigit() else 10.0
                    raise RetryableError("arXiv 429 rate limit", retry_after=retry_after)
                resp.raise_for_status()
                return resp.text

        xml_text = with_retry(_fetch, attempts=5, base=2.0, cap=60.0)
        xmlns = "{http://www.w3.org/2005/Atom}"
        root = xml.etree.ElementTree.fromstring(xml_text)
        entries = root.findall(f"{xmlns}entry")
        records = []
        for entry in entries:
            raw_id = entry.findtext(f"{xmlns}id", "").strip()
            paper_id = raw_id.split("/abs/")[-1] if "/abs/" in raw_id else raw_id
            paper_id = re.sub(r"v\d+$", "", paper_id)
            published = entry.findtext(f"{xmlns}published", "").strip()[:10]
            title = " ".join(entry.findtext(f"{xmlns}title", "").split())
            summary = " ".join(entry.findtext(f"{xmlns}summary", "").split())[:600]
            records.append({
                "id": paper_id,
                "url": f"https://arxiv.org/abs/{paper_id}",
                "published": published,
                "title": title,
                "summary": summary,
            })
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {_redact_key(str(exc))}"


# ---- TODO 3: Hugging Face ----
@tool
def hf_daily_papers(limit: int = 30, date: str = "", keyword: str = "") -> str:
    """Hugging Face Daily Papers = what is trending in AI research. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars} sorted by upvotes. `date` is YYYY-MM-DD (empty = latest).
    `keyword` filters title/summary; there is no topic search on this endpoint (use hf_search_papers for a topic)."""
    try:
        clamped_limit = max(1, min(int(limit), 100))
        params = {"limit": clamped_limit}
        if date and str(date).strip():
            params["date"] = str(date).strip()

        def _fetch():
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(HF_DAILY_URL, params=params)
                if resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    retry_after = float(ra) if ra and ra.isdigit() else 10.0
                    raise RetryableError("HF 429 rate limit", retry_after=retry_after)
                resp.raise_for_status()
                return resp.json()

        items = with_retry(_fetch, attempts=5, base=1.0, cap=30.0)
        records = []
        kw = str(keyword).strip().lower() if keyword else ""
        for item in items:
            paper = item.get("paper") if isinstance(item.get("paper"), dict) else item
            paper_id = paper.get("id") or item.get("id")
            if not paper_id:
                continue
            title = " ".join(str(paper.get("title") or item.get("title") or "").split())
            raw_summary = paper.get("summary") or item.get("summary") or ""
            summary = " ".join(str(raw_summary).split())[:600]
            published = str(paper.get("publishedAt") or item.get("publishedAt") or "")[:10]
            upvotes = int(paper.get("upvotes") or item.get("upvotes") or 0)
            github = str(paper.get("githubRepo") or item.get("githubRepo") or "")
            stars = int(paper.get("githubStars") or item.get("githubStars") or 0)

            if kw and kw not in (title + " " + summary).lower():
                continue

            records.append({
                "id": str(paper_id),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "published": published,
                "title": title,
                "summary": summary,
                "upvotes": upvotes,
                "github": github,
                "stars": stars,
            })
        records.sort(key=lambda r: r.get("upvotes", 0), reverse=True)
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {_redact_key(str(exc))}"


@tool
def hf_search_papers(query: str, limit: int = 10) -> str:
    """Search Hugging Face papers by topic. Returns a JSON list of
    {id, url, published, title, summary, upvotes, github, stars}."""
    try:
        q = str(query).strip()
        if not q:
            return "NO RESULTS"
        clamped_limit = max(1, min(int(limit), 50))
        params = {"q": q, "limit": clamped_limit}

        def _fetch():
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(HF_SEARCH_URL, params=params)
                if resp.status_code == 429:
                    ra = resp.headers.get("Retry-After")
                    retry_after = float(ra) if ra and ra.isdigit() else 10.0
                    raise RetryableError("HF 429 rate limit", retry_after=retry_after)
                resp.raise_for_status()
                return resp.json()

        items = with_retry(_fetch, attempts=5, base=1.0, cap=30.0)
        records = []
        for item in items:
            paper = item.get("paper") if isinstance(item.get("paper"), dict) else item
            paper_id = paper.get("id") or item.get("id")
            if not paper_id:
                continue
            title = " ".join(str(paper.get("title") or item.get("title") or "").split())
            raw_summary = paper.get("ai_summary") or paper.get("summary") or item.get("summary") or ""
            summary = " ".join(str(raw_summary).split())[:600]
            published = str(paper.get("publishedAt") or item.get("publishedAt") or "")[:10]
            upvotes = int(paper.get("upvotes") or item.get("upvotes") or 0)
            github = str(paper.get("githubRepo") or item.get("githubRepo") or "")
            stars = int(paper.get("githubStars") or item.get("githubStars") or 0)

            records.append({
                "id": str(paper_id),
                "url": f"https://huggingface.co/papers/{paper_id}",
                "published": published,
                "title": title,
                "summary": summary,
                "upvotes": upvotes,
                "github": github,
                "stars": stars,
            })
        if not records:
            return "NO RESULTS"
        return json.dumps(records, ensure_ascii=False)
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {_redact_key(str(exc))}"


# ---- TODO 4: web search / fetch through the Exa MCP endpoint ----
def _call_exa_mcp(tool_name: str, arguments: dict) -> str:
    key = os.getenv("EXA_API_KEY", "").strip()
    target_url = f"{EXA_URL}?exaApiKey={key}" if key else EXA_URL
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

    def _req():
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(target_url, json=payload, headers=headers)
            if resp.status_code == 429:
                ra = resp.headers.get("Retry-After")
                retry_after = float(ra) if ra and ra.isdigit() else 10.0
                raise RetryableError("Exa HTTP 429 rate limit", retry_after=retry_after)
            resp.raise_for_status()
            raw_text = resp.text

            data_obj = None
            for line in raw_text.splitlines():
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str:
                        try:
                            data_obj = json.loads(data_str)
                            break
                        except json.JSONDecodeError:
                            pass
            if data_obj is None:
                try:
                    data_obj = resp.json()
                except Exception:
                    raise RetryableError(f"Cannot parse Exa response: {raw_text[:200]}")

            if not isinstance(data_obj, dict):
                raise RetryableError("Invalid Exa response format")

            if "error" in data_obj:
                err = data_obj["error"]
                err_msg = err.get("message", str(err)) if isinstance(err, dict) else str(err)
                if "rate limit" in str(err_msg).lower():
                    raise RetryableError(f"Exa rate limit: {err_msg}", retry_after=15.0)
                raise RuntimeError(f"Exa RPC error: {err_msg}")

            result = data_obj.get("result", {})
            meta = result.get("_meta", {})
            if meta.get("rateLimited") or meta.get("rate_limited") or "rate limit" in str(meta).lower():
                raise RetryableError("Exa rate limit flag in _meta", retry_after=15.0)

            content_list = result.get("content", [])
            texts = []
            for item in content_list:
                if isinstance(item, dict) and item.get("type") == "text":
                    t = item.get("text", "")
                    if "rate limit" in t.lower() and len(t) < 500:
                        raise RetryableError(f"Exa rate limit in text: {t}", retry_after=15.0)
                    texts.append(t)
                elif isinstance(item, str):
                    texts.append(item)
            return "\n\n".join(texts).strip()

    return with_retry(_req, attempts=5, base=2.0, cap=60.0)


@tool
def web_search(query: str, objective: str = "", num_results: int = 5) -> str:
    """Search the web (Exa). Describe the ideal page in natural language. Returns clean text of the top results with URLs."""
    try:
        q = str(query).strip()
        if not q:
            return "NO RESULTS"
        obj = str(objective).strip() or f"search research papers and surveys on {q}"
        num = max(1, min(int(num_results), 10))
        res = _call_exa_mcp("web_search_exa", {"query": q, "objective": obj, "numResults": num})
        return res if res else "NO RESULTS"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {_redact_key(str(exc))}"


@tool
def web_fetch(url: str) -> str:
    """Read the full content of one web page (e.g. an arXiv abstract page) as markdown. Long pages are truncated."""
    try:
        u = str(url).strip()
        if not u:
            return "NO RESULTS"
        res = _call_exa_mcp("web_fetch_exa", {"urls": [u]})
        if not res:
            return "NO RESULTS"
        return res[:12000]
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {_redact_key(str(exc))}"


# ---- TODO 5: registry (the researcher subagent gets exactly these) ----
SOURCE_TOOLS = [arxiv_search, hf_daily_papers, hf_search_papers, web_search, web_fetch]


if __name__ == "__main__":
    for name, fn, args in [
        ("arxiv_search", arxiv_search, {"query": "world model", "max_results": 3}),
        ("hf_daily_papers", hf_daily_papers, {"limit": 20}),
        ("hf_search_papers", hf_search_papers, {"query": "world model", "limit": 3}),
        ("web_search", web_search, {"query": "survey paper on world models", "num_results": 2}),
        ("web_fetch", web_fetch, {"url": "https://arxiv.org/abs/1803.10122"}),
    ]:
        try:
            print(f"== {name}\n{fn.invoke(args)[:400]}\n")
        except NotImplementedError as exc:
            print(f"== {name}: not implemented yet ({exc})\n")
