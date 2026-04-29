"""
synthesizer.py
--------------
Sends the unified context dict to Claude and returns a structured dict
with critical/watch/on_track/bottom_line sections for the briefing UI.
"""

import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()


def _build_prompt(ctx: dict) -> str:
    invoice_lines = "\n".join(
        f"  - {inv['invoiceId']} | {inv['customerName']} | ${inv['amount']:,} | "
        f"{inv['daysOverdue']} days overdue | Action: {inv['action']}"
        for inv in ctx["flaggedInvoices"]
    )
    gap_lines = "\n".join(
        f"  - Placement {g['placementId']} ({g['candidateName']} @ {g['clientName']}) "
        f"— estimated unbilled: ${g['estimatedUnbilled']:,}"
        for g in ctx["billingGaps"]
    )
    recruiter_lines = "\n".join(
        f"  - {r['recruiter']}: {r['week2Placements']} placements this week "
        f"(was {r['week1Placements']} last week) — {r['flag']}. {r['note']}"
        for r in ctx["flaggedRecruiters"]
    )
    aged_critical_lines = "\n".join(
        f"  - {j['id']} | {j['clientName']} | {j['role']} | "
        f"{j['daysOpen']} days open | {j['submissions']} submissions"
        for j in ctx["agedCriticalOrders"]
    )
    stalled_lines = "\n".join(
        f"  - {j['id']} | {j['clientName']} | {j['role']} | "
        f"{j['daysOpen']} days open | 0 submissions"
        for j in ctx["stalledOrders"]
    )
    end_lines = "\n".join(
        f"  - {u['candidateName']} @ {u['clientName']} — ends {u['endDate']} "
        f"({u['daysRemaining']} days) | {u['redeploymentStatus']}"
        for u in ctx["upcomingEnds"]
    )

    return f"""You are an AI executive briefing assistant for Talent Groups, a staffing firm.
Produce a sharp, decisive morning briefing for the CIO using the submit_briefing tool.

TODAY'S DATE: Thursday, April 24, 2026

Rules:
- critical = max 3 findings, each with max 3 bullet items — issues needing action TODAY
- watch = max 3 findings, each with max 3 bullet items — trends to monitor
- on_track = exactly 3 bullet strings (revenue attainment, margin, active billing)
- bottom_line = one decisive sentence, max 35 words — REQUIRED, never leave empty
- Use real numbers — never vague
- Each finding title must state the key figure or impact
- In item strings: use <strong>name</strong> for bold, [RED]text[/RED] / [AMBER]text[/AMBER] / [GREEN]text[/GREEN] for colour

---

BULLHORN ATS DATA:

Active Placements: {ctx['activePlacements']} contracts
Billable Hours: {ctx['weeklyBillableHours']:,} hrs | Avg Bill Rate: ${ctx['avgBillRate']}/hr | Avg Margin: {ctx['avgMarginPct']}%
Projected Weekly Revenue: ${ctx['projectedWeeklyRevenue']:,}

Pipeline (week2 vs week1):
  Submissions: {ctx['week2']['submissions']} (was {ctx['week1']['submissions']}) | Interviews: {ctx['week2']['interviews']} | Offers: {ctx['week2']['offers']} | Placements: {ctx['week2']['placements']} (was {ctx['week1']['placements']})
  Fill Rate: {ctx['week2']['fillRate']}% (was {ctx['week1']['fillRate']}%) | Time-to-Fill: {ctx['week2']['timeToFill']} days (was {ctx['week1']['timeToFill']})
  Trend: {ctx['wowTrend']}

Open Job Orders: {ctx['totalOpenJobOrders']} total

Aged Critical Orders:
{aged_critical_lines or '  None'}

Stalled Orders (0 submissions 7+ days):
{stalled_lines or '  None'}

Flagged Recruiters:
{recruiter_lines or '  None'}

Dallas Team Fill Rate: {ctx['dallasTeamFillRateWk1']}% → {ctx['dallasTeamFillRateWk2']}% ({ctx['dallasWoWChange']}% WoW)

Upcoming Placement Ends (next 14 days):
{end_lines or '  None'}

---

BUSINESS CENTRAL DATA:

April Revenue: ${ctx['monthlyRevenue']:,} vs ${ctx['monthlyTarget']:,} target ({ctx['monthlyAttainmentPct']}% attainment)
Weekly Run Rate: ${ctx['weeklyRunRate']:,} vs ${ctx['weeklyRunRateTarget']:,} target
Gross Margin: {ctx['grossMarginPct']}% (target: {ctx['grossMarginTarget']}%)
DSO: {ctx['dsoDays']} days (target: <{ctx['dsoTarget']} days)

AR Aging:
  Total Outstanding: ${ctx['totalAR']:,}
  61–90 days: ${ctx['ar_61_90']:,}
  90+ days:   ${ctx['ar_90plus']:,}

Flagged Invoices:
{invoice_lines or '  None'}

Unbilled (Bullhorn placements missing BC invoice):
{gap_lines or '  None'}
  Total estimated unbilled: ${ctx['totalUnbilledEstimate']:,}

---

Output the JSON now.
"""


_BRIEFING_TOOL = {
    "name": "submit_briefing",
    "description": "Submit the structured executive briefing sections.",
    "input_schema": {
        "type": "object",
        "properties": {
            "critical": {
                "type": "array",
                "description": "Issues requiring action TODAY",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string", "description": "Short title stating the key issue and figure"},
                        "tag":   {"type": "string", "description": "1-2 word category label"},
                        "items": {
                            "type": "array",
                            "items": {"type": "string", "description": "Bullet point — use <strong> for bold, [RED]..[/RED] / [AMBER]..[/AMBER] / [GREEN]..[/GREEN] for colour highlights"},
                        },
                    },
                    "required": ["title", "tag", "items"],
                },
            },
            "watch": {
                "type": "array",
                "description": "Trends to monitor closely",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "tag":   {"type": "string"},
                        "items": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["title", "tag", "items"],
                },
            },
            "on_track": {
                "type": "array",
                "description": "2-3 positives to note",
                "items": {"type": "string"},
            },
            "bottom_line": {
                "type": "string",
                "description": "Single decisive sentence (max 40 words) on where the CIO's focus must go today",
            },
        },
        "required": ["critical", "watch", "on_track", "bottom_line"],
    },
}


def generate_briefing(context: dict) -> dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=api_key)
    prompt = _build_prompt(context)

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=4096,
        tools=[_BRIEFING_TOOL],
        tool_choice={"type": "tool", "name": "submit_briefing"},
        messages=[{"role": "user", "content": prompt}],
    )

    tool_block = next(b for b in response.content if b.type == "tool_use")
    data = tool_block.input  # already a validated dict — no JSON parsing needed
    _expand_tags(data)
    return data


def _expand_tags(data: dict) -> None:
    import re
    replacements = [
        (r'\[RED\](.*?)\[/RED\]',     r'<span class="hl-red">\1</span>'),
        (r'\[AMBER\](.*?)\[/AMBER\]', r'<span class="hl-amber">\1</span>'),
        (r'\[GREEN\](.*?)\[/GREEN\]', r'<span class="hl-green">\1</span>'),
    ]

    def fix(s: str) -> str:
        for pattern, repl in replacements:
            s = re.sub(pattern, repl, s, flags=re.IGNORECASE)
        return s

    for section in ("critical", "watch"):
        for finding in data.get(section, []):
            finding["title"] = fix(finding.get("title", ""))
            finding["items"] = [fix(item) for item in finding.get("items", [])]

    data["on_track"] = [fix(item) for item in data.get("on_track", [])]
    data["bottom_line"] = fix(data.get("bottom_line", ""))
