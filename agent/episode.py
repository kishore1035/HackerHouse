"""Episode reconstruction: which transactions on the card belong to the same fraud episode as the flagged one."""
from __future__ import annotations
import numpy as np, pandas as pd

HALF = pd.Timedelta(hours=72)
CAND_FEATS = ["dt_h", "adt_h", "amt", "log_amt", "amt_z", "amt_ratio_flag", "online", "prod_C", "prod_H", "prod_R", "prod_S", "prod_W", "same_prod", "same_channel",
              "region_freq", "same_region", "is_home", "has_dev", "same_dev", "dev_unseen", "dev_new", "proxy", "m_false", "m_true", "c1", "c2", "c13", "c14",
              "d1", "dist1", "rank_abs", "n_cand", "flag_online", "flag_prod_new", "cand_prod_seen", "flag_region_freq"]


def candidates(card: pd.DataFrame, anchor_id: int) -> pd.DataFrame:
    a = card[card.TransactionID == anchor_id].iloc[0]
    T = a.ts
    prior = card[card.ts < T - pd.Timedelta(hours=72)]
    if len(prior) < 5:
        prior = card[card.ts < T]
    cand = card[(card.ts >= T - HALF) & (card.ts <= T + HALF)].copy()
    n = len(prior)
    pm, ps = prior.TransactionAmt.mean(), prior.TransactionAmt.std()
    regf = prior.region.astype(str).value_counts(normalize=True) if n else pd.Series(dtype=float)
    home = regf.index[0] if len(regf) else None
    prior_devs = set(prior.device_id) - {""}
    prior_prods = set(prior.ProductCD)
    d = pd.DataFrame(index=cand.index)
    d["TransactionID"] = cand.TransactionID
    d["dt_h"] = (cand.ts - T).dt.total_seconds() / 3600
    d["adt_h"] = d.dt_h.abs()
    d["amt"] = cand.TransactionAmt
    d["log_amt"] = np.log1p(cand.TransactionAmt)
    d["amt_z"] = (cand.TransactionAmt - pm) / (ps if ps and ps > 0 else 1) if n > 2 else np.nan
    d["amt_ratio_flag"] = cand.TransactionAmt / max(a.TransactionAmt, 0.01)
    d["online"] = (cand.channel == "online").astype(int)
    for p in "CHRSW":
        d[f"prod_{p}"] = (cand.ProductCD == p).astype(int)
    d["same_prod"] = (cand.ProductCD == a.ProductCD).astype(int)
    d["same_channel"] = (cand.channel == a.channel).astype(int)
    d["region_freq"] = cand.region.astype(str).map(regf).fillna(0) if n else np.nan
    d["same_region"] = (cand.region.astype(str) == str(a.region)).astype(int)
    d["is_home"] = (cand.region.astype(str) == home).astype(int) if home else 0
    d["has_dev"] = (cand.device_id != "").astype(int)
    d["same_dev"] = ((cand.device_id == a.device_id) & (cand.device_id != "")).astype(int)
    d["dev_unseen"] = ((cand.device_id != "") & ~cand.device_id.isin(prior_devs)).astype(int)
    d["dev_new"] = (cand.id_15 == "New").astype(int)
    d["proxy"] = cand.id_23.notna().astype(int)
    d["m_false"], d["m_true"] = cand.m_false, cand.m_true
    for c in ("C1", "C2", "C13", "C14", "D1", "dist1"):
        d[c.lower()] = cand[c].replace(-1, np.nan)
    d["rank_abs"] = d.adt_h.rank(method="first")
    d["n_cand"] = len(cand)
    d["flag_online"] = int(a.channel == "online")
    d["flag_prod_new"] = int(a.ProductCD not in prior_prods) if n else np.nan
    d["cand_prod_seen"] = cand.ProductCD.isin(prior_prods).astype(int)
    d["flag_region_freq"] = float(regf.get(str(a.region), 0)) if n else np.nan
    return d
