"""relabel_fixes.py — apply the corrections tracked across the labeling session.

Five rows to fix:
  19df97c26d3467f8 — wrong values in language_patterns / edge_case_reason
  19e32408d592d128 — edge_case_reason got "y"
  19e32e093576d648 — exclude from eval (stitched Typeform threads)
  19e37739e85c19db — change to qualified/booked with cross_thread_continuation
  19e4be5fea76755d — exclude from eval (stitched Toast form threads)

We don't UPDATE the existing rows — we INSERT new label rows. The labels table
allows multiple labels per inquiry_id; downstream queries can take the most
recent by labeled_at. Keeps the audit trail intact.
"""
import json, sqlite3
from datetime import datetime, timezone

DB = "labels.db"

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

# Each entry is a full replacement label. Mirrors the labels-table schema.
FIXES = [
    {
        "inquiry_id": "19df97c26d3467f8",
        "received_at": None,
        "channel": "direct_email",
        "inquiry_type": "private_event",
        "language": "en",
        "group_size": 35,
        "lead_time_days": 15,
        "date_specificity": "firm_date",
        "budget_signal": "absent",
        "budget_amount": None,
        "budget_basis": None,
        "menu_tier_fit": "entry",
        "qualification_decision": "qualified",
        "decision_reasoning": "Repeat customer (referenced 2023 event), 35-guest onsite private event for May 20. Confirmed Menu #1 plus house Pinot Grigio and Pinot Noir matching prior event. Final headcount 32. Operator referenced prior selections to speed re-qualification.",
        "response_sent": "Sent menus #1 and #2, referenced 2023 selections (Menu #1), reoffered house wines at same prices. Followed up for confirmation. Confirmed Menu #1 and prior wine choices.",
        "response_latency_hours": None,
        "outcome": "booked",
        "friction_points": ["operator_followup_required"],
        "language_patterns": ["repeat_customer", "operator_referenced_prior_selections", "menu_continuity"],
        "edge_case_flag": 1,
        "edge_case_reason": "RELABEL: prior label had 'y' typed into language_patterns and 'yes' typed into edge_case_reason. Real reason: clean example of a repeat-customer fast re-qualification where the operator surfaces prior event details. Useful for testing agent recognition of returning customers and ability to propose 'same as last time' shortcuts.",
        "unresolved_fields": [],
    },
    {
        "inquiry_id": "19e32408d592d128",
        "received_at": None,
        "channel": "direct_email",
        "inquiry_type": "private_event",
        "language": "en",
        "group_size": 25,
        "lead_time_days": 14,
        "date_specificity": "firm_date",
        "budget_signal": "absent",
        "budget_amount": None,
        "budget_basis": None,
        "menu_tier_fit": "mid",
        "qualification_decision": "qualified",
        "decision_reasoning": "Returning customer, 20-25 guests, firm date, requested specific space (left front patio). Customer chose 3-course chosen entree menu and confirmed booking within the thread. Fully email-qualified with no phone call needed for the booking decision itself.",
        "response_sent": "Offered front private patio with 3-course or buffet menu options, explained how each menu format works, confirmed booking on left front patio with 3-course menu for 20-25 guests.",
        "response_latency_hours": None,
        "outcome": "booked",
        "friction_points": [],
        "language_patterns": ["returning_customer", "knows_the_space", "references_48hr_rule", "celebration_of_life_context", "fast_decision"],
        "edge_case_flag": 1,
        "edge_case_reason": "RELABEL: prior edge_case_reason got 'y' typed instead of the real reason. Real reason: reference example of fast, clean email-qualified booking with a knowledgeable returning customer. Whole qualification took ~80 minutes from initial inquiry to confirmed booking. Useful positive baseline alongside the 16-guest June 11 thread.",
        "unresolved_fields": [],
    },
    {
        "inquiry_id": "19e32e093576d648",
        "received_at": None,
        "channel": "typeform",
        "inquiry_type": "unknown",
        "language": "en",
        "group_size": None,
        "lead_time_days": None,
        "date_specificity": "no_date",
        "budget_signal": "absent",
        "budget_amount": None,
        "budget_basis": None,
        "menu_tier_fit": "unknown",
        "qualification_decision": "human_review",
        "decision_reasoning": "EXCLUDE_FROM_EVAL: STITCHED THREAD - contains two unrelated Typeform submissions for different events (25-guest offsite 6/12 and 15-guest baby shower 7/25). Gmail bundled them by sender. Do not use for evaluation until exporter is rebuilt to split these.",
        "response_sent": "No response in thread.",
        "response_latency_hours": None,
        "outcome": "unknown",
        "friction_points": [],
        "language_patterns": ["stitched_thread", "export_bug", "typeform_submission", "EXCLUDE_FROM_EVAL"],
        "edge_case_flag": 1,
        "edge_case_reason": "EXCLUDE_FROM_EVAL: BAD DATA - two unrelated Typeform submissions stitched into one thread by Gmail bundling. Tracked for the option-C exporter session.",
        "unresolved_fields": [],
    },
    {
        "inquiry_id": "19e37739e85c19db",
        "received_at": None,
        "channel": "typeform",
        "inquiry_type": "catering",
        "language": "en",
        "group_size": 20,
        "lead_time_days": 62,
        "date_specificity": "firm_date",
        "budget_signal": "explicit",
        "budget_amount": 5000,
        "budget_basis": "total",
        "menu_tier_fit": "unknown",
        "qualification_decision": "qualified",
        "decision_reasoning": "RELABEL: same customer as email thread 19e3cdfd754257d3 (50th anniversary, July 18, 20 guests, San Marcos). Typeform was first touch, phone call did the qualifying work, email thread completed the booking. Final outcome: booked at $2020.85 with $80 out-of-tier delivery fee.",
        "response_sent": "No response in this thread - operator response went through the parallel email thread.",
        "response_latency_hours": None,
        "outcome": "booked",
        "friction_points": ["extended_zone_delivery"],
        "language_patterns": ["budget_explicit", "frequent_guest", "milestone_event", "offsite_delivery", "extended_zone", "cross_thread_continuation"],
        "edge_case_flag": 1,
        "edge_case_reason": "RELABEL: previously labeled human_review/unknown. Cross-thread evidence from 19e3cdfd754257d3 confirms this booked. Customer Typeform-self-reported $5K+ budget; actual booking landed at $2020.85, showing Typeform budget self-report runs high.",
        "unresolved_fields": [],
    },
    {
        "inquiry_id": "19e4be5fea76755d",
        "received_at": None,
        "channel": "web_form",
        "inquiry_type": "unknown",
        "language": "en",
        "group_size": None,
        "lead_time_days": None,
        "date_specificity": "no_date",
        "budget_signal": "absent",
        "budget_amount": None,
        "budget_basis": None,
        "menu_tier_fit": "unknown",
        "qualification_decision": "human_review",
        "decision_reasoning": "EXCLUDE_FROM_EVAL: STITCHED THREAD - contains two unrelated Toast contact form submissions: a plant-based menu vendor pitch and a real 10-12 guest graduation dinner reservation request. Gmail bundled them. Do not use for evaluation until exporter is rebuilt.",
        "response_sent": "No response in thread.",
        "response_latency_hours": None,
        "outcome": "unknown",
        "friction_points": [],
        "language_patterns": ["stitched_thread", "export_bug", "toast_form_submission", "EXCLUDE_FROM_EVAL"],
        "edge_case_flag": 1,
        "edge_case_reason": "EXCLUDE_FROM_EVAL: BAD DATA - two unrelated Toast form submissions stitched. Second stitched-thread instance after 19e32e093576d648, confirming Gmail-bundling pattern. Tracked for option-C exporter session.",
        "unresolved_fields": [],
    },
]


def insert_fix(cx, fix):
    cx.execute("""INSERT INTO labels
        (inquiry_id, received_at, channel, inquiry_type, language, group_size,
         lead_time_days, date_specificity, budget_signal, budget_amount, budget_basis,
         menu_tier_fit, qualification_decision, decision_reasoning, response_sent,
         response_latency_hours, outcome, friction_points, language_patterns,
         edge_case_flag, edge_case_reason, unresolved_fields, labeled_at, labeled_by, batch_id)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (fix["inquiry_id"], fix["received_at"], fix["channel"], fix["inquiry_type"],
         fix["language"], fix["group_size"], fix["lead_time_days"], fix["date_specificity"],
         fix["budget_signal"], fix["budget_amount"], fix["budget_basis"], fix["menu_tier_fit"],
         fix["qualification_decision"], fix["decision_reasoning"], fix["response_sent"],
         fix["response_latency_hours"], fix["outcome"], json.dumps(fix["friction_points"]),
         json.dumps(fix["language_patterns"]), fix["edge_case_flag"], fix["edge_case_reason"],
         json.dumps(fix["unresolved_fields"]), now(), "hugo", "b1_relabel"))


def main():
    cx = sqlite3.connect(DB)
    cx.execute("PRAGMA foreign_keys = ON")
    for fix in FIXES:
        insert_fix(cx, fix)
        print(f"  inserted relabel for {fix['inquiry_id']}")
    cx.commit()
    print(f"\napplied {len(FIXES)} relabels in batch 'b1_relabel'")

    # Stats summary across the most recent label per inquiry.
    print("\n=== batch 1 stats (using most recent label per inquiry) ===")
    rows = cx.execute("""
        SELECT inquiry_type, qualification_decision, outcome, channel
        FROM labels l
        WHERE labeled_at = (SELECT MAX(labeled_at) FROM labels WHERE inquiry_id = l.inquiry_id)
    """).fetchall()

    from collections import Counter
    by_type    = Counter(r[0] for r in rows)
    by_decision = Counter(r[1] for r in rows)
    by_outcome = Counter(r[2] for r in rows)
    by_channel = Counter(r[3] for r in rows)

    def show(label, counter):
        total = sum(counter.values())
        print(f"\n  {label}:")
        for k, v in sorted(counter.items(), key=lambda x: -x[1]):
            print(f"    {k:<22} {v:>3}  ({100*v/total:.0f}%)")

    show("inquiry_type", by_type)
    show("qualification_decision", by_decision)
    show("outcome", by_outcome)
    show("channel", by_channel)
    cx.close()


if __name__ == "__main__":
    main()
