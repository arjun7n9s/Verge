"""Alert-fatigue metrics from live feedback (spec §4.6)."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from verge_schema.enums import FeedbackVerdict


def compute_fatigue_metrics(store) -> dict:
    """Aggregate FPR, daily S/N trend, and per-zone alert volume."""
    entries = store.audit_entries(limit=50_000)
    feedback_rows = [
        e for e in entries if e.get("kind") == "feedback"
    ]
    by_day: dict[str, dict[str, int]] = defaultdict(lambda: {"falseAlarms": 0, "useful": 0})
    for e in feedback_rows:
        payload = e.get("payload") or {}
        ts = payload.get("timestamp") or e.get("timestamp")
        if not ts:
            continue
        try:
            day = datetime.fromisoformat(ts.replace("Z", "+00:00")).strftime("%m/%d")
        except ValueError:
            continue
        verdict = payload.get("verdict", "")
        if verdict == FeedbackVerdict.FALSE_ALARM.value:
            by_day[day]["falseAlarms"] += 1
        elif verdict == FeedbackVerdict.USEFUL.value:
            by_day[day]["useful"] += 1

    trend = [{"date": d, **counts} for d, counts in sorted(by_day.items())]

    fpr = store.fpr()
    total_fb = sum(v["falseAlarms"] + v["useful"] for v in by_day.values())
    useful = sum(v["useful"] for v in by_day.values())
    action_rate = round(useful / total_fb, 3) if total_fb else None

    now = datetime.now(UTC)
    window = now - timedelta(hours=12)
    findings = store.list_findings(shadow=None)
    zone_counts: dict[str, int] = defaultdict(int)
    for f in findings:
        created = f.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        if created >= window:
            zone_counts[f.zone_id] += 1

    zone_limits = []
    default_limit = 15
    for zone_id, count in sorted(zone_counts.items()):
        limit = default_limit
        pct = round(100 * count / limit) if limit else 0
        zone_limits.append({
            "zoneId": zone_id,
            "current": count,
            "limit": limit,
            "pct": pct,
        })

    alerts_per_shift = round(len(findings) / max(len({f.owner for f in findings if f.owner}), 1), 1)

    return {
        "fpr": fpr,
        "alertsPerShift": alerts_per_shift,
        "falseAlarmRatio": fpr,
        "operatorActionRate": action_rate,
        "trend": trend,
        "zones": zone_limits,
        "measured": bool(feedback_rows),
    }
