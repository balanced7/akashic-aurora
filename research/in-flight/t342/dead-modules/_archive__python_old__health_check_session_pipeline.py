#!/usr/bin/env python3
"""
Session pipeline health — Redis logs, canonical stream, summary parity, compressor, inference GPU hints.

Usage:
  python E:\\AI-Setup\\health_check_session_pipeline.py
  python E:\\AI-Setup\\health_check_session_pipeline.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import redis  # noqa: E402

from config import (  # noqa: E402
    BASE_DIR,
    CANONICAL_EVENTS_JSONL,
    SESSION_EVENTS_STREAM,
    SESSION_STATE_FILE,
    get_docker_redis_config,
    get_redis_config,
)

# Compressor default matches session_compressor.py
GEMMA_URL = os.environ.get("GEMMA_URL", "http://localhost:5000")


def _sub(cmd: list[str], timeout: float = 15.0) -> tuple[int, str, str]:
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return p.returncode, p.stdout or "", p.stderr or ""
    except Exception as e:
        return -1, "", str(e)


def compressor_pids() -> list[dict]:
    ps_cmd = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
        "| Where-Object { $_.CommandLine -match 'session_compressor' } "
        "| Select-Object ProcessId, CommandLine | ConvertTo-Json -Compress"
    )
    code, out, err = _sub(
        ["powershell", "-NoProfile", "-Command", ps_cmd], timeout=20
    )
    rows: list[dict] = []
    if code != 0 or not out.strip():
        return rows
    try:
        data = json.loads(out)
        if isinstance(data, dict):
            rows.append({"pid": data.get("ProcessId"), "cmd": data.get("CommandLine", "")})
        elif isinstance(data, list):
            for item in data:
                rows.append(
                    {"pid": item.get("ProcessId"), "cmd": item.get("CommandLine", "")}
                )
    except json.JSONDecodeError:
        pass
    return rows


def docker_ps_json() -> list[dict]:
    code, out, _ = _sub(["docker", "ps", "--format", "{{json .}}"], timeout=15)
    if code != 0:
        return []
    rows = []
    for line in out.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def docker_inspect_devices(container: str) -> dict:
    code, out, err = _sub(
        [
            "docker",
            "inspect",
            container,
            "--format",
            "{{json .HostConfig.Devices}}|||{{json .HostConfig.DeviceRequests}}|||{{.HostConfig.Privileged}}",
        ],
        timeout=15,
    )
    if code != 0:
        return {"error": err or out or "inspect failed"}
    parts = out.strip().split("|||")
    dev = json.loads(parts[0]) if len(parts) > 0 and parts[0] else []
    req = json.loads(parts[1]) if len(parts) > 1 and parts[1] else None
    priv = parts[2].strip().lower() == "true" if len(parts) > 2 else None
    return {"Devices": dev, "DeviceRequests": req, "Privileged": priv}


def ollama_ps(container: str) -> dict:
    code, out, err = _sub(
        ["docker", "exec", container, "ollama", "ps"], timeout=20
    )
    text = (out + err).strip()
    return {"exit_code": code, "raw": text}


def http_json(url: str, timeout: float = 5.0) -> dict:
    try:
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "health-check/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return {"ok": True, "status": resp.status, "json": json.loads(body)}
            except json.JSONDecodeError:
                return {"ok": True, "status": resp.status, "text": body[:800]}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def local_ollama_ps(port: int = 11434) -> dict:
    """Host-published Ollama HTTP API (if exposed)."""
    data = http_json(f"http://127.0.0.1:{port}/api/ps", timeout=5)
    if not data.get("ok") or not isinstance(data.get("json"), dict):
        return data
    models = data["json"].get("models") or []
    gpu_loaded = False
    for m in models:
        sv = m.get("size_vram")
        try:
            if sv is not None and int(sv) > 0:
                gpu_loaded = True
                break
        except (TypeError, ValueError):
            continue
    data["derived_size_vram_positive"] = gpu_loaded
    return data


def summarize_log_tail(lines: int = 5) -> dict:
    log_dir = BASE_DIR / "session_logs"
    primary = log_dir / "session_all.jsonl"
    out = {"session_all.jsonl": {"exists": primary.exists(), "tail_lines": []}}
    if primary.exists():
        try:
            data = primary.read_text(encoding="utf-8", errors="replace").splitlines()
            out["session_all.jsonl"]["approx_lines"] = len(data)
            out["session_all.jsonl"]["tail_lines"] = data[-lines:]
        except Exception as e:
            out["session_all.jsonl"]["error"] = str(e)
    return out


def redis_checks() -> dict:
    rep: dict = {"wsl": {}, "docker": {}}
    for label, factory in [
        ("wsl", lambda: redis.Redis(**get_redis_config())),
        ("docker", lambda: redis.Redis(**get_docker_redis_config())),
    ]:
        try:
            r = factory()
            r.ping()
            summ_keys = list(r.scan_iter(match="session:summary:*", count=500))
            rep[label]["ping"] = True
            rep[label]["session_summary_count"] = len(summ_keys)
            rep[label]["stream_entries_approx"] = r.xlen(SESSION_EVENTS_STREAM)
            idx_docs = None
            try:
                info = r.execute_command("FT.INFO", "session_text_idx")
                di = dict(zip(info[::2], info[1::2]))
                idx_docs = di.get(b"num_docs", di.get("num_docs"))
                if isinstance(idx_docs, bytes):
                    idx_docs = idx_docs.decode()
            except Exception as e:
                idx_docs = f"err:{e}"
            rep[label]["ft_num_docs"] = idx_docs
            if label == "wsl":
                try:
                    rep[label]["learn_decisions_count"] = int(r.zcard("learn:decisions:idx") or 0)
                    rep[label]["learn_experiences_success"] = int(
                        r.zcard("learn:experiences:success") or 0
                    )
                except Exception:
                    rep[label]["learn_decisions_count"] = None
                    rep[label]["learn_experiences_success"] = None
        except Exception as e:
            rep[label]["ping"] = False
            rep[label]["error"] = str(e)
    # parity
    wc = rep.get("wsl", {}).get("session_summary_count")
    dc = rep.get("docker", {}).get("session_summary_count")
    rep["summary_parity_match"] = (
        wc is not None and dc is not None and wc == dc if wc is not None else None
    )
    rep["summary_counts"] = {"wsl": wc, "docker": dc}
    return rep


def persisted_session() -> dict:
    if not SESSION_STATE_FILE.exists():
        return {"exists": False}
    try:
        return {"exists": True, **json.loads(SESSION_STATE_FILE.read_text(encoding="utf-8"))}
    except Exception as e:
        return {"exists": True, "error": str(e)}


def inference_gpu_report() -> dict:
    """
    Best-effort: summarizer posts to GEMMA_URL (/health, /api/chat).
    Actual inference is usually Ollama in Docker — ROCm image + /dev/dri hints GPU path.
    """
    report: dict = {
        "gemma_voice_base_url": GEMMA_URL,
        "voice_health": http_json(f"{GEMMA_URL.rstrip('/')}/health"),
        "host_ollama_api_ps": local_ollama_ps(11434),
    }

    containers = docker_ps_json()
    names = [c.get("Names", "") for c in containers]
    report["docker_running_names_sample"] = names[:12]

    primary_image: dict[str, str] = {}
    for c in containers:
        raw_n = (c.get("Names") or "").strip()
        first = raw_n.split(",")[0].strip()
        if first:
            primary_image[first] = (c.get("Image") or "").strip()

    ollama_candidates = []
    for c in containers:
        name = (c.get("Names") or "").lower()
        img = (c.get("Image") or "").lower()
        if "ollama" in name or "ollama" in img:
            ollama_candidates.append((c.get("Names") or "").split(",")[0].strip())

    voice_candidates = []
    for c in containers:
        name = (c.get("Names") or "").lower()
        if "voice" in name:
            voice_candidates.append((c.get("Names") or "").split(",")[0].strip())

    report["ollama_container_candidates"] = ollama_candidates
    report["voice_container_candidates"] = voice_candidates

    gpu_hints = []
    for cand in ollama_candidates[:3]:
        if not cand:
            continue
        tag = cand.split(",")[0].strip()
        devices = docker_inspect_devices(tag)
        ps_out = ollama_ps(tag)
        raw = ps_out.get("raw") or ""
        processor_guess = None
        # Typical `ollama ps` lines include a PROCESSOR column (CPU vs GPU)
        if re.search(r"\bGPU\b", raw, re.I):
            processor_guess = "GPU"
        elif re.search(r"\bCPU\b", raw, re.I):
            processor_guess = "CPU"
        img = primary_image.get(tag, "")
        gpu_hints.append(
            {
                "container": tag,
                "image": img,
                "image_rocm": "rocm" in img.lower(),
                "devices_inspect": devices,
                "ollama_ps": ps_out,
                "processor_hint": processor_guess,
            }
        )

    report["ollama_gpu_hints"] = gpu_hints

    # ROCm-style device exposure
    for hint in gpu_hints:
        devs = hint.get("devices_inspect", {}).get("Devices") or []
        hint["has_dri_or_kfd"] = any(
            isinstance(d, dict)
            and (
                "/dev/dri" in str(d.get("PathOnHost", ""))
                or "/dev/kfd" in str(d.get("PathOnHost", ""))
            )
            for d in devs
        )

    # Verdict for summarizer (compressor → GEMMA_URL → ai-voice → Ollama)
    api_ps = report.get("host_ollama_api_ps") or {}
    vr_loaded = bool(api_ps.get("derived_size_vram_positive"))
    ps_hints = [h.get("processor_hint") for h in gpu_hints]
    ps_gpu = any(h == "GPU" for h in ps_hints)
    ps_cpu = any(h == "CPU" for h in ps_hints)
    rocm_img = any(h.get("image_rocm") for h in gpu_hints)
    dri = any(h.get("has_dri_or_kfd") for h in gpu_hints)

    if ps_gpu or vr_loaded:
        verdict = "GPU (Ollama reports GPU offload / VRAM resident weights)"
    elif ps_cpu or (
        isinstance(api_ps.get("json"), dict)
        and (api_ps.get("json", {}).get("models"))
        and not vr_loaded
    ):
        verdict = "CPU (Ollama `ollama ps` shows CPU and/or size_vram=0 - model running on CPU RAM)"
    else:
        verdict = "unknown (Ollama not reachable or no loaded model)"

    report["summarizer_acceleration_verdict"] = verdict
    report["summarizer_evidence"] = {
        "api_ps_size_vram_positive": vr_loaded,
        "ollama_ps_processor_hints": ps_hints,
        "ollama_image_rocm": rocm_img,
        "docker_has_gpu_devices": dri,
    }

    return report


def main():
    parser = argparse.ArgumentParser(description="Session pipeline health check")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args()

    # Fix accidental import mistake - remove GEMMA_URL_ENVunused from config import if it fails
    payload = {
        "timestamp": datetime.now().isoformat(),
        "persisted_session_state": persisted_session(),
        "canonical_jsonl": {
            "path": str(CANONICAL_EVENTS_JSONL),
            "exists": CANONICAL_EVENTS_JSONL.exists(),
            "bytes": CANONICAL_EVENTS_JSONL.stat().st_size if CANONICAL_EVENTS_JSONL.exists() else 0,
        },
        "redis": redis_checks(),
        "compressor_processes": compressor_pids(),
        "session_logs": summarize_log_tail(),
        "inference": inference_gpu_report(),
    }

    # Recent stream IDs (WSL)
    try:
        r = redis.Redis(**get_redis_config())
        payload["stream_tail_ids"] = [
            mid for mid, _ in r.xrevrange(SESSION_EVENTS_STREAM, "+", "-", count=5)
        ]
    except Exception as e:
        payload["stream_tail_error"] = str(e)

    if args.json:
        print(json.dumps(payload, indent=2, default=str))
        return

    print("=== Session pipeline health ===")
    print(f"Time: {payload['timestamp']}")
    print(f"Session state file: {payload['persisted_session_state']}")
    print(f"Canonical JSONL: {payload['canonical_jsonl']}")
    rw = payload["redis"]["wsl"]
    rd = payload["redis"]["docker"]
    print(
        f"Redis WSL ping={rw.get('ping')} summaries={rw.get('session_summary_count')} "
        f"stream_len={rw.get('stream_entries_approx')} FT_docs={rw.get('ft_num_docs')} "
        f"learn_ADRs={rw.get('learn_decisions_count')} learn_exp_ok={rw.get('learn_experiences_success')}"
    )
    print(f"Redis Docker ping={rd.get('ping')} summaries={rd.get('session_summary_count')} FT_docs={rd.get('ft_num_docs')}")
    print(f"Summary parity (counts equal): {payload['redis'].get('summary_counts')}")
    cp = payload["compressor_processes"]
    print(f"Compressor daemon: {len(cp)} process(es)", cp or "(none — run session_compressor.py --daemon)")
    print(f"Stream tail IDs: {payload.get('stream_tail_ids', payload.get('stream_tail_error'))}")
    inf = payload["inference"]
    print(f"Voice/Gemma URL: {inf['gemma_voice_base_url']}")
    print(f"  /health: {inf['voice_health']}")
    print(f"Host Ollama GET /api/ps: {inf['host_ollama_api_ps']}")
    print(f"Summarizer acceleration: {inf.get('summarizer_acceleration_verdict')}")
    print(f"  Evidence: {inf.get('summarizer_evidence')}")
    for h in inf.get("ollama_gpu_hints", []):
        print(f"  Ollama container `{h.get('container')}` (image `{h.get('image')}`):")
        print(f"    has_dri_or_kfd: {h.get('has_dri_or_kfd')} | image_rocm: {h.get('image_rocm')}")
        print(f"    ollama_ps exit={h.get('ollama_ps', {}).get('exit_code')}")
        raw = h.get("ollama_ps", {}).get("raw", "")[:400]
        print(f"    ollama_ps snippet:\n{raw}")
    print("Done.")


if __name__ == "__main__":
    main()
