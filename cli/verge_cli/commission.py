"""The commissioning workflow (spec §14.5) — CLI presentation layer.

Core logic lives in ``eval.commissioning`` so the API and CLI share one path.
"""

from __future__ import annotations

from eval.commissioning import (
    DEMO_LAYOUT,
    DEMO_SENSORS,
    MIN_RULES_FOR_GOLIVE,
    Check,
    CommissioningReport,
    run_commission,
)

__all__ = [
    "Check",
    "CommissioningReport",
    "DEMO_LAYOUT",
    "DEMO_SENSORS",
    "MIN_RULES_FOR_GOLIVE",
    "render_markdown",
    "run_commission",
]


def render_markdown(report: CommissioningReport) -> str:
    icon = {"pass": "✅", "warn": "⚠️ ", "fail": "❌"}
    lines = [
        f"# Commissioning report — {report.plant}",
        "",
        "> Spec §14.5. Six steps, every plant, in order. Verge acts on nothing "
        "here (P8); it reports readiness so the safety officer decides go-live "
        "with measured numbers, not a pitch.",
        "",
        f"**Readiness: {'READY for 30-day shadow mode' if report.ready else 'NOT READY'}**",
        "",
        "| Step | | Detail |",
        "|------|---|--------|",
    ]
    for c in report.checks:
        lines.append(f"| {c.step} | {icon.get(c.status, c.status)} | {c.detail} |")
    if report.dry_run:
        lines += [
            "",
            "## Dry-run vs. history (step 5)",
            "",
            "_What Verge would have caught on this plant's incidents, vs. the "
            "fixed-threshold (B0), rate-of-rise (B1), and AND-gate (B2) baselines._",
            "",
            "| Incident | Verge lead (band) | Band OK | B0 | B1 | B2 |",
            "|----------|-------------------|---------|----|----|----|",
        ]
        for d in report.dry_run:
            v = d["verge"]
            lead = "silent" if v["leadMin"] is None else f"{v['leadMin']} min"
            band = v["band"] or "—"
            cal = v.get("bandCalibrated")
            cal_s = "—" if cal is None else ("yes" if cal else "no")

            def _lm(b):
                return "silent" if b["leadMin"] is None else f"{b['leadMin']} min"

            lines.append(
                f"| {d['incident']} | **{lead} ({band})** | {cal_s} "
                f"| {_lm(d['b0'])} | {_lm(d['b1'])} | {_lm(d['b2'])} |")
    lines.append("")
    return "\n".join(lines)
