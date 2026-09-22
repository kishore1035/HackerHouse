"""Investigation features for one flagged transaction on one card.

Works against any client exposing the DataAccess interface (agent/data_access.py):
the TigerGraph client at run time, the in-memory client for offline training.
"""
from __future__ import annotations
import numpy as np, pandas as pd

WIN = pd.Timedelta(hours=48)


def _mode(s):
    s = s.dropna()
    return s.mode().iloc[0] if len(s) else None


def build(client, txn_id: int, card_id: str, as_of: pd.Timestamp | None = None) -> tuple[dict, dict]:
    """Return (features, context). `context` holds the human-readable evidence handles the agent cites."""
    card = client.card_txns(card_id)
    flagged = card[card.TransactionID == txn_id].iloc[0]
    T = flagged.ts
    cutoff = as_of or (T + WIN)
    card = card[card.ts <= cutoff]
    prior = card[card.ts < T]
    win = card[(card.ts >= T - WIN) & (card.ts <= T + WIN) & (card.TransactionID != txn_id)]
    around = card[(card.ts >= T - WIN) & (card.ts <= T + WIN)]  # incl. flagged
    online = around[around.channel == "online"]
    f: dict = {}
    ctx: dict = {"flagged": flagged, "prior_n": len(prior), "window_txns": win.TransactionID.tolist()}

    # --- baseline behaviour (prior history)
    f["risk"] = flagged.risk_score
    f["amt"] = flagged.TransactionAmt
    f["log_amt"] = np.log1p(flagged.TransactionAmt)
    f["online"] = int(flagged.channel == "online")
    for p in "CHRSW":
        f[f"prod_{p}"] = int(flagged.ProductCD == p)
    f["n_prior"] = len(prior)
    pm, ps = prior.TransactionAmt.mean(), prior.TransactionAmt.std()
    f["prior_mean"] = pm
    f["amt_z"] = (flagged.TransactionAmt - pm) / (ps if ps and ps > 0 else 1) if len(prior) > 2 else np.nan
    f["amt_pct"] = (prior.TransactionAmt < flagged.TransactionAmt).mean() if len(prior) else np.nan
    f["prior_online_share"] = (prior.channel == "online").mean() if len(prior) else np.nan
    f["prod_seen"] = int(flagged.ProductCD in set(prior.ProductCD)) if len(prior) else np.nan
    f["prior_mean_risk"] = prior.risk_score.mean() if len(prior) else np.nan
    f["hour"] = T.hour
    f["m_false"], f["m_true"] = flagged.m_false, flagged.m_true
    for c in ("c1", "c2", "c13", "c14", "D1", "dist1"):
        col = {"c1": "C1", "c2": "C2", "c13": "C13", "c14": "C14"}.get(c, c)
        v = flagged[col]
        f[c] = np.nan if v == -1 else v

    # --- region / trip logic
    region = flagged.region if isinstance(flagged.region, str) or not pd.isna(flagged.region) else None
    region = None if region in (None, "", "nan") else str(region)
    prior_regions = set(prior.region.dropna().astype(str))
    home = _mode(prior.region.astype(str).where(prior.region.notna()))
    f["region_known"] = int(region is not None)
    f["region_new"] = int(region is not None and region not in prior_regions) if len(prior) else np.nan
    f["region_prior_n"] = int((prior.region.astype(str) == region).sum()) if region else 0
    f["region_freq"] = f["region_prior_n"] / len(prior) if len(prior) and region else np.nan
    f["n_regions_prior"] = len(prior_regions)
    win_ip = win[(win.channel == "in_person") & win.region.notna()]
    f["n_regions_win"] = win_ip.region.astype(str).nunique()
    f["win_ip_nonhome_share"] = float((win_ip.region.astype(str) != home).mean()) if len(win_ip) and home else np.nan
    f["flag_is_home"] = int(region is not None and region == home)
    f["win_dist1_mean"] = win.dist1.replace(-1, np.nan).mean() if len(win) else np.nan
    same_region_win = win[win.region.astype(str) == region] if region else win.iloc[0:0]
    f["win_same_region_n"] = len(same_region_win)
    wide = card[(card.ts >= T - pd.Timedelta(days=7)) & (card.ts <= T + pd.Timedelta(days=7))]
    reg_days = wide[wide.region.astype(str) == region].ts.dt.date.nunique() if region else 0
    f["region_days_7d"] = reg_days
    home_win = win[(win.region.astype(str) == home) & (win.channel == "in_person")] if home else win.iloc[0:0]
    f["home_continues"] = len(home_win)
    f["in_person_new_region_win"] = int(((win.channel == "in_person") & ~win.region.astype(str).isin(prior_regions) & win.region.notna()).sum())

    # --- tight episode window (+-6h): fraud episodes are bursts, heavy cards drown them in the 48h window
    w6 = around[(around.ts >= T - pd.Timedelta(hours=6)) & (around.ts <= T + pd.Timedelta(hours=6))]
    f["e6_n"] = len(w6)
    f["e6_online"] = int((w6.channel == "online").sum())
    f["e6_inperson"] = int((w6.channel == "in_person").sum())
    f["e6_nonhome_ip"] = int(((w6.channel == "in_person") & (w6.region.astype(str) != home)).sum()) if home else 0
    f["e6_regions"] = w6[w6.channel == "in_person"].region.astype(str).nunique()
    f["e6_devices"] = w6.device_id.replace("", np.nan).nunique()
    f["e6_amt_sum"] = w6.TransactionAmt.sum()
    f["e6_new_dev"] = int((w6.id_15 == "New").sum())
    f["e6_mfalse"] = w6.m_false.mean() if len(w6) else np.nan
    f["e6_mixed"] = int(w6.channel.nunique() > 1)
    f["e6_prod_new"] = int((~w6.ProductCD.isin(set(prior.ProductCD))).sum()) if len(prior) else np.nan

    # --- burst / window behaviour
    f["win_n"] = len(win)
    f["win_online_n"] = int((win.channel == "online").sum())
    f["win_inperson_n"] = int((win.channel == "in_person").sum())
    f["win_amt_sum"] = win.TransactionAmt.sum()
    f["win_risk_max"] = win.risk_score.max() if len(win) else np.nan
    f["win_risk_mean"] = win.risk_score.mean() if len(win) else np.nan
    f["mixed_channel"] = int(around.channel.nunique() > 1)
    hr = around[(around.ts >= T - pd.Timedelta(hours=1)) & (around.ts <= T + pd.Timedelta(hours=1))]
    f["hr_n"] = len(hr)
    f["hr_small_online"] = int(((hr.channel == "online") & (hr.TransactionAmt < 5)).sum())
    f["small_online_48h"] = int(((online.TransactionAmt < 5)).sum())
    f["struct_500"] = int(((around.channel == "online") & (around.TransactionAmt >= 400) & (around.TransactionAmt < 500)).sum())
    f["struct_500_1h"] = int(((hr.channel == "online") & (hr.TransactionAmt >= 400) & (hr.TransactionAmt < 500)).sum())
    f["max_after_small"] = int(len(online) >= 4 and (online.TransactionAmt < 5).sum() >= 3 and online.TransactionAmt.max() > 20)
    f["win_products_new"] = int((~win.ProductCD.isin(set(prior.ProductCD))).sum()) if len(prior) else np.nan

    # --- device & shared origin (graph hops)
    dev = flagged.device_id if isinstance(flagged.device_id, str) and flagged.device_id else None
    prior_devs = set(prior.device_id.dropna()) - {""}
    f["has_device"] = int(dev is not None)
    f["dev_new_flag"] = int(flagged.id_15 == "New") if isinstance(flagged.id_15, str) else 0
    f["dev_found_flag"] = int(flagged.id_15 == "Found") if isinstance(flagged.id_15, str) else 0
    f["dev_unseen_on_card"] = int(dev is not None and dev not in prior_devs)
    f["proxy_anon"] = int(str(flagged.id_23) == "IP_PROXY:ANONYMOUS")
    f["proxy_any"] = int(isinstance(flagged.id_23, str))
    win_devs = set(around.device_id.dropna()) - {""}
    f["win_n_devices"] = len(win_devs)
    dc, dcases = 0, []
    ctx["device"] = dev
    if dev:
        dtx = client.device_txns(dev)
        dtx = dtx[dtx.ts <= cutoff]
        near = dtx[(dtx.ts >= T - pd.Timedelta(days=30)) & (dtx.ts <= T + pd.Timedelta(days=30))]
        dc = near.card_id.nunique()
        ctx["device_cards"] = sorted(set(near.card_id) - {card_id})
        dcases = client.device_closed_cases(dev, before=T)
        f["dev_total_txn"] = len(dtx)
    else:
        f["dev_total_txn"] = 0
    f["dev_cards_30d"] = dc
    f["dev_fraud_cases"] = sum(1 for c in dcases if c["outcome"] == "confirmed_fraud")
    f["dev_cleared_cases"] = sum(1 for c in dcases if c["outcome"] == "cleared")
    ctx["device_cases"] = dcases

    # --- card history in the case memory
    cc = client.card_closed_cases(card_id, before=T)
    f["card_prior_fraud_cases"] = sum(1 for c in cc if c["outcome"] == "confirmed_fraud")
    f["card_prior_cleared_cases"] = sum(1 for c in cc if c["outcome"] == "cleared")
    ctx["card_cases"] = cc
    return f, ctx
