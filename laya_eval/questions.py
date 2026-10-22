"""Laya question definitions for each QA criterion.

Every criterion is asked four ways in ONE predict() call (Laya answers all questions in one pass):
  w1      noul, criteria wording 1, default option labels
  w2      noul, criteria wording 2 (different phrasing of the same thing)
  w1_ab   noul, wording 1, model-facing labels overridden to neutral "A"/"B" (README: label dominance, #156)
  choice  two-option choice with neutral keys A/B (README-suggested workaround), A = the "true" side

`yes` says which pipeline verdict a HIGH P(true) means:
  yes == "PASS"  evidence criteria  (Empathy, Probing, Confirmed resolved)
  yes == "FAIL"  violation criteria (Active listening, Ownership, Rapport, Escalation, Hostility)
"""

VARIANTS = ["w1", "w2", "w1_ab", "choice"]

# criterion -> (yes, (w1_instr, w1_true, w1_false), (w2_instr, w2_true, w2_false))
DEFS = {
    "empathy": (
        "PASS",
        ("Does the agent acknowledge the customer's frustration with empathy?",
         "the agent acknowledges the customer's frustration or feelings and responds with care",
         "the agent ignores, brushes off or is rude about the customer's frustration"),
        ("Was the agent empathetic to the upset customer?",
         "empathetic: the agent recognises how the customer feels and responds to it",
         "not empathetic: the agent is cold, dismissive or goes straight to business"),
    ),
    "active_listening": (
        "FAIL",
        ("Does the second agent question ask for the same information as the first?",
         "the agent repeats the same question and asks again for information already requested",
         "the second question asks for something different from the first"),
        ("Did the agent unnecessarily repeat a question?",
         "yes, it is the same question asked twice",
         "no, the two questions are about different things"),
    ),
    "ownership": (
        "FAIL",
        ("Does the agent deflect responsibility, blame another team, or refuse to help?",
         "the agent deflects, blames another team or department, refuses to help, or tells the customer to contact someone else",
         "the agent takes ownership and keeps working on the customer's problem"),
        ("Is the agent avoiding responsibility for the customer's problem?",
         "the agent avoids responsibility by passing the customer elsewhere or saying nothing can be done",
         "the agent owns the problem and commits to following it through"),
    ),
    "rapport": (
        "FAIL",
        ("Is the agent rude, condescending, dismissive, sarcastic or unprofessional?",
         "the agent is rude, condescending, dismissive, sarcastic or unprofessional toward the customer",
         "the agent is polite, respectful and professional"),
        ("Does the agent talk down to the customer or show a poor attitude?",
         "the agent talks down to the customer or has a poor, impatient attitude",
         "the agent is courteous and keeps a professional tone"),
    ),
    "probing": (
        "PASS",
        ("Did the agent ask at least one genuine diagnostic question about the customer's problem?",
         "the agent asked at least one question that investigates the cause or specifics of the problem, such as when it started, which device, what error or lights, or what was already tried",
         "the agent only asked greetings, identity verification, confirmations, upsell, scheduling or closing questions"),
        ("Did the agent investigate the cause of the problem with a real troubleshooting question?",
         "yes, the agent asked a troubleshooting question about the cause or details of the problem",
         "no, none of the agent's questions investigate the problem itself"),
    ),
    "resolved": (
        "PASS",
        ("Did the agent explicitly confirm that the customer's issue was resolved?",
         "the agent explicitly confirms the issue is resolved or fixed, usually after checking with the customer",
         "the agent never confirms resolution: the call just ends, the agent assumes it is fixed, the customer says it still fails, or it is handed off"),
        ("Was the problem confirmed as fixed by the agent before the call ended?",
         "yes, the agent confirms the problem is fixed or resolved",
         "no, the agent does not confirm the problem is fixed"),
    ),
    "escalation": (
        "FAIL",
        ("Did the customer ask for a supervisor, manager or escalation that the agent refused, ignored or discouraged?",
         "the customer asked for a supervisor, manager or escalation and the agent refused, ignored, discouraged or faked it",
         "the customer did not ask to escalate, or the agent handled the request properly"),
        ("Did the agent block the customer from reaching a supervisor or escalating?",
         "yes, the agent blocked or brushed off a request to speak to a supervisor or escalate",
         "no, there was no such request or the agent handled it properly"),
    ),
    "hostility": (
        "FAIL",
        ("Is the agent hostile, abusive, insulting, threatening, mocking, or hangs up on the customer?",
         "the agent insults, mocks, threatens, is abusive toward the customer, or abruptly hangs up",
         "the agent stays professional and respectful, even if the customer is angry"),
        ("Does the agent treat the customer with hostility?",
         "yes, the agent is hostile, sarcastic in a nasty way, insulting or threatening",
         "no, the agent stays calm and professional"),
    ),
}


def yes_means(criterion):
    return DEFS[criterion][0]


def build_questions(criterion):
    _, w1, w2 = DEFS[criterion]
    return {
        "w1": {"type": "noul", "instructions": w1[0], "criteria": {"true": w1[1], "false": w1[2]}},
        "w2": {"type": "noul", "instructions": w2[0], "criteria": {"true": w2[1], "false": w2[2]}},
        "w1_ab": {"type": "noul", "instructions": w1[0], "criteria": {"true": w1[1], "false": w1[2]},
                  "labels": {"true": "A", "false": "B"}},
        "choice": {"type": "choice", "instructions": w1[0], "criteria": {"A": "yes, " + w1[1], "B": "no, " + w1[2]}},
    }


def p_yes(answer_for_variant, variant):
    """P(true side) from a Laya answer dict."""
    if variant == "choice":
        return float(answer_for_variant["probabilities"]["A"])
    return float(answer_for_variant["noul"])


def p_pass(criterion, py):
    return py if yes_means(criterion) == "PASS" else 1.0 - py
