"""
agents/test_auditor.py

Test Auditor Agent:
Focuses on test coverage gaps, missing regression tests, untested edge cases
(null inputs, empty collections, boundary conditions), and brittle test patterns.
"""

from state import PRReviewState
from agents.common import get_structured_auditor_llm, convert_findings_to_dicts

TEST_SYSTEM_PROMPT = """You are a Lead QA and Test Automation Engineer reviewing a Pull Request diff.
Your task is to identify gaps in testing, missing test coverage, and unhandled edge cases:
- New endpoints or business logic added without corresponding unit/integration tests
- Untested edge cases (e.g. empty search query, invalid category, missing parameters, negative numbers)
- Lack of negative test cases (testing for 400 Bad Request or 404 Not Found)
- Potential unhandled exceptions (e.g. KeyError, NoneType attribute errors if db returns None)

Review the provided Git diff carefully.
For any real testing gaps you detect, create an AuditFinding with:
- category: "TEST_COVERAGE"
- severity: "HIGH" for completely untested critical endpoints, "MEDIUM" for missing edge cases
- line_start and line_end corresponding to the diff
- clear description and a recommended pytest/unittest test case outline.

If no testing gaps are found, return an empty findings list.
"""


def test_auditor_node(state: PRReviewState) -> dict:
    """
    LangGraph Node for the Test Auditor.
    Reads diff_content from state and returns newly discovered testing findings.
    """
    diff = state.get("diff_content", "")
    llm = get_structured_auditor_llm()

    messages = [
        {"role": "system", "content": TEST_SYSTEM_PROMPT},
        {"role": "user", "content": f"Pull Request Diff to review:\n\n{diff}"}
    ]

    result = llm.invoke(messages)
    findings = convert_findings_to_dicts(result.findings)

    print(f"[Test Auditor] Finished scan. Found {len(findings)} issue(s).")
    return {"audit_findings": findings}
