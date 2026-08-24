"""
Wire-probe battery — DeepSeek API, raw SSE capture.
Run: py research/in-flight/wire-capture-deepseek-2026-08-02/probes.py
"""
from __future__ import annotations
import json, os, sys, time, pathlib, pprint, itertools

# --- setup: key and client ------------------------------------------------
ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from deepseek_chat import load_key, BASE_URL, PRO

API_KEY = load_key()
if not API_KEY:
    print("FATAL: no DEEPSEEK_API_KEY", file=sys.stderr)
    sys.exit(1)

import httpx
from openai import OpenAI

SDK = OpenAI(api_key=API_KEY, base_url=BASE_URL,
             timeout=httpx.Timeout(120, connect=15), max_retries=1)
HTTPX = httpx.Client(timeout=httpx.Timeout(120, connect=15))

OUT = pathlib.Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

def save(name, text):
    p = OUT / name
    p.write_text(text, encoding="utf-8")
    print(f"  -> saved {p}")

# ========================================================================
# P1: logprobs under stream=True
# ========================================================================
print("=" * 72)
print("P1: logprobs under stream=True — does it work?")
print("=" * 72)

try:
    stream = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": "Say 'hello' and nothing else."}],
        max_tokens=8,
        stream=True,
        logprobs=True,
        top_logprobs=3,
    )
    chunks = []
    for i, c in enumerate(stream):
        d = {"index": i}
        if c.choices:
            ch = c.choices[0]
            d["delta"] = ch.delta.model_dump() if hasattr(ch.delta, "model_dump") else str(ch.delta)
            d["logprobs"] = str(ch.logprobs) if ch.logprobs else None
            d["finish_reason"] = ch.finish_reason
        if hasattr(c, "usage") and c.usage:
            d["usage"] = c.usage.model_dump() if hasattr(c.usage, "model_dump") else str(c.usage)
        chunks.append(d)
    result = {"status": "success", "n_chunks": len(chunks), "chunks": chunks}
    print(f"  SUCCESS: {len(chunks)} chunks received")
except Exception as e:
    result = {"status": "error", "error": str(e), "type": type(e).__name__}
    print(f"  ERROR: {type(e).__name__}: {e}")

save("p1-logprobs-stream.json", json.dumps(result, indent=2, default=str))

# ========================================================================
# P2: RAW WIRE CAPTURE — httpx direct, no SDK filter
# ========================================================================
print("=" * 72)
print("P2: RAW WIRE CAPTURE — httpx direct SSE bytes")
print("=" * 72)

PAYLOAD = {
    "model": PRO,
    "messages": [{"role": "user", "content": "Think briefly: what is 7+3? Then answer concisely."}],
    "max_tokens": 32,
    "stream": True,
    "stream_options": {"include_usage": True},
    "thinking": {"type": "enabled"},
    "reasoning_effort": "high",
}

raw_lines = []
raw_bytes_chunks = []
try:
    with HTTPX.stream(
        "POST",
        f"{BASE_URL}/chat/completions",
        json=PAYLOAD,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
        },
    ) as resp:
        # capture ALL response headers first
        resp_headers = dict(resp.headers)
        print(f"  HTTP {resp.status_code}")
        for k, v in resp_headers.items():
            print(f"    {k}: {v}")
        raw_lines.append(f"# HTTP {resp.status_code}")
        for k, v in resp_headers.items():
            raw_lines.append(f"# HEADER {k}: {v}")

        # now read raw bytes — capture each chunk with timing
        chunk_idx = 0
        for data in resp.iter_bytes():
            ts = time.monotonic()
            raw_bytes_chunks.append({"idx": chunk_idx, "ts": ts, "len": len(data), "hex_first_32": data[:32].hex()})
            text = data.decode("utf-8", errors="replace")
            raw_lines.append(f"# BYTE-CHUNK {chunk_idx} ts={ts:.6f} len={len(data)}")
            for line in text.split("\n"):
                raw_lines.append(f"D|{line}")
            chunk_idx += 1

    save("p2-raw-sse.txt", "\n".join(raw_lines))
    save("p2-byte-chunks.json", json.dumps(raw_bytes_chunks, indent=2))
    print(f"  {chunk_idx} HTTP byte chunks captured")

except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    save("p2-raw-sse-error.txt", str(e))

# ========================================================================
# P3: TTFT DECOMPOSITION — cache hit vs miss
# ========================================================================
print("=" * 72)
print("P3: TTFT DECOMPOSITION — same prompt twice, then perturbed")
print("=" * 72)

PROMPT_CACHE = "The capital of France is Paris. The capital of Germany is Berlin. The capital of Italy is"
PERTURBED   = "The capital of France is Paris. The capital of Germany is Berlin. The capital of Spain is"

def measure_ttft(prompt, label):
    t0 = time.monotonic()
    stream = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8,
        stream=True,
        stream_options={"include_usage": True},
        temperature=0.0,
    )
    first_ts = None
    usage = None
    content = []
    reasoning = []
    for c in stream:
        if first_ts is None:
            # Any real token — content OR reasoning — counts as first token
            if c.choices:
                d = c.choices[0].delta
                has_content = d.content and d.content.strip()
                has_reasoning = getattr(d, "reasoning_content", None) or (getattr(d, "model_extra", None) or {}).get("reasoning_content")
                if has_content or (has_reasoning and has_reasoning.strip()):
                    first_ts = time.monotonic()
        if c.choices and c.choices[0].delta.content:
            content.append(c.choices[0].delta.content)
        if c.choices:
            r = getattr(c.choices[0].delta, "reasoning_content", None)
            if r:
                reasoning.append(r)
        if hasattr(c, "usage") and c.usage:
            usage = c.usage.model_dump() if hasattr(c.usage, "model_dump") else dict(c.usage)
    t1 = time.monotonic()
    ttft = round(first_ts - t0, 4) if first_ts else None
    return {"label": label, "ttft_s": ttft, "total_s": round(t1 - t0, 4),
            "usage": usage, "content": "".join(content), "reasoning": "".join(reasoning)[:80]}

p3a = measure_ttft(PROMPT_CACHE, "run-1 (cold or warm)")
time.sleep(0.5)
p3b = measure_ttft(PROMPT_CACHE, "run-2 (should be cache hit)")
time.sleep(0.5)
p3c = measure_ttft(PERTURBED, "run-3 (perturbed prefix, should miss)")

p3_results = [p3a, p3b, p3c]
for r in p3_results:
    print(f"  {r['label']}: TTFT={r['ttft_s']:.3f}s, total={r['total_s']:.3f}s, usage={r['usage']}")
save("p3-ttft-decomposition.json", json.dumps(p3_results, indent=2))

# ========================================================================
# P4: FORCED TRUNCATION — max_tokens=8, prompt wants more
# ========================================================================
print("=" * 72)
print("P4: FORCED TRUNCATION — max_tokens=8 on a prompt that wants more")
print("=" * 72)

chunks_p4 = []
try:
    stream = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": "List the numbers from 1 to 20, one per line."}],
        max_tokens=8,
        stream=True,
        stream_options={"include_usage": True},
    )
    for i, c in enumerate(stream):
        d = {"index": i}
        if c.choices:
            d["delta_content"] = c.choices[0].delta.content
            d["finish_reason"] = c.choices[0].finish_reason
        if hasattr(c, "usage") and c.usage:
            d["usage"] = c.usage.model_dump() if hasattr(c.usage, "model_dump") else str(c.usage)
        chunks_p4.append(d)
    last = chunks_p4[-1] if chunks_p4 else {}
    print(f"  {len(chunks_p4)} chunks, last finish_reason: {last.get('finish_reason')}")
    print(f"  last few: {json.dumps(chunks_p4[-4:], indent=2)}")
    save("p4-forced-truncation.json", json.dumps(chunks_p4, indent=2))
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    save("p4-forced-truncation-error.txt", str(e))

# ========================================================================
# P5: RATE-LIMIT HEADERS — dump ALL response headers
# ========================================================================
print("=" * 72)
print("P5: RATE-LIMIT HEADERS — dump all response headers from one call")
print("=" * 72)

header_info = {}
try:
    # Use a non-streaming call so headers are on the response object itself
    resp = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": "Say hi."}],
        max_tokens=4,
        stream=False,
    )
    # The SDK doesn't expose raw HTTP headers directly. Try _response or response.
    raw_resp = getattr(resp, "_response", None) or getattr(resp, "response", None)
    if raw_resp:
        header_info["headers"] = dict(raw_resp.headers)
        header_info["http_version"] = str(raw_resp.http_version)
    else:
        header_info["note"] = "no _response/response attribute on the SDK result"
        header_info["dir_resp"] = [a for a in dir(resp) if not a.startswith("__")]
    # Also try the streaming version for headers
    stream = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": "Say hi."}],
        max_tokens=4,
        stream=True,
        stream_options={"include_usage": True},
    )
    raw_stream_resp = None
    for c in stream:
        raw_stream_resp = getattr(c, "_response", None) or getattr(c, "response", None)
        if raw_stream_resp:
            break
    if raw_stream_resp:
        header_info["stream_headers"] = dict(raw_stream_resp.headers)
    else:
        header_info["stream_headers_note"] = "no _response on stream chunks either"

    print(f"  non-stream headers: {json.dumps(header_info.get('headers', {}), indent=2)}")
    print(f"  stream headers: {json.dumps(header_info.get('stream_headers', {}), indent=2)}")
    save("p5-rate-limit-headers.json", json.dumps(header_info, indent=2, default=str))

except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    save("p5-rate-limit-headers-error.txt", str(e))

# ========================================================================
# P6: EXTRA — anything the wire shows us
# ========================================================================
print("=" * 72)
print("P6: EXTRA — inspect chunk.model_extra, chunk fields, anything surprising")
print("=" * 72)

# Do a thinking-enabled call and dump the FULL model_dump of every chunk
extra_chunks = []
try:
    stream = SDK.chat.completions.create(
        model=PRO,
        messages=[{"role": "user", "content": "Think briefly: what color is the sky? Answer in one word."}],
        max_tokens=16,
        stream=True,
        stream_options={"include_usage": True},
        extra_body={"thinking": {"type": "enabled"}, "reasoning_effort": "high"},
    )
    for i, c in enumerate(stream):
        d = {}
        # Full model_dump
        try:
            d["model_dump"] = c.model_dump()
        except Exception:
            d["model_dump"] = str(c)
        # model_extra specifically
        try:
            d["model_extra"] = c.model_extra if hasattr(c, "model_extra") else "NO ATTR"
        except Exception as e:
            d["model_extra"] = f"ERROR: {e}"
        # all attributes
        d["public_attrs"] = [a for a in dir(c) if not a.startswith("_")]
        extra_chunks.append(d)
        if i >= 15:
            break
    save("p6-extra-chunk-internals.json", json.dumps(extra_chunks, indent=2, default=str))
    print(f"  {len(extra_chunks)} chunks inspected")
except Exception as e:
    print(f"  ERROR: {type(e).__name__}: {e}")
    save("p6-extra-chunk-internals-error.txt", str(e))

print("=" * 72)
print("BATTERY COMPLETE")
print("=" * 72)
