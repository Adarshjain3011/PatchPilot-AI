"""
agents/architecture_auditor.py

Architecture Auditor Agent:
Focuses on software engineering best practices, Clean Code principles,
separation of concerns (e.g. leaking raw DB queries into API route handlers),
coupling, and maintainability.
"""

from state import PRReviewState
from agents.common import get_structured_auditor_llm, convert_findings_to_dicts

ARCH_SYSTEM_PROMPT = """You are a Software Architect reviewing a Pull Request diff.
Your task is to identify architectural flaws, design anti-patterns, and code smells:
- Layering violations (e.g. database connections and raw SQL executed directly in HTTP route handlers instead of a repository/service layer)
- God functions / SRP (Single Responsibility Principle) violations doing routing, validation, database fetching, and serialization in one place
- Tight coupling and hardcoded dependencies
- Lack of error handling or missing transaction management

Review the provided Git diff carefully.
For any real architectural issues you detect, create an AuditFinding with:
- category: "ARCHITECTURE"
- severity: "MEDIUM" or "LOW" depending on maintainability impact
- line_start and line_end corresponding to the diff
- clear description and an architectural refactoring suggestion (e.g. extract to PostService / Repository).

If no architectural issues are found, return an empty findings list.
"""


def architecture_auditor_node(state: PRReviewState) -> dict:
    """
    LangGraph Node for the Architecture Auditor.
    Reads diff_content from state and returns newly discovered architectural findings.
    """
    diff = state.get("diff_content", "")
    llm = get_structured_auditor_llm()

    messages = [
        {"role": "system", "content": ARCH_SYSTEM_PROMPT},
        {"role": "user", "content": f"Pull Request Diff to review:\n\n{diff}"}
    ]

    result = llm.invoke(messages)
    findings = convert_findings_to_dicts(result.findings)

    print(f"[Architecture Auditor] Finished scan. Found {len(findings)} issue(s).")
    return {"audit_findings": findings}
