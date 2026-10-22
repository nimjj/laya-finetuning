"""End-to-end, load and memory test of the v3 service with the REAL model.

    python laya-finetuning/eval/v3_service_test.py --out laya-finetuning/runs/v3/service_test.json

It starts `python main.py` with LAYA_FLOW=v3 on a spare port, then:
  A. sends 3 calls to /api/evaluate and checks the scores equal the ones the offline comparison got (compare_agt.jsonl);
  B. sends bad input (empty transcript, oversize body) and checks the error codes;
  C. LOAD: submits more calls than the waiting line holds, at the same moment, through /api/jobs; checks the extras are refused with
     503 + Retry-After, every accepted call is graded, and the server is still healthy afterwards;
  D. 20 simultaneous /api/evaluate calls: those that outlast the wait limit must come back as 503 with a job id that later finishes;
  E. WORST CASE: a transcript as large as the limits allow;
and samples the server's memory every second (working set and peak commit; Windows only). All calls are AI-written test calls.
"""
import argparse
import ctypes
import glob
import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from ctypes import wintypes

import _roots  # noqa: E402  (finds the QA app root; see _roots.py)
ROOT = _roots.QA_ROOT


class _PMC(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD), ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t), ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


class _PE32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD), ("th32ParentProcessID", wintypes.DWORD),
                ("pcPriClassBase", wintypes.LONG), ("dwFlags", wintypes.DWORD), ("szExeFile", ctypes.c_char * 260)]


def family(pid):
    """The process and all its descendants (the venv launcher starts the real Python as a child)."""
    k32 = ctypes.windll.kernel32
    k32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    snap = k32.CreateToolhelp32Snapshot(0x2, 0)
    kids, entry = {}, _PE32()
    entry.dwSize = ctypes.sizeof(entry)
    ok = k32.Process32First(snap, ctypes.byref(entry))
    while ok:
        kids.setdefault(entry.th32ParentProcessID, []).append(entry.th32ProcessID)
        ok = k32.Process32Next(snap, ctypes.byref(entry))
    k32.CloseHandle(snap)
    out, todo = [], [pid]
    while todo:
        p = todo.pop()
        out.append(p)
        todo.extend(kids.get(p, []))
    return out


def memory_gb(proc):
    """(working set now, sum of peak working sets, sum of peak commit) over the process family, in GB."""
    g = 1024 ** 3
    ws = pws = commit = 0
    for pid in family(proc.pid):
        pmc = _PMC()
        pmc.cb = ctypes.sizeof(pmc)
        h = ctypes.windll.kernel32.OpenProcess(0x0400 | 0x0010, False, pid)      # query information | read
        if not h:
            continue
        try:
            if ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
                ws, pws, commit = ws + pmc.WorkingSetSize, pws + pmc.PeakWorkingSetSize, commit + pmc.PeakPagefileUsage
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    return (ws / g, pws / g, commit / g)


def http(method, url, body=None, headers=None, timeout=300):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"content-type": "application/json", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"{}"), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw), dict(e.headers)
        except Exception:
            return e.code, {"raw": raw[:200].decode("utf-8", "replace")}, dict(e.headers)


def load_calls(folder, n):
    out = []
    for fp in sorted(glob.glob(os.path.join(ROOT, folder, "*.json")))[:n]:
        d = json.load(open(fp, encoding="utf-8"))
        if isinstance(d, dict) and d.get("transcript"):
            out.append((os.path.basename(fp)[:-5], d))
    return out


def body_of(d, call_id):
    return {"transcript": d["transcript"], "customer_name": d.get("customer_name") or d.get("customerName"), "call_id": call_id, "tenant_id": "load-test"}


def worst_case_call(calls):
    """As large as the limits allow: 1,500 turns of ~160 characters, times spread over the 4-hour limit."""
    turns, i = [], 0
    pool = [t for _, d in calls for t in d["transcript"] if len(t.get("text", "")) > 60]
    while len(turns) < 1500:
        t = dict(pool[i % len(pool)])
        t["text"] = (t["text"] + " " + t["text"])[:160]
        t["start_time_sec"] = len(turns) * 9
        t.pop("end_time", None)
        t.pop("end_time_sec", None)
        turns.append(t)
        i += 1
    return turns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--port", type=int, default=8016)
    ap.add_argument("--accepted", type=int, default=50, help="queue size on the server (QUEUE_MAX)")
    ap.add_argument("--extra", type=int, default=6, help="calls sent beyond the line's capacity")
    ap.add_argument("--simultaneous", type=int, default=20)
    ap.add_argument("--skip-worst", action="store_true")
    ap.add_argument("--log", default=None)
    args = ap.parse_args()
    base = f"http://127.0.0.1:{args.port}"
    calls = load_calls("laya-finetuning/inputs/AG-T", 100)
    offline = {}
    cmp_path = os.path.join(ROOT, "laya-finetuning", "runs", "v3", "compare_agt.jsonl")
    if os.path.exists(cmp_path):
        for line in open(cmp_path, encoding="utf-8"):
            r = json.loads(line)
            offline[r["call"]] = r["v3_score"]

    env = dict(os.environ, LAYA_FLOW="v3", SERVER_HOST="127.0.0.1", SERVER_PORT=str(args.port), QUEUE_MAX=str(args.accepted))
    logf = open(args.log or os.path.join(ROOT, "logs", "v3_service_test_server.log"), "w", encoding="utf-8")
    t_start = time.time()
    proc = subprocess.Popen([sys.executable, "main.py"], cwd=ROOT, env=env, stdout=logf, stderr=subprocess.STDOUT)
    mem = {"peak_ws": 0.0, "peak_commit": 0.0, "samples": []}
    stop = threading.Event()

    def sampler():
        while not stop.is_set():
            ws, pws, commit = memory_gb(proc)
            mem["peak_ws"], mem["peak_commit"] = max(mem["peak_ws"], pws), max(mem["peak_commit"], commit)
            mem["samples"].append((round(time.time() - t_start), round(ws, 2)))
            stop.wait(1.0)
    threading.Thread(target=sampler, daemon=True).start()
    report = {"note": "AI-written test calls; real model; this PC (Core Ultra 7 255U, 14 threads, 15 GB RAM)"}
    try:
        # ---- model load / readiness
        ready_at, status = None, None
        while time.time() - t_start < 600:
            try:
                status, body, _ = http("GET", base + "/ready", timeout=5)
                if status == 200:
                    ready_at = time.time() - t_start
                    break
            except Exception:
                pass
            time.sleep(1)
        report["ready_seconds"] = round(ready_at, 1) if ready_at else None
        report["memory_after_load_gb"] = round(memory_gb(proc)[0], 2)
        print("ready after", report["ready_seconds"], "s; memory", report["memory_after_load_gb"], "GB", flush=True)
        if not ready_at:
            report["fatal"] = f"server never became ready (last status {status})"
            return

        # ---- A. functional
        a = []
        for name, d in calls[:3]:
            t0 = time.time()
            code, body, _ = http("POST", base + "/api/evaluate", body_of(d, name))
            score = body.get("result", {}).get("final_score") if code == 200 else None
            a.append({"call": name, "http": code, "score": score, "offline_score": offline.get(name), "seconds": round(time.time() - t0, 1),
                      "match": score is not None and score == offline.get(name),
                      "meta": body.get("result", {}).get("meta") if code == 200 else body})
        report["A_functional"] = a
        print("A:", [(x["call"], x["http"], x["score"], x["offline_score"]) for x in a], flush=True)

        # ---- B. bad input
        b = {}
        b["empty_transcript"] = http("POST", base + "/api/evaluate", {"transcript": []})[0]
        b["oversize_body"] = http("POST", base + "/api/evaluate", {"transcript": [{"speaker": "Agent", "text": "x" * 3_000_000}]})[0]
        b["too_many_turns"] = http("POST", base + "/api/evaluate", {"transcript": [{"speaker": "Agent", "text": "hi", "start_time_sec": i} for i in range(1600)]})[0]
        b["unknown_job"] = http("GET", base + "/api/jobs/doesnotexist")[0]
        b["health"] = http("GET", base + "/health")[0]
        report["B_bad_input"] = b
        print("B:", b, flush=True)

        # ---- C. load: capacity + extra at the same moment
        n = args.accepted + args.extra
        t0 = time.time()
        sub = []

        def submit(i):
            name, d = calls[(i + 3) % len(calls)]
            code, body, hdr = http("POST", base + "/api/jobs", body_of(d, f"load-{i}"))
            return {"i": i, "call": name, "http": code, "job_id": body.get("job_id"), "retry_after": hdr.get("Retry-After") or hdr.get("retry-after")}
        with ThreadPoolExecutor(max_workers=n) as ex:
            sub = list(ex.map(submit, range(n)))
        accepted = [s for s in sub if s["http"] == 202]
        refused = [s for s in sub if s["http"] == 503]
        print(f"C: submitted {n}: accepted {len(accepted)}, refused {len(refused)} (503 with Retry-After: {sum(bool(s['retry_after']) for s in refused)})", flush=True)
        done = {}
        while len(done) < len(accepted) and time.time() - t0 < 3600:
            for s in accepted:
                if s["job_id"] in done:
                    continue
                code, body, _ = http("GET", base + f"/api/jobs/{s['job_id']}", timeout=30)
                if code == 200 and body["status"] in ("done", "failed"):
                    done[s["job_id"]] = body
            time.sleep(3)
        elapsed = time.time() - t0
        waits = sorted(b.get("waited_seconds", 0) for b in done.values())
        runs = [b.get("run_seconds", 0) for b in done.values()]
        report["C_load"] = {
            "submitted": n, "accepted": len(accepted), "refused_503": len(refused), "refused_with_retry_after": sum(bool(s["retry_after"]) for s in refused),
            "other_codes": sorted({s["http"] for s in sub} - {202, 503}), "finished_ok": sum(b["status"] == "done" for b in done.values()),
            "failed": sum(b["status"] == "failed" for b in done.values()), "total_seconds": round(elapsed, 1),
            "seconds_per_call_throughput": round(elapsed / max(1, len(done)), 1), "mean_run_seconds": round(sum(runs) / max(1, len(runs)), 1),
            "longest_wait_seconds": waits[-1] if waits else None, "median_wait_seconds": waits[len(waits) // 2] if waits else None,
            "health_after": http("GET", base + "/ready")[0]}
        print("C:", report["C_load"], flush=True)

        # ---- D. simultaneous /api/evaluate
        t0 = time.time()

        def evaluate(i):
            name, d = calls[(i + 60) % len(calls)]
            t1 = time.time()
            code, body, hdr = http("POST", base + "/api/evaluate", body_of(d, f"sim-{i}"), timeout=400)
            return {"i": i, "http": code, "seconds": round(time.time() - t1, 1), "job_id": (body.get("detail") or {}).get("job_id") if code == 503 else None}
        with ThreadPoolExecutor(max_workers=args.simultaneous) as ex:
            sim = list(ex.map(evaluate, range(args.simultaneous)))
        late = [s for s in sim if s["http"] == 503]
        late_done = 0
        for s in late:
            for _ in range(200):
                code, body, _ = http("GET", base + f"/api/jobs/{s['job_id']}", timeout=30)
                if code == 200 and body["status"] in ("done", "failed"):
                    late_done += body["status"] == "done"
                    break
                time.sleep(3)
        report["D_simultaneous_evaluate"] = {"sent": len(sim), "answered_200": sum(s["http"] == 200 for s in sim), "timed_out_503": len(late),
                                             "timed_out_later_finished": late_done, "other_codes": sorted({s["http"] for s in sim} - {200, 503}),
                                             "slowest_answer_seconds": max(s["seconds"] for s in sim), "total_seconds": round(time.time() - t0, 1)}
        print("D:", report["D_simultaneous_evaluate"], flush=True)

        # ---- E. worst-case transcript
        if not args.skip_worst:
            turns = worst_case_call(calls)
            body = {"transcript": turns, "call_id": "worst-case", "tenant_id": "load-test"}
            size = len(json.dumps(body))
            t0 = time.time()
            code, resp, _ = http("POST", base + "/api/jobs", body)
            job_id = resp.get("job_id")
            final = None
            while code == 202 and time.time() - t0 < 1800:
                c2, b2, _ = http("GET", base + f"/api/jobs/{job_id}", timeout=30)
                if c2 == 200 and b2["status"] in ("done", "failed"):
                    final = b2
                    break
                time.sleep(5)
            meta = (final or {}).get("result", {}).get("meta", {}) if final and final["status"] == "done" else {}
            report["E_worst_case"] = {"request_bytes": size, "turns": len(turns), "submit_http": code, "status": (final or {}).get("status"),
                                      "seconds": round(time.time() - t0, 1), "model_rows": meta.get("model_rows"), "model_words": meta.get("model_words"),
                                      "error": (final or {}).get("error"), "alive_after": http("GET", base + "/health")[0]}
            print("E:", report["E_worst_case"], flush=True)
    finally:
        stop.set()
        ws, pws, commit = memory_gb(proc)
        report["memory"] = {"peak_working_set_gb": round(max(mem["peak_ws"], pws), 2), "peak_commit_gb": round(max(mem["peak_commit"], commit), 2),
                            "working_set_now_gb": round(ws, 2), "limit_target_gb": 8.0}
        report["server_still_running_at_end"] = proc.poll() is None
        report["total_test_minutes"] = round((time.time() - t_start) / 60, 1)
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, default=str)
        print("memory:", report["memory"], flush=True)
        print("SERVICE TEST DONE", flush=True)


if __name__ == "__main__":
    main()
