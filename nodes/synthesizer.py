"""
nodes/synthesizer.py

Synthesizer & Risk Scoring Engine (Fan-In Node):
1. Collects findings accumulated from all 4 parallel auditors.
2. Deduplicates overlapping findings across auditor domains.
3. Computes a weighted risk score (0-100) and assigns a risk_level.
4. Determines if Human-In-The-Loop approval is required (requires_approval = True).
"""

from typing import List, Dict, Any, Tuple
from state import PRReviewState, AuditFinding

# Severity weights used to calculate the composite risk score
SEVERITY_WEIGHTS = {
    "CRITICAL": 35,
    "HIGH": 20,
    "MEDIUM": 10,
    "LOW": 5
}


def deduplicate_findings(raw_findings: List[AuditFinding]) -> List[AuditFinding]:
    """
    Deduplicates findings when multiple auditors flag the same issue on overlapping lines.
    Prioritizes higher severity when duplicate or overlapping reports exist.
    """
    severity_rank = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    deduped: List[AuditFinding] = []

    # Sort findings by file, start line, and highest severity first
    sorted_findings = sorted(
        raw_findings,
        key=lambda f: (
            f.get("file_path", ""),
            f.get("line_start", 0),
            -severity_rank.get(f.get("severity", "LOW"), 1)
        )
    )

    for finding in sorted_findings:
        is_duplicate = False
        for existing in deduped:
            # Check if in same file and targeting overlapping line numbers
            same_file = existing.get("file_path") == finding.get("file_path")
            lines_overlap = not (
                finding.get("line_end", 0) < existing.get("line_start", 0) or
                finding.get("line_start", 0) > existing.get("line_end", 0)
            )

            # Check for keyword similarity in issue title (e.g. SQL Injection or JWT Secret)
            title_a = existing.get("issue_title", "").lower()
            title_b = finding.get("issue_title", "").lower()
            common_topic = any(
                keyword in title_a and keyword in title_b
                for keyword in ["sql", "jwt", "secret", "n+1", "connection"]
            )

            if same_file and (lines_overlap or common_topic):
                is_duplicate = True
                break

        if not is_duplicate:
            deduped.append(finding)

    return deduped


def calculate_risk(findings: List[AuditFinding]) -> Tuple[int, str, bool]:
    """
    Calculates composite risk score (0-100), risk level, and HITL approval requirement.
    
    Rules:
    - CRITICAL finding adds 35 points
    - HIGH finding adds 20 points
    - MEDIUM finding adds 10 points
    - LOW finding adds 5 points
    - Any CRITICAL vulnerability or score >= 50 enforces requires_approval = True
    """
    raw_score = sum(SEVERITY_WEIGHTS.get(f.get("severity", "LOW"), 5) for f in findings)
    risk_score = min(100, raw_score)

    if risk_score >= 75:
        risk_level = "CRITICAL"
    elif risk_score >= 50:
        risk_level = "HIGH"
    elif risk_score >= 25:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Strict safety gate: Any critical vulnerability or HIGH/CRITICAL score requires approval
    has_critical_issue = any(f.get("severity") == "CRITICAL" for f in findings)
    requires_approval = has_critical_issue or risk_level in ["HIGH", "CRITICAL"]

    return risk_score, risk_level, requires_approval


def synthesizer_node(state: PRReviewState) -> dict:
    """
    LangGraph Fan-In Node.
    Consolidates parallel findings, scores overall PR risk, and triggers the HITL gate.
    """
    raw_findings = state.get("audit_findings", [])
    deduped = deduplicate_findings(raw_findings)
    risk_score, risk_level, requires_approval = calculate_risk(deduped)

    status = "WAITING_APPROVAL" if requires_approval else "REPAIRING"

    print("\n" + "=" * 70)
    print("🧠 [Synthesizer Node] Findings Aggregated & Analyzed")
    print("=" * 70)
    print(f"  • Raw Findings from Auditors: {len(raw_findings)}")
    print(f"  • Deduplicated Action Items : {len(deduped)}")
    print(f"  • Aggregate Risk Score       : {risk_score}/100")
    print(f"  • Calculated Risk Level      : {risk_level}")
    print(f"  • Human Approval Required    : {'⚠️  YES (HITL Triggered)' if requires_approval else '✅ NO (Auto-pass)'}")
    print(f"  • Next Workflow Status       : {status}")
    print("=" * 70)

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "requires_approval": requires_approval,
        "status": status
    }
