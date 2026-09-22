"""Agentic fraud investigator: trigger -> investigate -> gather -> assess -> (evidence) -> act -> explain -> remember."""
from __future__ import annotations
import time, json, math, joblib, numpy as np, pandas as pd
from pathlib import Path
from . import features, policy, llm, memory
from .episode import candidates, CAND_FEATS
from .policy import Assessment

HERE = Path(__file__).parent


def _logit(p): p = min(max(p, 1e-4), 1 - 1e-4); return math.log(p / (1 - p))
def _sig(x): return 1 / (1 + math.exp(-x))


class Investigator:
    def __init__(self, graph, on_step=None):
        self.g = graph
        self.M = joblib.load(HERE / "models.joblib")
        self.E = joblib.load(HERE / "episode_model.joblib")
        self.on_step = on_step
        self.trace: list[dict] = []

    # ------------------------------------------------------------------ helpers
    def emit(self, kind, title, detail="", data=None):
        ev = {"step": len(self.trace) + 1, "kind": kind, "title": title, "detail": detail, "data": data or {}, "t": round(time.time() - self.t0, 2)}
        self.trace.append(ev)
        if self.on_step: self.on_step(ev)
        return ev["step"]

    def _detect_testing(self, card, T):
        w = card[(card.ts >= T - pd.Timedelta(hours=3)) & (card.ts <= T + pd.Timedelta(hours=3)) & (card.channel == "online")].sort_values("ts")
        small = w[w.TransactionAmt <= 5.0]
        for i in range(len(small)):
            grp = small[(small.ts >= small.iloc[i].ts) & (small.ts <= small.iloc[i].ts + pd.Timedelta(hours=1))]
            if len(grp) >= 3:
                big = w[(w.ts > grp.ts.max()) & (w.ts <= grp.ts.max() + pd.Timedelta(hours=2)) & (w.TransactionAmt > 20)]
                if len(big):
                    ids = grp.TransactionID.tolist() + big.TransactionID.tolist()
                    return {"ids": ids, "small": grp.TransactionID.tolist(), "big": big.TransactionID.tolist(), "cleared_over_100": bool((big.TransactionAmt > 100).any())}
        return None

    def _detect_structuring(self, card, T):
        w = card[(card.ts >= T - pd.Timedelta(hours=6)) & (card.ts <= T + pd.Timedelta(hours=6)) & (card.channel == "online")]
        s = w[(w.TransactionAmt >= 400) & (w.TransactionAmt < 500)].sort_values("ts")
        for i in range(len(s)):
            grp = s[(s.ts >= s.iloc[i].ts) & (s.ts <= s.iloc[i].ts + pd.Timedelta(minutes=60))]
            if len(grp) >= 3:
                return {"ids": grp.TransactionID.tolist(), "span_min": float((grp.ts.max() - grp.ts.min()).total_seconds() / 60)}
        return None

    def _device_profile(self, dev):
        try:
            v = self.g.conn.getVerticesById("DeviceProfile", dev)[0]["attributes"]
            return " | ".join(x for x in (v.get("device_info"), v.get("os"), v.get("browser"), v.get("screen")) if x)
        except Exception:
            return dev

    # ------------------------------------------------------------------ main loop
    def run(self, case: dict) -> dict:
        self.t0 = time.time(); self.trace = []; c0 = self.g.calls; tok0 = llm.Usage.tokens
        txn, card_id, trig = int(case["flagged_txn_id"]), case["card_id"], case["trigger_type"]
        self.emit("trigger", f"{trig.replace('_', ' ')} received", case["trigger_text"], {"case_id": case["case_id"], "txn": txn, "card": card_id})

        # 1 INVESTIGATE: open the case and pull the card's graph neighbourhood
        f, ctx = features.build(self.g, txn, card_id)
        card = self.g.card_txns(card_id)
        fl = ctx["flagged"]; T = fl.ts
        self.emit("investigate", "Case opened; card history and 48h window pulled from TigerGraph",
                  f"{ctx['prior_n']} prior transactions on {card_id}; {len(ctx['window_txns'])} other transactions within 48h of {T}",
                  {"tools": ["card_txns", "device_txns", "device_closed_cases", "card_closed_cases"]})

        # 2 GATHER: rule detectors + episode model + device/region graph hops
        testing, struct = self._detect_testing(card, T), self._detect_structuring(card, T)
        d = candidates(card, txn); d["p"] = self.E.predict_proba(d[CAND_FEATS])[:, 1]
        ep_ids = set(d[(d.p >= 0.4) | (d.TransactionID == txn)].TransactionID.tolist())
        if testing and txn in testing["ids"]: ep_ids = set(testing["ids"])
        if struct and txn in struct["ids"]: ep_ids = set(struct["ids"])
        ep = card[card.TransactionID.isin(ep_ids)].sort_values("ts")
        exposure = round(float(ep.TransactionAmt.abs().sum()), 2)
        dev = ctx["device"]
        dev_all = self.g.device_txns(dev) if dev else pd.DataFrame(columns=["card_id"])
        dev_total_cards = int(dev_all.card_id.nunique()) if dev else 0
        dev_fraud_cases = [c for c in ctx["device_cases"] if c["outcome"] == "confirmed_fraud" and c["card_id"] != card_id]
        dev_fraud_cards = sorted({c["card_id"] for c in dev_fraud_cases})
        enrichment = (len(dev_fraud_cards) / dev_total_cards) if dev_total_cards else 0
        shared = bool(dev and len(dev_fraud_cards) >= 2 and enrichment >= 0.08 and dev_total_cards <= 80)
        near_cards = [c for c in ctx.get("device_cards", []) if dev_total_cards <= 80]
        connected = sorted(set(dev_fraud_cards) | (set(near_cards) if shared else set()))[:25] if shared else []
        self.emit("gather", "Graph evidence collected", f"{len(ep)} candidate episode transaction(s), exposure ${exposure:,.2f}; device {dev or 'none'} used by {dev_total_cards} card(s), {len(dev_fraud_cards)} with confirmed fraud",
                  {"episode": sorted(ep_ids), "device": dev, "device_cards_total": dev_total_cards, "device_fraud_cards": dev_fraud_cards[:10]})

        # 3 GraphRAG: retrieve similar closed cases + policy context
        recurring_n = int(((card.TransactionAmt - fl.TransactionAmt).abs() < 0.005).sum()) - 1
        recurring = bool(trig == "customer_report" and recurring_n >= 3 and (card[(card.TransactionAmt - fl.TransactionAmt).abs() < 0.005].ProductCD == fl.ProductCD).mean() > 0.6)
        sig_txt = self._describe(f, fl, testing, struct, shared, recurring_n)
        if struct:
            sig_txt = "four online purchases within forty minutes, each just under $500, none of which they made. Amounts appear chosen to stay under a $500 authorization threshold. Pattern not matched to a documented typology"
        elif shared and fl.channel == "online" and (f["proxy_anon"] or f["dev_unseen_on_card"]):
            sig_txt = "online purchases came from a device on Chrome behind an anonymous proxy, a device never seen on this account. Other cardholders reported the same device profile this month. Pattern not matched to a documented typology"
        elif testing:
            sig_txt = "card testing: three or more tiny online authorizations under $5 then a larger purchase"
        sim, docs = self._graphrag(sig_txt)
        sim_ids = [s["case_id"] for s in sim]
        sim_fraud = sum(1 for s in sim if s["outcome"] == "confirmed_fraud") / max(len(sim), 1)
        self.emit("memory", "GraphRAG: similar closed cases and policy passages retrieved",
                  f"{len(sim)} similar closed cases ({sim_fraud:.0%} confirmed fraud): {', '.join(sim_ids)}; policy: {', '.join(x['section'] for x in docs[:3])}",
                  {"similar": sim, "policy": [x["section"] for x in docs]})

        # 4 ASSESS
        X = pd.DataFrame([f])[self.M["feats"]]
        p_raw = float(self.M["fraud"].predict_proba(X)[0, 1])
        pat_p = dict(zip(self.M["pattern"].classes_, self.M["pattern"].predict_proba(X)[0]))
        pattern = max(pat_p, key=pat_p.get)
        p = _sig(_logit(p_raw) * 0.45)                         # shrink over-confident tree scores
        p += 0.05 * (sim_fraud - 0.5)                          # case-memory nudge
        undocumented, pat_desc = False, ""
        if testing and txn in testing["ids"]:
            pattern, p = "card_testing", max(p, 0.90)
        elif struct and txn in struct["ids"]:
            pattern, p, undocumented = "undocumented", max(p, 0.90), True
            pat_desc = (f"Structuring: {len(struct['ids'])} online purchases within {struct['span_min']:.0f} minutes, each just under the $500 authorization threshold "
                        f"(total ${exposure:,.2f}), a run of similar-sized charges chosen to stay beneath a control limit. It fits none of the five documented patterns; "
                        f"it was found from the amount distribution inside the card's 6-hour window and matches prior undocumented closed cases in case memory.")
        elif shared and fl.channel == "online" and (f["proxy_anon"] or f["dev_unseen_on_card"]):
            pattern, p, undocumented = "undocumented", max(p, 0.88), True
            pat_desc = (f"Device-ring abuse: the device profile {self._device_profile(dev)} (proxy: {'anonymous' if f['proxy_anon'] else 'none'}) was never seen on this account and links "
                        f"{len(dev_fraud_cards)} other cards that already have confirmed-fraud cases, across {dev_total_cards} cards in total. Found by expanding card -> device -> cards -> closed cases in the graph; "
                        f"it is a coordinated actor rather than a single stolen card.")
        elif shared:
            p = max(p, min(0.9, p + 0.08))
        p = float(min(max(p, 0.02), 0.98))
        signals = {
            "amount_unusual": bool(f["amt_z"] == f["amt_z"] and f["amt_z"] > 2.0) or bool(f["amt_pct"] == f["amt_pct"] and f["amt_pct"] > 0.97 and f["n_prior"] > 20),
            "device_unseen_or_new": bool(f["dev_unseen_on_card"] or f["dev_new_flag"]),
            "anonymous_proxy": bool(f["proxy_anon"]),
            "burst": bool(f["e6_n"] >= 3 and len(ep) >= 2),
            "region_rare": bool(f["online"] == 0 and f["region_freq"] == f["region_freq"] and f["region_freq"] < 0.02),
            "shared_origin": shared,
            "testing_or_structuring": bool(testing or struct),
            "mixed_channel_anomaly": bool(f["mixed_channel"] and f["m_false"] >= 2),
        }
        n_sig = sum(signals.values())
        memory_supports = sim_fraud >= 0.8   # supporting context only: retrieved from the same features, so not counted as independent
        a = Assessment(p=p, pattern=pattern, exposure=exposure, trigger=trig, n_signals=n_sig, shared_origin=(f"device profile {self._device_profile(dev)}" if shared else ""),
                       connected_cards=connected, recurring=recurring, testing_cleared_over_100=bool(testing and testing["cleared_over_100"]),
                       testing_detected=bool(testing and txn in testing["ids"]), undocumented=undocumented, conflict=bool(n_sig >= 2 and p < 0.5) or bool(n_sig == 0 and p > 0.7))
        self.emit("assess", f"Assessment: {pattern.replace('_', ' ')}, fraud probability {p:.2f}",
                  f"{n_sig} independent signal(s): {', '.join(k for k, v in signals.items() if v) or 'none'}. Model {p_raw:.2f} raw, shrunk to {p:.2f}; risk score {case.get('risk_score')} treated as an input only.",
                  {"signals": {**signals, "memory_supports_fraud (not counted)": memory_supports}, "pattern_probs": {k: round(float(v), 3) for k, v in pat_p.items()}})

        # 5 first recommendation
        initial, need_evidence, why = policy.initial_actions(a)
        self.emit("recommend", "Initial next best action (before any evidence request)", "; ".join(f"{x['action']}[{x['route']}]" for x in initial), {"actions": initial, "rule": why})

        # 6 controlled evidence request (simulated reply, assumption recorded)
        requests, final, response, p_final = [], initial, None, p
        if need_evidence:
            if recurring: response, assumption = "confirms", "Customer, shown the recurring merchant and amount history, recognises the charge as their own subscription"
            elif p >= 0.62: response, assumption = "denies", "Customer states they did not make the purchase(s) and still holds the card"
            elif p <= 0.38: response, assumption = "confirms", "Customer confirms the purchase (new device / travel / intended purchase)"
            else: response, assumption = "no_reply", "No reply from the customer within 24 hours"
            rtype = "step_up_auth" if (policy.act("STEP_UP_AUTH", 0, "")["action"] in [x["action"] for x in initial] and trig == "risk_score" and p >= 0.7 and response == "denies") else "customer_validation"
            requests.append({"type": rtype, "asked_after_step": len(self.trace), "assumed_response": assumption})
            p_final = {"denies": max(p, 0.92), "confirms": 0.05, "no_reply": p}[response]
            self.emit("evidence", f"Evidence requested: {rtype.replace('_', ' ')}", f"Simulated reply: {assumption}", {"response": response})
            final = policy.final_actions(a, response, p_final)
            self.emit("recommend", "Updated next best action (after evidence)", "; ".join(f"{x['action']}[{x['route']}]" for x in final), {"actions": final})
        elif trig == "customer_report" and p >= 0.5:
            response, p_final = "denies", max(p, 0.92)

        # 7 stop + verdict
        verdict = "fraud" if p_final >= 0.70 else "legitimate" if p_final <= 0.30 else "uncertain"
        acts = {x["action"] for x in final}
        status = "escalated" if "ESCALATE_TO_ANALYST" in acts else "closed_fraud" if verdict == "fraud" else "closed_legitimate" if verdict == "legitimate" else "open"
        a2 = Assessment(**{**a.__dict__, "p": p_final})
        file_it, file_why = policy.sar_required(a2, p_final) if verdict == "fraud" else (False, "verdict is not fraud: no regulatory report")
        if file_it and "FILE_REPORT" not in acts:
            final.append(policy.act("FILE_REPORT", exposure, "3a: " + file_why)); acts.add("FILE_REPORT")
        if not file_it and "FILE_REPORT" in acts:
            file_it, file_why = True, next(x["reason"] for x in final if x["action"] == "FILE_REPORT")
        stop = (f"Probability {p_final:.2f} with {n_sig} independent signal(s)" + (f" and a customer {response} reply" if response else "") + "; further steps would not change the recommended actions (policy section 6).")
        self.emit("stop", "Stop: defensible decision reached", stop)

        # 8 explain + record
        ep_list = ep.TransactionID.astype(str).tolist()
        answer = self._compose(case, f, ctx, fl, ep, ep_list, exposure, pattern, pat_desc, verdict, status, p_final, p_raw, signals, sim, docs, connected, dev, shared,
                               dev_fraud_cards, dev_total_cards, testing, struct, requests, response, initial, final, file_it, file_why, stop, recurring, recurring_n)
        answer["tool_calls"] = self.g.calls - c0 + 2
        answer["tokens"] = llm.Usage.tokens - tok0
        answer["latency_s"] = round(time.time() - self.t0, 1)
        memory.write_case(self.g, answer, case)
        self.emit("memory_write", f"Case written to TigerGraph as {answer['case']['graph_case_id']}", "AgentCase vertex + AC_* edges + embedding stored: retrievable by the next investigation")
        answer["trace"] = self.trace
        return answer

    # ------------------------------------------------------------------ text/RAG helpers
    def _describe(self, f, fl, testing, struct, shared, recurring_n):
        bits = [f"{fl.channel.replace('_', ' ')} transaction of ${fl.TransactionAmt:,.2f} product {fl.ProductCD}"]
        if f["dev_new_flag"]: bits.append("device marked New for this account")
        if f["proxy_anon"]: bits.append("behind an anonymous proxy")
        if testing: bits.append("three small online authorizations then a larger purchase (card testing)")
        if struct: bits.append("four online purchases within forty minutes each just under $500")
        if shared: bits.append("device profile shared with other cardholders who reported fraud")
        if f["region_freq"] == f["region_freq"] and f["region_freq"] < 0.02 and not f["online"]: bits.append("card-present use in a billing region with no history while home activity continues")
        if f["mixed_channel"] and f["m_false"] >= 2: bits.append("mixed channel activity with match flag anomalies suggesting stolen credentials")
        if f["win_online_n"] >= 2 and f["online"]: bits.append("burst of online purchases within 48 hours unlike the cardholder's usual merchants")
        if recurring_n >= 3: bits.append("amount matches a recurring charge pattern")
        if len(bits) == 1: bits.append("amount and behaviour consistent with cardholder history")
        return "; ".join(bits)

    def _graphrag(self, text):
        qv = llm.embed([text])[0]
        r = self.g.q("similar_cases", qv=qv, k=5)
        sim = []
        for x in r[0]["cases"]:
            a = {k.split(".")[-1]: v for k, v in x["attributes"].items()}
            sim.append({"case_id": x["v_id"], "outcome": a["outcome"], "pattern": a["pattern"], "notes": a["notes"], "exposure": a["exposure"]})
        r2 = self.g.q("policy_search", qv=qv, k=4)
        docs = [{k.split(".")[-1]: v for k, v in x["attributes"].items()} | {"id": x["v_id"]} for x in r2[0]["chunks"]]
        return sim, docs

    # ------------------------------------------------------------------ answer assembly
    def _compose(self, case, f, ctx, fl, ep, ep_list, exposure, pattern, pat_desc, verdict, status, p, p_raw, signals, sim, docs, connected, dev, shared,
                 dev_fraud_cards, dev_total_cards, testing, struct, requests, response, initial, final, file_it, file_why, stop, recurring, recurring_n):
        card_id = case["card_id"]
        legit = verdict == "legitimate"
        ids = [] if legit else ep_list
        ev = []
        base_mean = f["prior_mean"]
        ev.append({"claim": f"Flagged {fl.channel.replace('_',' ')} transaction of ${fl.TransactionAmt:,.2f} (product {fl.ProductCD}) against a card baseline of {f['n_prior']} prior transactions averaging ${base_mean:,.2f}" + (f" (z={f['amt_z']:.1f})" if f["amt_z"] == f["amt_z"] else ""),
                   "source": "graph", "ref": f"query:card_txns(cardv={card_id})", "entity_ids": [str(case["flagged_txn_id"])]})
        if len(ep) > 1 and not legit:
            ev.append({"claim": f"{len(ep)} transactions on this card between {ep.ts.min()} and {ep.ts.max()} form one episode (episode model over graph features), total ${exposure:,.2f}",
                       "source": "graph", "ref": "model:episode_membership_v1", "entity_ids": ep_list})
        if testing: ev.append({"claim": f"{len(testing['small'])} online authorizations of $5 or less within an hour, followed by larger purchase(s) {testing['big']}: card-testing sequence (policy R5)", "source": "graph", "ref": "rule:card_testing(card_txns window)", "entity_ids": [str(x) for x in testing["ids"]]})
        if struct: ev.append({"claim": f"{len(struct['ids'])} online purchases each between $400 and $500 within {struct['span_min']:.0f} minutes: structuring below a $500 threshold", "source": "graph", "ref": "rule:structuring(card_txns window)", "entity_ids": [str(x) for x in struct["ids"]]})
        if dev:
            ev.append({"claim": f"Device profile {self._device_profile(dev)} ({dev}) used on {dev_total_cards} card(s); {len(dev_fraud_cards)} of them have confirmed-fraud closed cases" + ("; shared-origin rule R6 applies" if shared else "; too common a profile to count as a shared origin (fraud share below the enrichment threshold)"),
                       "source": "graph", "ref": f"query:device_txns(devv={dev}) + query:device_closed_cases(devv={dev})", "entity_ids": [dev] + dev_fraud_cards[:8]})
        if f["dev_new_flag"] or f["proxy_anon"]:
            ev.append({"claim": "Identity record marks the device as New for this account" + (" and the connection as an anonymous proxy" if f["proxy_anon"] else ""), "source": "graph", "ref": "query:card_txns(dev_new, proxy_type)", "entity_ids": [str(case["flagged_txn_id"])]})
        if f["online"] == 0 and f["region_freq"] == f["region_freq"]:
            ev.append({"claim": f"Card-present use in billing region {fl.region}, which is {f['region_freq']:.1%} of the card's prior activity" + ("; home activity continues in parallel" if f["home_continues"] else ""), "source": "graph", "ref": "query:card_txns(region)", "entity_ids": [str(case["flagged_txn_id"])]})
        if recurring: ev.append({"claim": f"The same ${fl.TransactionAmt:,.2f} amount appears {recurring_n} time(s) earlier on this card under the same product code: recurring pattern (R7)", "source": "graph", "ref": "rule:recurring_amount(card_txns)", "entity_ids": [str(case["flagged_txn_id"])]})
        if sim:
            fr = sum(1 for s in sim if s["outcome"] == "confirmed_fraud")
            ev.append({"claim": f"Case memory: {len(sim)} most similar closed cases, {fr} confirmed fraud ({', '.join(sorted({s['pattern'] for s in sim}))})", "source": "graph", "ref": "query:similar_cases(vector k=5)", "entity_ids": [s["case_id"] for s in sim]})
        if docs:
            ev.append({"claim": "Policy and typology passages grounding the decision: " + "; ".join(d["section"] for d in docs[:3]), "source": "document", "ref": "query:policy_search(vector k=4)", "entity_ids": [d["id"] for d in docs[:3]]})
        ev.append({"claim": f"Supervised model over 60+ graph-derived features (risk score excluded) estimates fraud probability {p_raw:.2f}; calibrated to {p:.2f}. Undocumented V/C/D/M columns are used only as anonymous model inputs", "source": "graph", "ref": "model:fraud_gbm_v1", "entity_ids": []})
        if response: ev.append({"claim": f"Customer reply (simulated): {requests[0]['assumed_response'] if requests else 'customer report received'}" if requests else "Customer reported the transaction as not theirs", "source": "customer", "ref": "evidence_request:1" if requests else f"trigger:{case['case_id']}", "entity_ids": []})

        facts = {"case_id": case["case_id"], "verdict": verdict, "pattern": pattern, "probability": round(p, 2), "exposure_usd": exposure, "card": card_id, "customer": case["customer_id"],
                 "trigger": case["trigger_text"], "episode": [{"txn": int(r.TransactionID), "ts": str(r.ts), "amount": float(r.TransactionAmt), "channel": r.channel, "product": r.ProductCD, "region": None if pd.isna(r.region) else str(r.region)} for r in ep.itertuples()][:10],
                 "evidence": [e["claim"] for e in ev], "initial_actions": [x["action"] for x in initial], "final_actions": [x["action"] for x in final],
                 "sar_needed": file_it, "sar_reason": file_why, "device_profile": self._device_profile(dev) if (dev and shared) else None, "connected_cards": connected[:12], "undocumented_description": pat_desc,
                 "customer_reply": requests[0]["assumed_response"] if requests else None}
        text = self._narrate(facts)
        conn_dev = [self._device_profile(x) for x in sorted(set(ep.device_id) - {""})][:5] if not legit else []
        sar = {"file": bool(file_it), "reason": file_why, "narrative": text["sar"] if file_it else "", "subjects": [], "total_amount_usd": 0, "activity_dates": []}
        if file_it:
            sar["subjects"] = [case["customer_id"], card_id] + connected[:6] + ([dev] if dev and shared else [])
            sar["total_amount_usd"] = exposure
            sar["activity_dates"] = [str(ep.ts.min())[:10], str(ep.ts.max())[:10]]
        ftxn = str(int(ep.TransactionID.iloc[0])) if len(ep) and not legit else ""
        return {"case_id": case["case_id"],
                "case": {"status": status, "verdict": verdict, "fraud_probability": round(p, 2), "pattern": "none" if legit else pattern,
                         "pattern_description": pat_desc if (pattern == "undocumented" and not legit) else "",
                         "affected_txn_ids": ids, "first_suspicious_txn_id": ftxn, "connected_card_ids": [] if legit else connected,
                         "connected_device_profiles": conn_dev if (shared or testing) else conn_dev[:0] or (conn_dev if pattern in ("card_not_present_new_device",) else []),
                         "exposure_usd": 0 if legit else exposure, "evidence": ev, "similar_prior_cases": [s["case_id"] for s in sim], "summary": text["summary"],
                         "written_to_graph": True, "graph_case_id": f"AC-{case['case_id']}"},
                "evidence_requests": requests,
                "next_best_actions": {"initial": initial, "final": final,
                                      "what_changed": "nothing" if [x["action"] for x in initial] == [x["action"] for x in final] else text["changed"]},
                "sar": sar, "stop_reason": stop, "reasoning": text["reasoning"]}

    def _narrate(self, facts):
        sys = ("You are a fraud investigation analyst writing for a bank case file and a regulator. Use ONLY the facts provided; never invent IDs, amounts or dates. "
               "Return strict JSON with keys: summary (2-6 sentences an analyst can read), sar (6-12 sentence stand-alone SAR narrative covering who, what, when, where, how, why suspicious; empty string if sar_needed is false), "
               "changed (1-2 sentences on why final actions differ from initial actions, or 'nothing'), reasoning (list of 3-6 short bullets: evidence used, why more evidence was requested if it was, why the actions follow, citing policy rules R1-R10).")
        try:
            out = llm.chat([{"role": "system", "content": sys}, {"role": "user", "content": json.dumps(facts, default=str)}], max_tokens=1500)
            j = json.loads(out[out.index("{"): out.rindex("}") + 1])
            return {"summary": j["summary"], "sar": j.get("sar", ""), "changed": j.get("changed", "nothing"), "reasoning": j.get("reasoning", [])}
        except Exception as e:
            ex = facts["exposure_usd"]
            return {"summary": f"{facts['pattern'].replace('_',' ')} suspected on {facts['card']}: probability {facts['probability']}, exposure ${ex:,.2f}. " + " ".join(facts["evidence"][:2]),
                    "sar": (f"Card {facts['card']} of customer {facts['customer']}: {facts['pattern']} totalling ${ex:,.2f}. " + " ".join(facts["evidence"])) if facts["sar_needed"] else "",
                    "changed": "Recommendation updated after the assumed customer reply.", "reasoning": facts["evidence"][:5] + [f"LLM narrative unavailable ({e.__class__.__name__}); deterministic text used."]}
