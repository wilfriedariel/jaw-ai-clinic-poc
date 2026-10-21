"""Synthetic data -> temperature agent -> audience agent -> results.json + demo.html.

Run: python3 -I pipeline.py   (deterministic, seed fixed)
Simplifications: rules are hand-set points (upgrade path: fit weights once real
Plato history exists); cost-per-lead is an assumed constant per source.
"""
import hashlib, json, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split

HERE = Path(__file__).parent
SEED = 11
N = 2400
rng = np.random.default_rng(SEED)
sig = lambda x: 1 / (1 + np.exp(-x))

SOURCES = ["Meta ad", "Instagram organic", "Google search", "Referral", "WhatsApp walk-in"]
SRC_P = [0.34, 0.18, 0.2, 0.12, 0.16]
SRC_EFFECT = {"Meta ad": -0.35, "Instagram organic": 0.0, "Google search": 0.15, "Referral": 0.7, "WhatsApp walk-in": 0.3}
ASSUMED_CPL = {"Meta ad": 14.0, "Instagram organic": 4.0, "Google search": 18.0, "Referral": 6.0, "WhatsApp walk-in": 3.0}  # S$, ASSUMED
TREATMENTS = ["Laser hair removal", "Pigmentation laser", "Acne scar treatment", "Facial", "Injectables", "Body contouring"]
TR_EFFECT = {"Laser hair removal": 0.2, "Pigmentation laser": 0.35, "Acne scar treatment": 0.25, "Facial": -0.2, "Injectables": 0.1, "Body contouring": -0.1}
AREAS = ["Central", "East", "West", "North-East", "North"]
INTERVAL = {"Laser hair removal": 42, "Pigmentation laser": 35, "Acne scar treatment": 30, "Facial": 28, "Injectables": 120, "Body contouring": 21}


def gen():
    rows = []
    for i in range(N):
        kind = "lead" if rng.random() < 0.6 else "patient"
        z = rng.normal()  # hidden intent, never given to the agents
        tr = rng.choice(TREATMENTS)
        age = int(np.clip(rng.normal(34, 9), 19, 62))
        r = dict(id=f"C{i:04d}", kind=kind, age=age, area=rng.choice(AREAS, p=[.3, .22, .18, .17, .13]),
                 treatment=tr, consent=bool(rng.random() < 0.72))
        if kind == "lead":
            src = rng.choice(SOURCES, p=SRC_P)
            r.update(source=src,
                     asked_price=bool(rng.random() < sig(0.9 * z - 0.2)),
                     asked_slots=bool(rng.random() < sig(1.1 * z - 1.0)),
                     msgs=int(np.clip(rng.poisson(np.exp(1.2 + 0.35 * z)), 1, 25)),
                     days_since_contact=int(np.clip(rng.exponential(np.exp(2.0 - 0.6 * z)), 0, 90)),
                     reply_latency_h=float(np.clip(rng.exponential(np.exp(1.3 - 0.5 * z)), 0.1, 72)),
                     days_since_enquiry=int(rng.integers(0, 45)))
            r["days_since_contact"] = min(r["days_since_contact"], r["days_since_enquiry"])
            logit = -1.5 + 1.2 * z + SRC_EFFECT[src] + TR_EFFECT[tr] + rng.normal(0, 0.8)
        else:
            iv = INTERVAL[tr]
            since = max(1, int(rng.normal(iv * np.exp(-0.25 * z), iv * 0.5)))
            has_pkg = rng.random() < 0.55
            r.update(source="Existing patient",
                     visits=int(np.clip(rng.poisson(np.exp(1.6 + 0.3 * z)), 1, 40)),
                     last_visit_days=min(since, 500),
                     next_booking=bool(rng.random() < sig(1.0 * z - 1.2)),
                     sessions_left=int(rng.integers(1, 6)) if has_pkg else 0,
                     package_expiry_days=int(rng.integers(5, 120)) if has_pkg else 0,
                     spend=int(np.clip(rng.normal(900 + 450 * z, 500), 80, 6000)))
            logit = -1.0 + 1.1 * z + TR_EFFECT[tr] * 0.5 + rng.normal(0, 0.8)
        r["converted"] = bool(rng.random() < sig(logit))
        rows.append(r)
    return pd.DataFrame(rows)


def score_row(r):
    """Transparent points. Returns (score 0-100, [reasons])."""
    s, why = 30, []
    def add(p, t):
        nonlocal s
        s += p; why.append((p, t))
    if r.kind == "lead":
        if r.asked_price: add(14, "asked the price")
        if r.asked_slots: add(18, "asked for a slot")
        if r.msgs >= 6: add(10, f"{int(r.msgs)} messages, engaged")
        elif r.msgs <= 2: add(-8, "only 1-2 messages")
        if r.days_since_contact <= 2: add(14, "contacted within 2 days")
        elif r.days_since_contact > 14: add(-16, f"silent {int(r.days_since_contact)} days")
        if r.reply_latency_h < 2: add(10, "replies within 2h")
        elif r.reply_latency_h > 24: add(-10, "slow to reply (>24h)")
        if r.source == "Referral": add(10, "referral")
        if r.source == "Meta ad": add(-4, "cold paid-social source")
        if r.days_since_enquiry > 30: add(-8, "enquiry older than 30 days")
    else:
        iv = INTERVAL[r.treatment]
        ratio = r.last_visit_days / iv
        if 0.8 <= ratio <= 1.6: add(18, f"due for {r.treatment} review ({int(r.last_visit_days)}d vs {iv}d interval)")
        elif ratio > 4: add(-18, f"lapsed ({int(r.last_visit_days)}d since visit)")
        elif ratio > 2.2: add(-4, "lapsing")
        if r.sessions_left > 0 and r.package_expiry_days <= 42: add(16, f"{int(r.sessions_left)} sessions expire in {int(r.package_expiry_days)}d")
        if r.visits >= 8: add(8, f"{int(r.visits)} visits, loyal")
        if r.spend >= 2000: add(5, "high-spend patient")
    return int(np.clip(s, 0, 100)), why


def tier(s): return "Hot" if s >= 62 else ("Warm" if s >= 40 else "Cold")


def next_action(r, t):
    if r.kind == "lead":
        return {"Hot": "Receptionist calls/WhatsApps today (staff-approved draft)",
                "Warm": "Send one discovery question, staff-approved",
                "Cold": "Nurture audience only, no staff time"}[t]
    return {"Hot": "Invite to review with Dr Cheak (doctor-approved pathway)",
            "Warm": "Add to next morning huddle sheet",
            "Cold": "Win-back campaign if consented"}[t]


def wilson_lo(k, n, z=1.96):
    if n == 0: return 0.0
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d


FIRST = ["Mei Ling", "Jia Hui", "Priya", "Siti", "Rachel", "Amanda", "Shu Ting", "Nurul", "Hui Min", "Sarah", "Wei Ting",
         "Aisha", "Jasmine", "Kelly", "Grace", "Natalie", "Farah", "Michelle", "Pei Shan", "Cheryl", "Joanne", "Tiffany", "Vanessa", "Bernice"]
LAST = list("ABCDEFGHJKLMNPRSTWY")


def add_chat(df):
    """Names + a short WhatsApp thread per contact. Separate RNG so the scored data is untouched."""
    g = np.random.default_rng(SEED + 1000)
    names, phones, chats = [], [], []
    for r in df.itertuples():
        names.append(f"{g.choice(FIRST)} {g.choice(LAST)}.")
        phones.append(f"+65 {g.choice([8, 9])}••• {g.integers(1000, 9999)}")
        if r.kind != "lead":
            chats.append([]); continue
        tr = r.treatment.lower()
        if r.asked_price and r.asked_slots: first = f"Hi, how much is {tr}? And do you have a slot this week?"
        elif r.asked_price: first = f"Hi, how much is {tr}?"
        elif r.asked_slots: first = f"Hi, do you have a slot this week for {tr}?"
        else: first = f"Hi, I'm interested in {tr}. Can I know more?"
        reply = f"Hi! Thanks for asking about {tr}. Would you like a consultation with Dr Cheak to see what suits you?"
        back = g.choice(["Ok thanks, let me think about it", "Is there a weekend slot?", "Do you have any promotions?", "What is the downtime like?"])
        dse, dsc = int(r.days_since_enquiry), int(r.days_since_contact)
        last_from = ("us" if g.random() < 0.65 else "them") if r.msgs <= 3 else ("them" if g.random() < 0.5 else "us")
        chat = [dict(who="them", text=first, days_ago=dse)]
        if last_from == "us":
            chat.append(dict(who="us", text=reply, days_ago=dsc))
        elif dsc < dse:
            chat.append(dict(who="us", text=reply, days_ago=min(dse, dsc + 1)))
            chat.append(dict(who="them", text=back, days_ago=dsc))
        chats.append(chat)
    df["name"], df["phone"], df["chat"] = names, phones, chats
    return df


def main():
    df = gen()
    # v2: patients with a booking need no outreach, so they leave the list and the evaluation
    # (v1 scored them -10 while the outcome counted them as converted; see CONTRACT.md amendment).
    df = df[~((df.kind == "patient") & df.next_booking)].reset_index(drop=True)
    sc = df.apply(score_row, axis=1)
    df["score"] = [x[0] for x in sc]
    df["why"] = [[w[1] for w in sorted(x[1], key=lambda t: -abs(t[0]))[:4]] for x in sc]
    df["tier"] = df.score.map(tier)
    df["action"] = [next_action(r, r.tier) for r in df.itertuples()]

    train, test = train_test_split(df, test_size=0.3, random_state=SEED, stratify=df.converted)
    res = {"seed": SEED, "n": len(df), "base_rate": float(df.converted.mean())}
    res["rules_auc_holdout"] = float(roc_auc_score(test.converted, test.score))
    for k in ("lead", "patient"):
        t = test[test.kind == k]
        res[f"rules_auc_holdout_{k}"] = float(roc_auc_score(t.converted, t.score))

    # fitted logistic on same observable features = what "scoring later" could add
    feat = ["age", "asked_price", "asked_slots", "msgs", "days_since_contact", "reply_latency_h", "days_since_enquiry",
            "visits", "last_visit_days", "next_booking", "sessions_left", "package_expiry_days", "spend"]
    X = df[feat].fillna(0).astype(float)
    X = pd.concat([X, pd.get_dummies(df[["kind", "source", "treatment"]]).astype(float)], axis=1)
    lr = LogisticRegression(max_iter=3000)
    lr.fit((X.loc[train.index] - X.loc[train.index].mean()) / (X.loc[train.index].std() + 1e-9), train.converted)
    mu, sd = X.loc[train.index].mean(), X.loc[train.index].std() + 1e-9
    res["logistic_auc_holdout"] = float(roc_auc_score(test.converted, lr.predict_proba((X.loc[test.index] - mu) / sd)[:, 1]))

    tt = test.groupby("tier").converted.agg(["mean", "count"])
    res["holdout_tier_conv"] = {k: {"rate": float(v["mean"]), "n": int(v["count"])} for k, v in tt.iterrows()}
    res["hot_over_cold"] = float(tt.loc["Hot", "mean"] / tt.loc["Cold", "mean"])
    res["all_tier_counts"] = df.tier.value_counts().to_dict()

    # ---- audience agent: learns only from training-set converters, leads only (acquisition)
    leads_tr = train[train.kind == "lead"].copy()
    base = leads_tr.converted.mean()
    leads_tr["age_band"] = pd.cut(leads_tr.age, [0, 27, 35, 45, 99], labels=["<=27", "28-35", "36-45", "46+"]).astype(str)
    segs = []
    for dims in (["source"], ["treatment"], ["age_band"], ["source", "treatment"], ["treatment", "age_band"], ["area"]):
        for key, g in leads_tr.groupby(dims):
            n, k = len(g), int(g.converted.sum())
            if n < 40: continue
            key = key if isinstance(key, tuple) else (key,)
            segs.append(dict(segment=" × ".join(map(str, key)), n=n, conv=k / n, lift=(k / n) / base,
                             lift_lo=wilson_lo(k, n) / base))
    segs = sorted(segs, key=lambda s: -s["lift_lo"])
    res["audience_base_rate_train_leads"] = float(base)
    res["top_segments"] = segs[:8]
    res["avoid_segments"] = sorted(segs, key=lambda s: s["lift_lo"])[:5]
    res["top_segment_lift_lo"] = segs[0]["lift_lo"]

    # source economics with ASSUMED cost per lead
    econ = []
    for src, g in leads_tr.groupby("source"):
        cpl = ASSUMED_CPL[src]
        conv = g.converted.mean()
        econ.append(dict(source=src, leads=len(g), conv=float(conv), assumed_cpl=cpl, cost_per_conversion=float(cpl / conv)))
    res["source_econ"] = sorted(econ, key=lambda e: e["cost_per_conversion"])

    # seed + suppression + retarget, all consent-gated
    allc = df.copy()
    seed = allc[allc.converted & allc.consent]
    suppress = allc[(allc.kind == "patient") & (allc.last_visit_days <= 30) | ~allc.consent]
    retarget = allc[(allc.kind == "lead") & allc.tier.isin(["Warm", "Cold"]) & allc.consent]
    res["seed_size"] = int(len(seed)); res["suppress_size"] = int(len(suppress)); res["retarget_size"] = int(len(retarget))
    res["consent_leak"] = int((~seed.consent).sum() + (~retarget.consent).sum())
    res["no_consent_total"] = int((~df.consent).sum())

    thr = dict(
        rules_auc=res["rules_auc_holdout"] >= 0.62,
        hot_over_cold=res["hot_over_cold"] >= 2.0,
        top_segment=res["top_segment_lift_lo"] > 1.0,
        consent_leak=res["consent_leak"] == 0,
    )
    res["pass"] = {k: bool(v) for k, v in thr.items()}
    res["all_pass"] = bool(all(thr.values()))

    # determinism hash of the scored table
    res["output_hash"] = hashlib.sha256(df[["id", "score", "converted"]].to_csv().encode()).hexdigest()[:16]
    (HERE / "results.json").write_text(json.dumps(res, indent=1, default=str))

    # demo payload: top leads by score (not by outcome), without the outcome column shown by default
    df = add_chat(df)
    show = df.sort_values("score", ascending=False)
    raw = show.drop(columns=["why", "action", "tier", "score"]).astype(object).where(show.drop(columns=["why", "action", "tier", "score"]).notna(), None)
    demo = []
    for (_, a), r in zip(raw.iterrows(), show.itertuples()):
        d = {k: (v.item() if hasattr(v, "item") else v) for k, v in a.items()}
        d.update(score=r.score, tier=r.tier, why=r.why, action=r.action)
        demo.append(d)
    payload = dict(res=res, contacts=demo)
    html = (HERE / "demo_template.html").read_text().replace("/*DATA*/", "const DATA=" + json.dumps(payload, default=str) + ";")
    (HERE / "demo.html").write_text(html)
    print(json.dumps({k: res[k] for k in ("rules_auc_holdout", "rules_auc_holdout_lead", "rules_auc_holdout_patient",
                                          "logistic_auc_holdout", "hot_over_cold", "holdout_tier_conv",
                                          "top_segment_lift_lo", "consent_leak", "pass", "all_pass", "output_hash")}, indent=1))


if __name__ == "__main__":
    main()
