"""Case memory: write every investigated case into TigerGraph so the next investigation can retrieve it."""
from __future__ import annotations
import json, pandas as pd
from . import llm


def write_case(g, ans: dict, case: dict):
    c = ans["case"]; cid = c["graph_case_id"]
    rec = {k: v for k, v in ans.items() if k not in ("trace", "reasoning")}
    now = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = g.conn
    conn.upsertVertex("AgentCase", cid, {"case_ref": ans["case_id"], "status": c["status"], "verdict": c["verdict"], "pattern": c["pattern"], "probability": c["fraud_probability"],
                                          "exposure": c["exposure_usd"], "summary": c["summary"][:3000], "created_at": now, "updated_at": now, "record": json.dumps(rec)[:60000]})
    sim_closed = [s for s in c["similar_prior_cases"] if not str(s).startswith("AC-")]
    sim_agent = [s for s in c["similar_prior_cases"] if str(s).startswith("AC-")]
    edges = {"AC_ON_CARD": ("Card", [case["card_id"]]), "AC_INVOLVES": ("Transaction", c["affected_txn_ids"] or [str(case["flagged_txn_id"])]),
             "AC_CONNECTED": ("Card", c["connected_card_ids"]), "AC_SIMILAR": ("ClosedCase", sim_closed), "AC_SIMILAR_AGENT": ("AgentCase", sim_agent)}
    for et, (tt, targets) in edges.items():
        for t in targets:
            try: conn.upsertEdge("AgentCase", cid, et, tt, str(t))
            except Exception: pass
    try:
        v = llm.embed([f"{c['pattern']} | {c['verdict']} | {c['summary']}"])[0]
        conn.upsertVertex("AgentCase", cid, {"emb": v})
    except Exception:
        pass
