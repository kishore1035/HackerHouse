"""Data access: TigerGraph (production) and in-memory (offline training) clients share one interface."""
from __future__ import annotations
import pandas as pd, numpy as np

TX_COLS = ["TransactionID", "TransactionAmt", "ts", "ProductCD", "channel", "risk_score", "card_id", "customer_id", "region", "addr2",
           "P_emaildomain", "R_emaildomain", "device_id", "id_15", "id_23", "id_34", "dist1", "D1", "C1", "C2", "C5", "C13", "C14", "m_false", "m_true"]


class FrameClient:
    """Same interface as GraphClient, backed by the slim CSVs (used for training + parity checks)."""

    def __init__(self, tx: pd.DataFrame, cases: pd.DataFrame, case_txn: pd.DataFrame):
        self.tx = tx
        self.by_card = {k: g.sort_values("ts") for k, g in tx.groupby("card_id")}
        self.by_dev = {k: g[["TransactionID", "card_id", "ts", "TransactionAmt"]] for k, g in tx[tx.device_id.astype(str) != ""].groupby("device_id")}
        self.cases = cases.set_index("case_id")
        ct = case_txn.merge(tx[["TransactionID", "device_id"]], left_on="txn_id", right_on="TransactionID")
        self.case_dev = ct[ct.device_id.astype(str) != ""][["case_id", "device_id"]].drop_duplicates()
        self.dev_cases = {k: g.case_id.tolist() for k, g in self.case_dev.groupby("device_id")}
        self.card_cases = {k: g.case_id.tolist() for k, g in cases.groupby("card_id")}

    def card_txns(self, card_id):
        return self.by_card[card_id]

    def device_txns(self, dev):
        return self.by_dev.get(dev, pd.DataFrame(columns=["TransactionID", "card_id", "ts", "TransactionAmt"]))

    def _cases(self, ids, before):
        out = []
        for cid in ids:
            r = self.cases.loc[cid]
            if before is None or r.closed_at < before:
                out.append({"case_id": cid, "outcome": r.outcome, "pattern": r.pattern, "card_id": r.card_id})
        return out

    def device_closed_cases(self, dev, before=None):
        return self._cases(self.dev_cases.get(dev, []), before)

    def card_closed_cases(self, card_id, before=None):
        return self._cases(self.card_cases.get(card_id, []), before)


def load_frames(slim="/home/vinay/hackerhouse/data/slim/"):
    tx = pd.read_csv(slim + "tx.csv", parse_dates=["ts"], dtype={"TransactionID": int, "region": str, "device_id": str, "addr2": str}, usecols=TX_COLS)
    tx["device_id"] = tx.device_id.fillna("")
    tx["region"] = tx.region.where(tx.region.notna() & (tx.region != ""), None)
    cases = pd.read_csv(slim + "closed_cases.csv", parse_dates=["opened_at", "closed_at"])
    case_txn = pd.read_csv(slim + "case_txn.csv")
    return tx, cases, case_txn


class GraphClient:
    """TigerGraph-backed client. Every call is an installed GSQL query; `calls` counts them for the answer file."""

    def __init__(self, host="http://127.0.0.1", rest=9000, gs=14240, user="tigergraph", pw="tigergraph"):
        import pyTigerGraph as tg
        self.conn = tg.TigerGraphConnection(host=host, restppPort=rest, gsPort=gs, username=user, password=pw, graphname="FraudGraph")
        self.calls = 0
        self.log: list[str] = []
        self._cache: dict = {}

    def q(self, name: str, **params):
        key = (name, tuple(sorted((k, tuple(v) if isinstance(v, list) else v) for k, v in params.items())))
        if key in self._cache:
            return self._cache[key]
        self.calls += 1
        fmt = lambda v: v[0] if isinstance(v, tuple) else ("<vector>" if isinstance(v, list) else v)
        self.log.append("query:%s(%s)" % (name, ", ".join("%s=%s" % (k, fmt(v)) for k, v in params.items())))
        r = self.conn.runInstalledQuery(name, params, timeout=120000)
        self._cache[key] = r
        return r

    @staticmethod
    def _vt(rows, cols):
        return pd.DataFrame([{"v_id": r["v_id"], **{k.split(".")[-1]: v for k, v in r["attributes"].items()}} for r in rows]) if rows else pd.DataFrame(columns=["v_id"] + cols)

    def get_vertex(self, vtype: str, vid):
        try:
            r = self.conn.getVerticesById(vtype, vid)
            return r[0] if r else None
        except Exception:
            return None

    def upsert_vertex(self, vtype: str, vid, attrs: dict):
        return self.conn.upsertVertex(vtype, str(vid), attrs)

    def upsert_edge(self, from_type: str, from_id, etype: str, to_type: str, to_id, attrs: dict | None = None):
        return self.conn.upsertEdge(from_type, str(from_id), etype, to_type, str(to_id), attrs or {})

    def vertex_counts(self) -> dict:
        return self.conn.getVertexCount("*")

    def card_txns(self, card_id):
        r = self.q("card_txns", cardv=(card_id,))
        df = self._vt(r[0]["txns"], [])
        df = df.rename(columns={"v_id": "TransactionID", "amount": "TransactionAmt", "product": "ProductCD", "dev_new": "id_15", "proxy_type": "id_23",
                                "match_status": "id_34", "d1": "D1", "c1": "C1", "c2": "C2", "c5": "C5", "c13": "C13", "c14": "C14"})
        df["TransactionID"] = df.TransactionID.astype(int)
        df["ts"] = pd.to_datetime(df.ts)
        df["device_id"] = df.device_id.fillna("")
        for c in ("id_15", "id_23"):
            df[c] = df[c].replace("", np.nan)
        df["region"] = df.region.replace("", None)
        return df.sort_values("ts").reset_index(drop=True)

    def device_txns(self, dev):
        r = self.q("device_txns", devv=(dev,))
        df = self._vt(r[0]["txns"], ["amount", "ts", "card_id"]).rename(columns={"v_id": "TransactionID", "amount": "TransactionAmt"})
        df["ts"] = pd.to_datetime(df.ts)
        return df

    def _case_rows(self, rows, before):
        out = []
        for r in rows:
            a = {k.split(".")[-1]: v for k, v in r["attributes"].items()}
            if before is None or pd.Timestamp(a["closed_at"]) < before:
                out.append({"case_id": r["v_id"], "outcome": a["outcome"], "pattern": a["pattern"], "card_id": a["card_id"]})
        return out

    def device_closed_cases(self, dev, before=None):
        r = self.q("device_closed_cases", devv=(dev,))
        return self._case_rows(r[0]["cases"], before)

    def card_closed_cases(self, card_id, before=None):
        r = self.q("card_closed_cases", cardv=(card_id,))
        seen, out = set(), []
        for c in self._case_rows(r[0]["own_cases"], before) + self._case_rows(r[1]["connected_cases"], before):
            if c["case_id"] not in seen:
                seen.add(c["case_id"]); out.append(c)
        return out

    def ring_expand(self, card_id):
        r = self.q("ring_expand", cardv=(card_id,))
        return r[0]["device_to_cards"], r[1]["card_to_devices"]


def make_graph_client(**kw):
    """Per the HHGOA brief: 'Use TigerGraph MCP to expose graph capabilities and data to the agent.'
    Set USE_TIGERGRAPH_MCP=false to force the direct pyTigerGraph client (e.g. tigergraph-mcp not installed)."""
    import os
    if os.environ.get("USE_TIGERGRAPH_MCP", "true").strip().lower() in ("1", "true", "yes"):
        try:
            from .mcp_client import MCPGraphClient
            return MCPGraphClient(**kw)
        except Exception as e:
            import sys
            print(f"TigerGraph MCP unavailable ({e}); falling back to the direct pyTigerGraph client", file=sys.stderr)
    return GraphClient(**kw)
