"""
agents/performance_auditor.py

Performance Auditor Agent:
Focuses on algorithmic complexity, database query inefficiencies (e.g. N+1 queries),
memory leaks, missing pagination, and unindexed filtering.
"""

from state import PRReviewState
from agents.common import get_structured_auditor_llm, convert_findings_to_dicts

PERF_SYSTEM_PROMPT = """You are a Principal Performance Engineer reviewing a Pull Request diff.
Your task is to identify performance bottlenecks and resource inefficiencies, including:
- N+1 database queries (queries executed in a loop)
- Unbounded queries or missing pagination (e.g. fetchall() on large tables)
- Inefficient loops, quadratic O(n^2) complexity where O(n) is possible
- Resource leaks (unclosed database connections, unclosed file handles)

Review the provided Git diff carefully.
For any real performance issues you detect, create an AuditFinding with:
- category: "PERFORMANCE"
- severity: "HIGH" for N+1 queries or memory/connection leaks, "MEDIUM" for sub-optimal loops
- line_start and line_end corresponding to the diff
- clear description and a concrete fix (e.g. using SQL JOINs or batch fetching).

If no performance issues are found, return an empty findings list.
"""


def performance_auditor_node(state: PRReviewState) -> dict:
    """
    LangGraph Node for the Performance Auditor.
    Reads diff_content from state and returns newly discovered performance findings.
    """
    diff = state.get("diff_content", "")
    llm = get_structured_auditor_llm()

    messages = [
        {"role": "system", "content": PERF_SYSTEM_PROMPT},
        {"role": "user", "content": f"Pull Request Diff to review:\n\n{diff}"}
    ]

    result = llm.invoke(messages)
    findings = convert_findings_to_dicts(result.findings)

    print(f"[Performance Auditor] Finished scan. Found {len(findings)} issue(s).")
    return {"audit_findings": findings}
