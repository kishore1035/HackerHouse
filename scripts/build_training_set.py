"""Turn the 5,565 closed cases into a labeled feature table (anchored at several txns per case)."""
import pandas as pd, numpy as np, random, sys, time
sys.path.insert(0, "/home/vinay/hackerhouse")
from agent.data_access import load_frames, FrameClient
from agent import features

tx, cases, case_txn = load_frames()
client = FrameClient(tx, cases, case_txn)
random.seed(7)
tx_idx = tx.set_index('TransactionID')
rows, t0 = [], time.time()
for i, r in enumerate(cases.itertuples()):
    ids = [int(float(x)) for x in str(r.txn_ids).split("|") if x and x != "nan"]
    first = int(float(r.first_fraud_txn_id)) if pd.notna(r.first_fraud_txn_id) else ids[0]
    anchors = [first] + [x for x in random.sample(ids, min(2, len(ids))) if x != first]
    for a in anchors[:3]:
        try:
            cid = tx_idx.loc[a, 'card_id']
            f, _ = features.build(client, a, cid)
        except Exception as e:
            print("skip", r.case_id, a, e); continue
        f.update(case_id=r.case_id, anchor=a, is_first=int(a == first), fraud=int(r.outcome == "confirmed_fraud"), pattern=r.pattern,
                 opened_at=r.opened_at, exposure=r.exposure_usd)
        rows.append(f)
    if i % 500 == 0: print(i, f"{time.time()-t0:.0f}s", flush=True)
df = pd.DataFrame(rows)
df.to_parquet("/home/vinay/hackerhouse/data/train_features.parquet")
print(df.shape, df.fraud.mean(), df.pattern.value_counts().to_dict())
