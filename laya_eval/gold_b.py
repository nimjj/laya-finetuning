"""Synthetic gold set, part B: Ownership and Rapport.

Labels are BY CONSTRUCTION, NOT human-verified. Item = (label, hard, payload).

Payload is a list of AGENT lines. Every line must contain at least one trigger phrase from
rule_engine.extract_ownership_snippets / extract_rapport_snippets, because in the real pipeline only
lines that hit the phrase list are ever sent to the LLM. The builder checks this.

OWNERSHIP: FAIL = agent blames another team, deflects responsibility, refuses to help, or tells the
customer to contact someone else. PASS = trigger phrase used benignly, agent still owns the problem.
RAPPORT: FAIL = rude, condescending, dismissive, sarcastic or unprofessional. PASS = trigger phrase
used benignly, tone professional.
"""

OWNERSHIP = [
    # ---------------- FAIL, clear ----------------
    ("FAIL", False, ["That's not my department, you'd have to call billing."]),
    ("FAIL", False, ["I don't handle outages, that's the network team's job."]),
    ("FAIL", False, ["There's nothing I can do about that, I'm afraid."]),
    ("FAIL", False, ["You'll have to ask the provisioning team about the install date."]),
    ("FAIL", False, ["That's not my problem, the modem was sold by a reseller."]),
    ("FAIL", False, ["Call back tomorrow and speak to someone else."]),
    ("FAIL", False, ["It's the billing team's issue, not something I handle."]),
    ("FAIL", False, ["Contact them directly, I can't do anything for you."]),
    ("FAIL", False, ["That's their responsibility, I'm done here."]),
    ("FAIL", False, ["I hope you get it sorted out with another department."]),
    ("FAIL", False, ["Wrong department, you'll need to call the sales line."]),
    ("FAIL", False, ["That's not our problem, it's your landlord's wiring."]),
    ("FAIL", False, ["I can't help with that one. It's a different department, you'd have to call them."]),
    # ---------------- FAIL, hard (polite deflection) ----------------
    ("FAIL", True, ["I'd love to help, but the network team owns outages so you would have to call them."]),
    ("FAIL", True, ["Sorry, that's their department to fix. Perhaps call back after the weekend."]),
    ("FAIL", True, ["I've noted it, but honestly there's nothing I can do to speed that up."]),
    ("FAIL", True, ["Unfortunately billing questions go to another team, so you'll have to ask them."]),
    ("FAIL", True, ["I don't handle hardware replacements, you can try the store."]),
    ("FAIL", True, ["That one is for the provisioning team, so please contact them on Monday."]),
    ("FAIL", True, ["Let me be honest, that's not my job, but good luck with it."]),
    # ---------------- PASS, clear (benign use of a trigger phrase) ----------------
    ("PASS", False, ["I'll call back in ten minutes once the technician confirms the outage."]),
    ("PASS", False, ["I'm sending this to the network team right now and I'll follow up with you myself."]),
    ("PASS", False, ["I'll contact them for you and stay on the line while we wait."]),
    ("PASS", False, ["The billing team will review the refund today, and I'll check on it personally tomorrow morning."]),
    ("PASS", False, ["I can't do anything about the weather, but I can schedule the technician for the first slot tomorrow."]),
    ("PASS", False, ["I'm coordinating with the provisioning team now and you'll hear from me by 3 pm."]),
    ("PASS", False, ["Please call back if the light turns red again and I'll stay on this ticket."]),
    ("PASS", False, ["I'll take it from here, and I'm looping in another team so you won't have to explain it again."]),
    ("PASS", False, ["I don't handle the upgrade pricing directly, but I'll personally walk it to the sales desk and get you an answer."]),
    ("PASS", False, ["You'd have to be at home for the visit, so let me book the evening slot."]),
    ("PASS", False, ["That's their policy for older devices, and I've asked for an exception on your behalf."]),
    ("PASS", False, ["Nothing I can do will bring the outage back faster, so I've set up text alerts and I'll call you when it's restored."]),
    ("PASS", False, ["I'll call back with the outcome by end of day, whatever it is."]),
    # ---------------- PASS, hard (sounds like deflection, still owns it) ----------------
    ("PASS", True, ["That's not my department, but I'll walk your ticket over to billing and stay with it until it's resolved."]),
    ("PASS", True, ["I don't handle that directly, so I'm bringing in a specialist right now and staying on the call."]),
    ("PASS", True, ["You would have to wait for the technician, but I've bumped you to the top of the queue."]),
    ("PASS", True, ["There's nothing I can do from here remotely, so I'm booking a technician for tomorrow morning."]),
    ("PASS", True, ["Contact them yourself if you like, but I've already emailed them and copied you."]),
    ("PASS", True, ["The network team owns outages, and I'm on a call with them now to get you an ETA."]),
    ("PASS", True, ["I'll have the other department call you today, and I'll chase it if they don't."]),
]

RAPPORT = [
    # ---------------- FAIL, clear ----------------
    ("FAIL", False, ["I already told you, calm down."]),
    ("FAIL", False, ["It's not rocket science, just plug it in."]),
    ("FAIL", False, ["Did you read the manual? It's basic stuff."]),
    ("FAIL", False, ["Are you serious? That's what you tried?"]),
    ("FAIL", False, ["How many times do I have to say it?"]),
    ("FAIL", False, ["You should have checked that before calling us."]),
    ("FAIL", False, ["You're wasting my time with this."]),
    ("FAIL", False, ["That's a stupid question, honestly."]),
    ("FAIL", False, ["Figure it out yourself, it's not that hard."]),
    ("FAIL", False, ["Obviously you didn't turn it off first."]),
    ("FAIL", False, ["What did you expect when you bought a cheap router?"]),
    ("FAIL", False, ["You should have known the plan had a limit."]),
    ("FAIL", False, ["Like I said, it's a waste of time to keep asking."]),
    # ---------------- FAIL, hard (subtle condescension / sarcasm) ----------------
    ("FAIL", True, ["As I said, it's very simple. I'm happy to repeat it slowly."]),
    ("FAIL", True, ["Obviously, it's not difficult, but sure, I'll walk you through it again."]),
    ("FAIL", True, ["If you'd listened the first time we wouldn't be here."]),
    ("FAIL", True, ["I just said that. Maybe write it down this time."]),
    ("FAIL", True, ["Don't be dramatic, it's only a router."]),
    ("FAIL", True, ["Seriously? The big blue button, it's right there."]),
    ("FAIL", True, ["Most people figure it out on their own, but I can help since you're struggling."]),
    # ---------------- PASS, clear (benign use of a trigger phrase) ----------------
    ("PASS", False, ["As I said, I'll send you the confirmation email within the hour."]),
    ("PASS", False, ["Obviously we want this fixed for you today, so I'm staying on until it's done."]),
    ("PASS", False, ["Don't be worried about the charge, it will be credited back to your account."]),
    ("PASS", False, ["Like I said, I'll personally follow up tomorrow morning."]),
    ("PASS", False, ["How many times has it dropped today? That will help me narrow it down."]),
    ("PASS", False, ["If you'd like, I can send the steps by email as well."]),
    ("PASS", False, ["Seriously? That's great news, I'm glad the speed is back."]),
    ("PASS", False, ["It's not difficult, and I'll talk you through each step slowly."]),
    ("PASS", False, ["You should have received a text with the confirmation number."]),
    ("PASS", False, ["Basic stuff first: let's check the cables, then we'll move on."]),
    ("PASS", False, ["I just said I would escalate it, and it's done, here's the reference number."]),
    ("PASS", False, ["Don't be afraid to ask me to slow down, I'm happy to repeat anything."]),
    ("PASS", False, ["You should have a green light now, can you check?"]),
    # ---------------- PASS, hard (blunt-sounding, still professional) ----------------
    ("PASS", True, ["Obviously I can't see your screen, so please describe what you see."]),
    ("PASS", True, ["As I said, the fee is part of the contract, but I'm happy to walk you through the terms."]),
    ("PASS", True, ["If you'd prefer a technician visit, I can book one for you."]),
    ("PASS", True, ["Please don't be alarmed by the red light, it's normal during updates."]),
    ("PASS", True, ["That's the third drop you've mentioned, so how many times has it happened today in total?"]),
    ("PASS", True, ["You should have gotten the invoice by now, let me resend it."]),
    ("PASS", True, ["It's not difficult once you see where the button is, and it took me a while to find it too."]),
]
