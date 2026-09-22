import sys, random, joblib; sys.path.insert(0, "/home/vinay/hackerhouse")
import pandas as pd, numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold
from agent.data_access import load_frames
from agent.episode import candidates, CAND_FEATS

tx, cases, ct = load_frames()
by_card = {k: g.sort_values("ts").reset_index(drop=True) for k, g in tx.groupby("card_id")}
txi = tx.set_index("TransactionID")
fr = cases[cases.outcome == "confirmed_fraud"]
random.seed(3); rows = []
for r in fr.itertuples():
    ids = [int(float(x)) for x in str(r.txn_ids).split("|")]
    first = int(float(r.first_fraud_txn_id)); card = txi.loc[first, "card_id"]
    ids = [i for i in ids if txi.loc[i, "card_id"] == card]
    for a in {first, random.choice(ids)}:
        d = candidates(by_card[card], a)
        d["y"] = d.TransactionID.isin(ids).astype(int); d["case_id"] = r.case_id; d["anchor"] = a; d["pattern"] = r.pattern
        d["is_anchor"] = (d.TransactionID == a).astype(int)
        rows.append(d)
D = pd.concat(rows, ignore_index=True)
print(D.shape, D.y.mean().round(3))
oof = np.zeros(len(D))
for tr, te in GroupKFold(5).split(D, groups=D.case_id):
    m = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.08, max_iter=200, random_state=1).fit(D.iloc[tr][CAND_FEATS], D.iloc[tr].y)
    oof[te] = m.predict_proba(D.iloc[te][CAND_FEATS])[:, 1]
D["p"] = oof
for thr in (0.3, 0.4, 0.5):
    g = D.assign(pred=((D.p >= thr) | (D.is_anchor == 1)).astype(int))
    tp = g.groupby(["case_id", "anchor"]).apply(lambda x: pd.Series({"tp": ((x.pred == 1) & (x.y == 1)).sum(), "pp": x.pred.sum(), "ap": x.y.sum(), "exact": int(((x.pred == 1) == (x.y == 1)).all())}))
    P, R = tp.tp.sum() / tp.pp.sum(), tp.tp.sum() / tp.ap.sum()
    print(f"thr {thr}: precision {P:.3f} recall {R:.3f} F1 {2*P*R/(P+R):.3f} exact-episode {tp.exact.mean():.3f}")
    if thr == 0.4:
        g2 = g.merge(tp.reset_index()[["case_id", "anchor", "exact"]], on=["case_id", "anchor"])
        print(g2.groupby("pattern").exact.mean().round(3).to_dict())
m = HistGradientBoostingClassifier(max_depth=6, learning_rate=0.08, max_iter=200, random_state=1).fit(D[CAND_FEATS], D.y)
joblib.dump(m, "/home/vinay/hackerhouse/agent/episode_model.joblib")
