"""Run the GSQL loading jobs against the local TigerGraph container."""
import pyTigerGraph as tg, time
c = tg.TigerGraphConnection(host="http://127.0.0.1", restppPort=9000, gsPort=14240, username="tigergraph", password="tigergraph", graphname="FraudGraph")
D = "/home/tigergraph/slim/"
for job, f in [("load_tx", "tx.csv"), ("load_next", "next.csv"), ("load_cases", "closed_cases.csv"), ("load_case_txn", "case_txn.csv"), ("load_case_conn", "case_conn.csv")]:
    t = time.time()
    out = c.gsql(f'USE GRAPH FraudGraph\nRUN LOADING JOB {job} USING f="{D}{f}"')
    print(job, f"{time.time()-t:.0f}s", out[-400:].replace("\n", " | "), flush=True)
print(c.getVertexCount("*"))
print({e: c.getEdgeCount(e) for e in ["MADE", "NEXT", "FROM_DEVICE", "INVOLVES", "CONNECTED_TO"]})
