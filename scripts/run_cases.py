"""Run the agent on the 20 exam cases; writes cases/<case_id>.json (+ traces for the UI)."""
import sys, json, time, pandas as pd, pathlib
sys.path.insert(0, "/home/vinay/hackerhouse")
from agent.data_access import GraphClient
from agent.investigator import Investigator

OUT = pathlib.Path("/home/vinay/hackerhouse/cases"); OUT.mkdir(exist_ok=True)
TR = pathlib.Path("/home/vinay/hackerhouse/data/traces"); TR.mkdir(exist_ok=True, parents=True)
only = set(sys.argv[1:])
g = GraphClient(); inv = Investigator(g)
cp = pd.read_csv("/home/vinay/hackerhouse/data/HHGOA_IEEE/case_pack.csv")
rows = []
for r in cp.to_dict("records"):
    if only and r["case_id"] not in only: continue
    try:
        a = inv.run(r)
    except Exception as e:
        import traceback; traceback.print_exc(); print("FAILED", r["case_id"], e); continue
    trace = a.pop("trace"); a.pop("reasoning", None) if False else None
    (TR / f"{r['case_id']}.json").write_text(json.dumps({"trace": trace, "reasoning": a.get("reasoning", [])}, default=str))
    out = {k: v for k, v in a.items() if k != "reasoning"}
    (OUT / f"{r['case_id']}.json").write_text(json.dumps(out, indent=2, default=str))
    c = a["case"]
    rows.append((r["case_id"], r["trigger_type"][:5], r["risk_score"], c["verdict"], c["fraud_probability"], c["pattern"], len(c["affected_txn_ids"]), c["exposure_usd"], c["status"],
                 "|".join(x["action"] for x in a["next_best_actions"]["final"]), a["sar"]["file"], a["latency_s"]))
    print(rows[-1], flush=True)
print(pd.DataFrame(rows, columns=["case", "trig", "risk", "verdict", "p", "pattern", "n_tx", "expo", "status", "final_actions", "sar", "lat"]).to_string())
