"""Slim the 708 MB transactions.csv into load-ready CSVs for TigerGraph.

Adds: card_id (customer + sorted card-signature index, matches the case pack),
device_id (DeviceInfo|OS|browser|screen profile), NEXT edges per card.
"""
import pandas as pd, numpy as np, pathlib

SRC = pathlib.Path("/home/vinay/hackerhouse/data/HHGOA_IEEE")
OUT = pathlib.Path("/home/vinay/hackerhouse/data/slim"); OUT.mkdir(exist_ok=True)

TX_COLS = ["TransactionID", "TransactionAmt", "ProductCD", "card2", "card3", "card4", "card5", "card6",
           "addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain", "customer_id", "ts",
           "channel", "risk_score", "C1", "C2", "C5", "C13", "C14", "D1", "D2", "D3", "D10", "D15"] + [f"M{i}" for i in range(1, 10)]

t = pd.read_csv(SRC / "transactions.csv", usecols=TX_COLS)
ident = pd.read_csv(SRC / "identity.csv", usecols=["TransactionID", "id_15", "id_23", "id_30", "id_31", "id_33", "id_34", "DeviceType", "DeviceInfo"])
print("tx", t.shape, "identity", ident.shape)

# --- card ids: per customer, order distinct (card2,card3,card4,card5,card6) tuples, NaN first
sig_cols = ["card2", "card3", "card4", "card5", "card6"]
sig = t[["customer_id"] + sig_cols].drop_duplicates().sort_values(["customer_id"] + sig_cols, na_position="first")
sig["k"] = sig.groupby("customer_id").cumcount() + 1
sig["card_id"] = sig.customer_id + "-K" + sig.k.astype(str)
t = t.merge(sig[["customer_id"] + sig_cols + ["card_id"]], on=["customer_id"] + sig_cols, how="left")

# --- device profiles
ident["profile"] = (ident.DeviceInfo.fillna("") + " | " + ident.id_30.fillna("") + " | " + ident.id_31.fillna("") + " | " + ident.id_33.fillna(""))
ident.loc[(ident.DeviceInfo.isna()) & ident.id_30.isna() & ident.id_31.isna() & ident.id_33.isna(), "profile"] = np.nan
codes, uniques = pd.factorize(ident.profile)
ident["device_id"] = np.where(codes >= 0, ["D%06d" % (c + 1) for c in codes], "")
t = t.merge(ident[["TransactionID", "id_15", "id_23", "id_34", "DeviceType", "device_id", "profile", "id_30", "id_31", "id_33", "DeviceInfo"]], on="TransactionID", how="left")

t["m_false"] = sum((t[f"M{i}"] == "F").astype(int) for i in range(1, 10))
t["m_true"] = sum((t[f"M{i}"] == "T").astype(int) for i in range(1, 10))
t["region"] = t.addr1.fillna(-1).astype(int).astype(str).replace("-1", "")
t["ts"] = pd.to_datetime(t.ts)
t = t.sort_values(["card_id", "ts", "TransactionID"]).reset_index(drop=True)

# --- transactions (one row -> Transaction vertex + Card/Customer/Device/Email/Region vertices and edges)
tx = t[["TransactionID", "TransactionAmt", "ts", "ProductCD", "channel", "risk_score", "card_id", "customer_id", "card4", "card6",
        "region", "addr2", "P_emaildomain", "R_emaildomain", "device_id", "DeviceInfo", "id_30", "id_31", "id_33", "DeviceType",
        "id_15", "id_23", "id_34", "dist1", "D1", "C1", "C2", "C5", "C13", "C14", "m_false", "m_true"]].copy()
tx["ts"] = tx.ts.dt.strftime("%Y-%m-%d %H:%M:%S")
for c in ["dist1", "D1", "C1", "C2", "C5", "C13", "C14"]:
    tx[c] = tx[c].fillna(-1)  # -1 = missing
tx["addr2"] = tx.addr2.fillna(-1).astype(int).replace(-1, "")
tx.to_csv(OUT / "tx.csv", index=False)

# --- NEXT edges within a card
t["next_id"] = t.groupby("card_id").TransactionID.shift(-1)
t[t.next_id.notna()][["TransactionID", "next_id"]].astype(int).to_csv(OUT / "next.csv", index=False)

# --- closed cases
h = pd.read_csv(SRC / "closed_cases_history.csv")
h.to_csv(OUT / "closed_cases.csv", index=False)
rows_i, rows_c = [], []
for r in h.itertuples():
    for x in str(r.txn_ids).split("|"):
        if x and x != "nan": rows_i.append((r.case_id, int(float(x))))
    if isinstance(r.connected_card_ids, str):
        for c in r.connected_card_ids.split("|"):
            if c: rows_c.append((r.case_id, c))
pd.DataFrame(rows_i, columns=["case_id", "txn_id"]).to_csv(OUT / "case_txn.csv", index=False)
pd.DataFrame(rows_c, columns=["case_id", "card_id"]).to_csv(OUT / "case_conn.csv", index=False)
print("cards", t.card_id.nunique(), "devices", len(uniques), "next edges", t.next_id.notna().sum(), "case_txn", len(rows_i), "case_conn", len(rows_c))
