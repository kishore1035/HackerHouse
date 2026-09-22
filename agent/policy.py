"""Fraud Policy v1.0 as code: action routing and rules R1-R10. Deterministic, so the LLM never decides an action."""
from __future__ import annotations
from dataclasses import dataclass, field

AUTO = {"ALLOW_TRANSACTION", "MONITOR_CARD", "MONITOR_CONNECTED_CARDS", "WARN_CUSTOMER", "VERIFY_WITH_CUSTOMER", "STEP_UP_AUTH",
        "GENERATE_REPORT", "CREATE_CASE", "ESCALATE_TO_ANALYST", "CLOSE_NO_FRAUD"}


def route(action: str, exposure: float) -> str:
    if action in AUTO: return "auto"
    if action == "DECLINE_TRANSACTION": return "L1"
    if action == "BLOCK_CARD": return "L1" if exposure <= 2500 else "L2"
    return "L2"  # BLOCK_ALL_CARDS, FILE_REPORT


def act(action: str, exposure: float, reason: str) -> dict:
    return {"action": action, "route": route(action, exposure), "reason": reason}


@dataclass
class Assessment:
    p: float                       # calibrated fraud probability
    pattern: str
    exposure: float
    trigger: str                   # risk_score | customer_report | analyst_request
    n_signals: int                 # independent evidence pieces (risk score excluded)
    shared_origin: str = ""        # name of the shared element (device profile / region / email), "" if none
    connected_cards: list = field(default_factory=list)
    recurring: bool = False        # flagged amount matches the card's own recurring pattern (R7)
    testing_cleared_over_100: bool = False
    testing_detected: bool = False
    undocumented: bool = False
    conflict: bool = False         # evidence points both ways


def sar_required(a: Assessment, p: float) -> tuple[bool, str]:
    """Section 3a: fraud confirmed/strongly suspected AND (exposure > $1,000 | shared origin | coordinated/undocumented)."""
    if p < 0.70:
        return False, "fraud not confirmed or strongly suspected (probability below 0.70): case only, no report"
    why = []
    if a.exposure > 1000: why.append(f"exposure ${a.exposure:,.2f} exceeds $1,000")
    if a.shared_origin: why.append(f"activity connects to a shared origin ({a.shared_origin}) and other cards' fraud")
    if a.undocumented: why.append("pattern is coordinated or undocumented (R9)")
    if why: return True, "; ".join(why)
    return False, f"fraud strongly suspected but exposure ${a.exposure:,.2f} is under $1,000 with no shared origin or coordination: case only"


def initial_actions(a: Assessment) -> tuple[list[dict], bool, str]:
    """Recommendation before any requested evidence. Returns (actions, needs_customer_evidence, rationale)."""
    ex, p = a.exposure, a.p
    acts: list[dict] = []
    file_it, _ = sar_required(a, p)
    # R5 card testing
    if a.testing_detected:
        acts += [act("DECLINE_TRANSACTION", ex, "R5: three or more small online authorizations within an hour followed by a larger purchase"),
                 act("STEP_UP_AUTH", ex, "R5: require step-up authentication before further activity")]
        if a.testing_cleared_over_100:
            acts.append(act("BLOCK_CARD", ex, "R5: a purchase over $100 has already cleared after the testing sequence"))
        acts.append(act("CREATE_CASE", ex, "R5: card testing warrants an internal case"))
        if a.shared_origin: acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: shared origin {a.shared_origin}"))
        return acts, not a.testing_cleared_over_100 and p < 0.85, "R5 card-testing sequence"
    # R7 disputed but legitimate recurring charge
    if a.trigger == "customer_report" and a.recurring:
        return [act("CREATE_CASE", ex, "R7: customer disputes a charge matching their own recurring pattern; case opened for the dispute"),
                act("VERIFY_WITH_CUSTOMER", ex, "R7: ask the cardholder to recognise the recurring merchant; do not block"),
                act("WARN_CUSTOMER", ex, "R7: send a recurring-charge reminder")], True, "R7 recurring dispute"
    # R9 undocumented coordinated pattern
    if a.undocumented and p >= 0.70:
        acts = [act("CREATE_CASE", ex, "R9: undocumented coordinated or repeated abuse")]
        if file_it: acts.append(act("FILE_REPORT", ex, "R9: coordinated/undocumented pattern requires a regulatory report"))
        acts.append(act("ESCALATE_TO_ANALYST", ex, "R9: hand the undocumented pattern to a human analyst"))
        acts.append(act("BLOCK_CARD", ex, "R2/R9: block and reissue the compromised card"))
        if a.connected_cards: acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: monitor every card sharing {a.shared_origin or 'the origin'}"))
        return acts, False, "R9 undocumented pattern"
    # customer report = the customer denies the transaction: R2
    if a.trigger == "customer_report" and p >= 0.5:
        acts = [act("BLOCK_CARD", ex, "R2: customer denies the transaction and the graph evidence supports fraud"),
                act("CREATE_CASE", ex, "R2: customer dispute opens a case")]
        if file_it: acts.append(act("FILE_REPORT", ex, "R2: " + sar_required(a, p)[1]))
        if a.shared_origin and a.connected_cards: acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: shared origin {a.shared_origin}"))
        return acts, False, "R2 customer denial"
    # confident fraud with >=2 independent signals: R1 does not apply
    if p >= 0.85 and a.n_signals >= 2:
        acts = [act("BLOCK_CARD", ex, f"Probability {p:.2f} with {a.n_signals} independent signals; R1 verification not required above 0.70"),
                act("CREATE_CASE", ex, "Probability >= 0.30")]
        if file_it: acts.append(act("FILE_REPORT", ex, "3a: " + sar_required(a, p)[1]))
        if a.shared_origin and a.connected_cards: acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: shared origin {a.shared_origin}"))
        return acts, False, "confident fraud"
    # confident legitimate
    if p <= 0.15 and a.n_signals == 0:
        return [act("CLOSE_NO_FRAUD", ex, f"Probability {p:.2f}; activity fits the cardholder's history"),
                act("ALLOW_TRANSACTION", ex, "Let the flagged transaction stand")], False, "confident legitimate"
    # uncertain: R1 verify first
    acts = [act("VERIFY_WITH_CUSTOMER", ex, f"R1: probability {p:.2f} with {a.n_signals} independent signal(s); verify before any block")]
    if p >= 0.70 and a.n_signals >= 1 and a.trigger != "customer_report":
        acts.insert(0, act("STEP_UP_AUTH", ex, "R1: step-up authentication while awaiting the cardholder"))
    if p >= 0.30: acts.append(act("CREATE_CASE", ex, "Probability >= 0.30 and evidence is requested (3a)"))
    if a.conflict or (0.30 <= p < 0.70 and ex > 500):
        acts.append(act("ESCALATE_TO_ANALYST", ex, "R8: uncertain verdict with exposure above $500 or conflicting evidence"))
    if a.shared_origin and a.connected_cards:
        acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: shared origin {a.shared_origin}"))
    return acts, True, "uncertain: request evidence"


def final_actions(a: Assessment, response: str, p_after: float) -> list[dict]:
    """Recommendation after the (simulated) reply. response: denies | confirms | no_reply."""
    ex = a.exposure
    if response == "confirms":
        return [act("CLOSE_NO_FRAUD", ex, "R3: customer confirms the transaction"), act("ALLOW_TRANSACTION", ex, "R3: let the transaction stand")]
    if response == "denies":
        acts = [act("BLOCK_CARD", ex, "R2: customer denies the transaction"), act("CREATE_CASE", ex, "R2: customer dispute opens a case")]
        b = Assessment(**{**a.__dict__, "p": p_after})
        file_it, why = sar_required(b, p_after)
        if a.exposure > 1000 or a.shared_origin:
            acts.append(act("FILE_REPORT", ex, "R2: " + (why if file_it else f"exposure ${ex:,.2f}" + (f" and shared origin {a.shared_origin}" if a.shared_origin else ""))))
        if a.shared_origin and a.connected_cards:
            acts.append(act("MONITOR_CONNECTED_CARDS", ex, f"R6: monitor cards sharing {a.shared_origin}"))
        return acts
    acts = [act("MONITOR_CARD", ex, "R4: no reply within 24 hours; raise monitoring for 72 hours"),
            act("DECLINE_TRANSACTION", ex, "R4: decline pending authorizations"),
            act("CREATE_CASE", ex, "Evidence requested and unanswered")]
    if ex > 500 or a.conflict: acts.append(act("ESCALATE_TO_ANALYST", ex, "R4/R8: no reply and exposure above $500, or conflicting evidence"))
    return acts
