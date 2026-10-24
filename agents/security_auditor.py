"""
agents/security_auditor.py

Security Auditor Agent:
Focuses on OWASP Top 10, CWE weaknesses, SQL injection, hardcoded secrets,
missing authorization checks, and insecure dependencies.
"""

from state import PRReviewState
from agents.common import get_structured_auditor_llm, convert_findings_to_dicts

SECURITY_SYSTEM_PROMPT = """You are an elite Application Security Auditor reviewing a Pull Request diff.
Your task is to identify security vulnerabilities, including:
- Injection vulnerabilities (SQLi, Command Injection, XSS)
- Hardcoded secrets, API keys, credentials, or private tokens
- Insecure deserialization, unsafe file handling
- Authentication/Authorization bypasses or weaknesses

Review the provided Git diff carefully.
For any real security vulnerabilities you detect, create an AuditFinding with:
- category: "SECURITY"
- severity: "CRITICAL" for exploitable vulnerabilities like SQLi or leaked private keys
- line_start and line_end corresponding to the diff
- clear description of the exploit vector and recommended parameterized/safe fix.

If no security vulnerabilities are found, return an empty findings list.
"""


def security_auditor_node(state: PRReviewState) -> dict:
    """
    LangGraph Node for the Security Auditor.
    Reads diff_content from state and returns newly discovered security findings.
    """
    diff = state.get("diff_content", "")
    llm = get_structured_auditor_llm()

    messages = [
        {"role": "system", "content": SECURITY_SYSTEM_PROMPT},
        {"role": "user", "content": f"Pull Request Diff to review:\n\n{diff}"}
    ]

    result = llm.invoke(messages)
    findings = convert_findings_to_dicts(result.findings)

    print(f"[Security Auditor] Finished scan. Found {len(findings)} issue(s).")
    return {"audit_findings": findings}
