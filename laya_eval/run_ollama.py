"""Ollama (llama3.1 8B) baseline on the gold set, using the pipeline's OWN prompts and parsing. Resumable.

Usage: python laya-finetuning/laya_eval/run_ollama.py [--limit N]
Writes laya-finetuning/laya_eval/results/ollama.jsonl with the raw reply and the verdict the pipeline would have produced.

Fidelity:
Needs the Ollama-era code: set QA_OLLAMA_ROOT to a version-10 checkout (default ../qa-analysis-ollama).

  * transport: src/services/llm_adapter.py on version-10 (same model default, temperature 0.1, num_ctx 8192)
  * empathy / active_listening / ownership / rapport / probing: the one-word prompts copied verbatim from
    dynamic_evaluator.py lines 198, 221, 245-250, 268-272, 291-300, with the same reply parsing
  * resolved / escalation / hostility: dynamic_evaluator.build_dynamic_prompt + parse_dynamic_ratings,
    format=json, num_predict=768, up to 3 attempts until the item is rated (run_batch, lines 326-343)
  * Escalation and Hostility are NOT in the repo's default criteria; their descriptions below are an
    explicit assumption written in the repo's VIOLATION-BASED style.
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
# llm_adapter only exists on the Ollama branches, so point this at a version-10 checkout.
QA_ROOT = Path(os.environ.get("QA_OLLAMA_ROOT", HERE.parents[2] / "qa-analysis-ollama"))
sys.path.insert(0, str(QA_ROOT))

from src.services.llm_adapter import query_llm, query_llm_with_state  # noqa: E402
from src.services.dynamic_evaluator import build_dynamic_prompt, parse_dynamic_ratings  # noqa: E402

CRITERION_DEFS = {
    "resolved": {"name": "Confirmed the issue is resolved",  # verbatim from resources/criteria_config.json
                 "description": "Did the agent explicitly confirm that the issue was resolved? Output YES or NO."},
    "escalation": {"name": "Escalation",
                   "description": "VIOLATION-BASED: Default to PASS. Rate FAIL only if the customer explicitly asks for a supervisor, "
                                  "manager or escalation and you can quote a specific agent line that refuses, ignores or discourages it. "
                                  "Handling the request properly, or no request at all, means PASS."},
    "hostility": {"name": "Hostility",
                  "description": "VIOLATION-BASED: Default to PASS. Rate FAIL only if you can quote a specific agent line that is hostile, "
                                 "abusive, insulting, threatening or mocking toward the customer, or the agent hangs up on the customer. "
                                 "A calm, professional agent means PASS even if the customer is angry."},
}


def one_word(prompt, parse):
    reply = query_llm(prompt, label="eval", format=None)
    err = reply.startswith("Error reaching Ollama")
    up = reply.upper()
    return reply, parse(up), err, ("PASS" not in up and "FAIL" not in up)


def judge(item):
    c, text = item["criterion"], item["text"]
    if c == "empathy":
        p = (f"<SNIPPET>\n{text}\n</SNIPPET>\nRead this snippet. Was the agent empathetic to the customer's frustration, or were they rude/dismissive? "
             "CRITICAL INSTRUCTION: Output EXACTLY ONE WORD. Do not explain. Reply ONLY with PASS (if empathetic) or FAIL (if rude).")
        return one_word(p, lambda up: "PASS" if "PASS" in up else "FAIL")
    if c == "active_listening":
        p = (f"<SNIPPET>\n{text}\n</SNIPPET>\nDid the agent unnecessarily repeat themselves because they weren't listening? "
             "CRITICAL INSTRUCTION: Output EXACTLY ONE WORD. Do not explain. Reply ONLY with PASS (no) or FAIL (yes).")
        return one_word(p, lambda up: "FAIL" if "FAIL" in up else "PASS")
    if c == "ownership":
        p = (f"<AGENT LINES>\n{text}\n</AGENT LINES>\n"
             "Do any of these agent lines blame another team/department, deflect responsibility, "
             "refuse to help, or tell the customer to contact someone else? "
             "Output EXACTLY ONE WORD: FAIL if any line clearly does, otherwise PASS.")
        return one_word(p, lambda up: "FAIL" if "FAIL" in up else "PASS")
    if c == "rapport":
        p = (f"<AGENT LINES>\n{text}\n</AGENT LINES>\n"
             "Are any of these agent lines rude, condescending, dismissive, sarcastic, or unprofessional? "
             "Output EXACTLY ONE WORD: FAIL if any line clearly is, otherwise PASS.")
        return one_word(p, lambda up: "FAIL" if "FAIL" in up else "PASS")
    if c == "probing":
        q_txt = "\n".join(f"- {q}" for q in item["questions"])
        p = (f"CUSTOMER PROBLEM: {item['problem']}\n\nThe agent asked these questions during the call:\n{q_txt}\n\n"
             "A DIAGNOSTIC question investigates the CAUSE or specifics of the technical problem "
             "(for example: when it started, what changed recently, which device/model/settings, what error or lights appear, what the customer already tried). "
             "Do NOT count any of these as diagnostic: greetings like 'how can I help you', "
             "identity verification (PIN, account number, name), confirmations like 'is that right', "
             "or questions about whether the fix worked at the end. "
             "Did the agent ask AT LEAST ONE genuine diagnostic question that investigates the problem? "
             "Output EXACTLY ONE WORD: PASS if yes, FAIL if no.")
        return one_word(p, lambda up: "PASS" if "PASS" in up else "FAIL")
    # batch path (resolved = B2 tail only, no context; escalation/hostility = B3 full call + problem context)
    chunk = [{"name": "Technical Knowledge" if c == "resolved" else "Compliance", "line_items": [CRITERION_DEFS[c]]}]
    ctx = ""
    if c != "resolved":
        cust = [ln.split(":", 1)[1].strip() for ln in item["lines"] if ln.startswith("Customer:")]
        ctx = f"\nCUSTOMER PROBLEM CONTEXT:\n{' '.join(cust[:10])}\n"
    prefix, suffix = build_dynamic_prompt(text, chunk, [], [], "Call", [], ctx)
    reply, rating = "", "NOT_RATED"
    for _ in range(3):
        reply = query_llm_with_state(prefix, suffix, label="batch", format="json", num_predict=768)
        rating = parse_dynamic_ratings(reply, chunk)[0]["rating"]
        if rating != "NOT_RATED":
            break
    err = reply.startswith("Error reaching Ollama")
    verdict = {"YES": "PASS", "NO": "FAIL"}.get(rating, rating)
    unparsed = verdict not in ("PASS", "FAIL")
    if unparsed:
        verdict = "FAIL"  # run_batch consumer turns NOT_RATED into FAIL (dynamic_evaluator.py:363)
    return reply, verdict, err, unparsed


if __name__ == "__main__":
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None
    CRITERIA = ["empathy", "active_listening", "ownership", "rapport", "probing", "resolved", "escalation", "hostility"]
    items = []
    for c in CRITERIA:
        with open(HERE / "data" / f"{c}.jsonl", encoding="utf-8") as f:
            items += [json.loads(l) for l in f]
    if limit:
        # one item per criterion first, so a small run still touches every prompt type
        items = [next(i for i in items if i["criterion"] == c) for c in CRITERIA][:limit]
    out = HERE / "results" / "ollama.jsonl"
    out.parent.mkdir(exist_ok=True)
    done = {json.loads(l)["id"] for l in open(out, encoding="utf-8")} if out.exists() else set()
    # held-out test items first, so the Laya-vs-Ollama comparison is available as early as possible
    todo = sorted((i for i in items if i["id"] not in done), key=lambda i: (i["split"] != "test", i["criterion"]))
    print(f"[ollama] {len(done)} done, {len(todo)} to run", flush=True)
    t_all = time.time()
    with open(out, "a", encoding="utf-8") as f:
        for n, it in enumerate(todo, 1):
            t0 = time.perf_counter()
            reply, verdict, err, unparsed = judge(it)
            dt = time.perf_counter() - t0
            f.write(json.dumps({"id": it["id"], "criterion": it["criterion"], "verdict": verdict, "error": err,
                                "unparsed": unparsed, "latency_s": round(dt, 3), "reply": reply[:400]}) + "\n")
            f.flush()
            print(f"[ollama] {n}/{len(todo)} {it['id']} -> {verdict}{' ERR' if err else ''}{' UNPARSED' if unparsed else ''} ({dt:.1f}s)  total {time.time()-t_all:.0f}s", flush=True)
