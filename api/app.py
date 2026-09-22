"""FastAPI backend: case queue, saved case files, live streamed investigations, graph stats."""
from __future__ import annotations
import sys, json, asyncio, threading, queue, pathlib, pandas as pd
sys.path.insert(0, "/home/vinay/hackerhouse")
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from agent.data_access import make_graph_client
from agent.investigator import Investigator

ROOT = pathlib.Path("/home/vinay/hackerhouse")
app = FastAPI(title="FraudGraph Agent")
graph = make_graph_client()
PACK = pd.read_csv(ROOT / "data/HHGOA_IEEE/case_pack.csv").to_dict("records")
lock = threading.Lock()


def _load(case_id):
    p = ROOT / "cases" / f"{case_id}.json"
    if not p.exists(): return None
    a = json.loads(p.read_text())
    t = ROOT / "data/traces" / f"{case_id}.json"
    if t.exists(): a.update(json.loads(t.read_text()))
    return a


@app.get("/api/cases")
def cases():
    out = []
    for r in PACK:
        a = _load(r["case_id"])
        out.append({**{k: (None if pd.isna(v) else v) for k, v in r.items()},
                    "investigated": bool(a), "verdict": a and a["case"]["verdict"], "probability": a and a["case"]["fraud_probability"],
                    "pattern": a and a["case"]["pattern"], "status": a and a["case"]["status"], "exposure": a and a["case"]["exposure_usd"],
                    "actions": a and [x["action"] for x in a["next_best_actions"]["final"]]})
    return out


@app.get("/api/cases/{case_id}")
def case(case_id: str):
    a = _load(case_id)
    if not a: raise HTTPException(404, "not investigated yet")
    return a


@app.get("/api/stats")
def stats():
    v = graph.vertex_counts()
    saved = [json.loads(p.read_text()) for p in (ROOT / "cases").glob("HHG-*.json")]
    return {"vertices": v, "transactions": v.get("Transaction"), "cards": v.get("Card"), "closed_cases": v.get("ClosedCase"), "agent_cases": v.get("AgentCase"),
            "investigated": len(saved), "sar": sum(1 for a in saved if a["sar"]["file"]), "avg_latency": round(sum(a["latency_s"] for a in saved) / max(len(saved), 1), 1)}


@app.post("/api/investigate/{case_id}")
def investigate(case_id: str):
    row = next((r for r in PACK if r["case_id"] == case_id), None)
    if not row: raise HTTPException(404, "unknown case")
    q: queue.Queue = queue.Queue()

    def work():
        with lock:
            try:
                inv = Investigator(graph, on_step=lambda ev: q.put(("step", ev)))
                a = inv.run({k: (None if pd.isna(v) else v) for k, v in row.items()})
                trace = a.pop("trace"); reasoning = a.get("reasoning", [])
                (ROOT / "cases" / f"{case_id}.json").write_text(json.dumps({k: v for k, v in a.items() if k != "reasoning"}, indent=2, default=str))
                (ROOT / "data/traces" / f"{case_id}.json").write_text(json.dumps({"trace": trace, "reasoning": reasoning}, default=str))
                a["trace"] = trace
                q.put(("done", a))
            except Exception as e:
                q.put(("error", {"error": str(e)}))

    threading.Thread(target=work, daemon=True).start()

    async def gen():
        while True:
            try:
                kind, payload = await asyncio.get_event_loop().run_in_executor(None, lambda: q.get(timeout=180))
            except Exception:
                break
            yield f"event: {kind}\ndata: {json.dumps(payload, default=str)}\n\n"
            if kind in ("done", "error"): break
    return StreamingResponse(gen(), media_type="text/event-stream")


app.mount("/", StaticFiles(directory=ROOT / "ui", html=True), name="ui")
