
"""
state.py

This file defines the data that our PR Copilot stores and shares
while reviewing and repairing a GitHub Pull Request (PR).

Think of "State" as a shared notebook:
- Every graph node can read the information it needs.
- A node can return updates to the state.
- LangGraph saves and manages these updates as the workflow runs.

This file defines three main data structures:

1. AuditFinding:
   Describes ONE problem found while checking the code.

2. PRReviewState:
   Stores information about the ENTIRE PR review workflow.

3. RepairSubgraphState:
   Stores information used inside the smaller repair workflow,
   where the AI generates a patch, runs tests, and tries to fix failures.
"""

from typing import Annotated, List, Optional, Literal
from typing_extensions import TypedDict
import operator


# ============================================================
# 1. AUDIT FINDING
# ============================================================
#
# What does "audit" mean?
# Audit means carefully checking something to find problems.
#
# What does "finding" mean?
# A finding is something discovered during that check.
#
# Therefore, AuditFinding means one specific problem discovered
# by an auditor while checking the code.
#
# Example:
# The Security Auditor finds that a SQL query may be vulnerable
# to SQL injection. It returns that problem using this structure.
#
# All auditors use the same structure so that the rest of our
# application can handle their results in a consistent way.


class AuditFinding(TypedDict):

    # A unique ID for this finding.
    # Example: "SEC-001"
    # This helps us identify and track an issue.
    id: str

    # The type of problem that was found.
    #
    # SECURITY:
    # A possible vulnerability or security weakness.
    #
    # PERFORMANCE:
    # Code that may be slow or use too many resources.
    #
    # TEST_COVERAGE:
    # Important code that may not have enough tests.
    #
    # ARCHITECTURE:
    # A problem with the code's design or structure.
    #
    # Literal lists the allowed values for type checkers.
    # It does not automatically validate values at runtime.
    category: Literal[
        "SECURITY",
        "PERFORMANCE",
        "TEST_COVERAGE",
        "ARCHITECTURE",
    ]

    # How serious is the problem?
    #
    # CRITICAL: Extremely serious; immediate attention may be needed.
    # HIGH:      A serious problem that should be fixed soon.
    # MEDIUM:    A problem that should be addressed.
    # LOW:       A smaller problem or improvement.
    #
    # These descriptions are examples of how our application
    # might interpret severity; we must define the exact policy.
    severity: Literal[
        "CRITICAL",
        "HIGH",
        "MEDIUM",
        "LOW",
    ]

    # The path of the file containing the problem.
    # Example: "backend/routes.py"
    file_path: str

    # The first line where the problem appears.
    # Example: 42
    line_start: int

    # The last line associated with the problem.
    # Example: 45
    line_end: int

    # A short title explaining the problem.
    # Example: "Possible SQL injection"
    issue_title: str

    # A longer explanation of what is wrong and why it matters.
    # Example: "User input is added directly to an SQL query."
    description: str

    # The suggested way to fix the problem.
    #
    # It can be a string if the auditor has a useful suggestion,
    # or None if it cannot confidently suggest a fix.
    #
    # Optional[str] means "string or None".
    # The key itself is still expected in this TypedDict.
    suggested_fix: Optional[str]


# ============================================================
# 2. MAIN GRAPH STATE: PRReviewState
# ============================================================
#
# This is the main state for the complete PR review workflow.
#
# It carries information from the beginning of the review
# until the workflow finishes.
#
# The workflow might:
# 1. Read a GitHub PR.
# 2. Run multiple auditors in parallel.
# 3. Combine their findings.
# 4. Calculate the risk.
# 5. Ask a human for approval.
# 6. Start the repair workflow.
# 7. Store the final result.
#
# Every node can read the state and return the fields it updates.
# LangGraph manages the updates according to each field's rules.


class PRReviewState(TypedDict):

    # --------------------------------------------------------
    # A. PULL REQUEST INFORMATION
    # --------------------------------------------------------

    # The ID or number of the pull request being reviewed.
    # Example: "PR-101" or "101", depending on our application.
    pr_id: str

    # The name of the GitHub repository.
    # Example: "my-company/backend"
    repo_name: str

    # The code changes in the pull request.
    #
    # A diff shows what was removed and what was added.
    # For example:
    # - old code that was removed
    # + new code that was added
    #
    # Auditors read this information to understand the changes.
    diff_content: str

    # A list of file paths changed in this pull request.
    # Example: ["backend/routes.py", "backend/auth.py"]
    #
    # This helps us identify which files need to be reviewed
    # and which files may be relevant to a repair.
    files_changed: List[str]

    # --------------------------------------------------------
    # B. FINDINGS FROM PARALLEL AUDITORS
    # --------------------------------------------------------

    # This list stores all the problems discovered by our auditors.
    #
    # Annotated tells LangGraph to use operator.add as the reducer.
    #
    # A reducer tells LangGraph HOW to combine updates when
    # multiple nodes write to the same state field in one graph step.
    #
    # operator.add combines lists by joining their contents.
    #
    # Example:
    # Security Auditor returns:    [finding_1, finding_2]
    # Performance Auditor returns: [finding_3]
    #
    # The combined list contains:
    # [finding_1, finding_2, finding_3]
    #
    # Each auditor should return only its OWN new findings.
    # Do not return the entire existing list again, because the
    # reducer would append those old findings again and create duplicates.
    #
    # The reducer does not automatically remove duplicate issues.
    # The synthesizer should handle duplicate findings later.
    #
    # Important:
    # The reducer combines updates to this field only.
    audit_findings: Annotated[
        List[AuditFinding],
        operator.add,
    ]

    # --------------------------------------------------------
    # C. OVERALL RISK ASSESSMENT
    # --------------------------------------------------------

    # A numerical score representing the risk found in this PR.
    #
    # Our application intends to use a score from 0 to 100.
    # Example: 85 might represent a very risky PR.
    #
    # We must implement and validate the 0-100 rule ourselves.
    # The int type alone does not enforce this range.
    risk_score: int

    # A human-readable risk category based on our risk policy.
    #
    # Example:
    # risk_score = 85
    # risk_level = "CRITICAL"
    #
    # The synthesizer must decide which scores belong to
    # LOW, MEDIUM, HIGH, and CRITICAL.
    risk_level: Literal[
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]

    # Tells the workflow whether a human must review the result
    # before the next protected action can happen.
    #
    # True:  Human approval is required.
    # False: Approval is not required by this particular rule.
    #
    # This field alone does not pause the graph.
    # We must add graph logic that checks this value.
    requires_approval: bool

    # --------------------------------------------------------
    # D. HUMAN-IN-THE-LOOP (HITL)
    # --------------------------------------------------------

    # Stores the human reviewer's decision.
    #
    # None:  No decision has been made yet.
    # True:  The reviewer approved the requested action.
    # False: The reviewer rejected the requested action.
    #
    # Our graph must check this value before proceeding.
    # The approval must also be tied to the specific action
    # being approved, such as repairing code.
    human_approved: Optional[bool]

    # Extra instructions provided by the human reviewer.
    #
    # Example:
    # "Fix the SQL injection and add a regression test."
    #
    # If the reviewer provides no instructions, this is None.
    human_instructions: Optional[str]

    # --------------------------------------------------------
    # E. REPAIR RESULT
    # --------------------------------------------------------

    # Stores the final patch produced by the repair workflow.
    #
    # A patch is a set of code changes that can be applied
    # to the original code.
    #
    # None means no final patch has been produced or returned.
    #
    # For a large project, we may store the patch in artifact
    # storage and keep its ID here instead of storing the full text.
    final_patch: Optional[str]

    # --------------------------------------------------------
    # F. OVERALL WORKFLOW STATUS
    # --------------------------------------------------------

    # Tells us the current overall stage of the PR review.
    #
    # RUNNING:
    # The workflow is running.
    #
    # WAITING_APPROVAL:
    # The workflow is waiting for a human decision.
    #
    # REPAIRING:
    # The repair workflow is working on the code.
    #
    # SUCCESS:
    # The workflow reached its defined success condition.
    #
    # REJECTED:
    # A human rejected the requested action.
    #
    # FAILED:
    # The workflow failed and could not continue successfully.
    #
    # We must explicitly update this field in our graph nodes.
    # LangGraph does not automatically change status strings.
    #
    # In a production system, verification and publication
    # may need separate status fields.
    status: Literal[
        "RUNNING",
        "WAITING_APPROVAL",
        "REPAIRING",
        "SUCCESS",
        "REJECTED",
        "FAILED",
    ]


# ============================================================
# 3. REPAIR SUBGRAPH STATE: RepairSubgraphState
# ============================================================
#
# The repair subgraph is a smaller workflow inside the main graph.
#
# Its job is to:
# 1. Read the issues that need fixing.
# 2. Generate a code patch.
# 3. Apply the patch in a restricted environment.
# 4. Run tests.
# 5. If tests fail, understand the failure and try again.
# 6. Stop when the repair succeeds or the retry limit is reached.
#
# This state stores the information needed by that smaller workflow.
#
# Defining a separate state schema helps organize the code.
# It does not, by itself, guarantee independent checkpoint history.
# Checkpoint behavior depends on how the graph is compiled and run.


class RepairSubgraphState(TypedDict):

    # --------------------------------------------------------
    # A. FILES AND ISSUES TO REPAIR
    # --------------------------------------------------------

    # The files that the repair agent is expected to modify.
    #
    # Example:
    # ["backend/routes.py", "tests/test_routes.py"]
    #
    # This gives the repair agent a clear scope.
    # Our application must still check the actual patch to make
    # sure it does not change files outside the allowed scope.
    target_files: List[str]

    # The audit findings that this repair operation should address.
    #
    # The parent graph can pass relevant findings into this state.
    # The repair agent uses them to understand what must be fixed.
    findings: List[AuditFinding]

    # Extra instructions from the human reviewer.
    #
    # Example:
    # "Use parameterized queries and add regression tests."
    #
    # None means no additional instructions were provided.
    custom_instructions: Optional[str]

    # --------------------------------------------------------
    # B. PATCH BEING TESTED
    # --------------------------------------------------------

    # The latest patch generated by the repair agent.
    #
    # The repair workflow can replace this value when it generates
    # a new patch after learning from a failed test.
    #
    # None means no patch has been generated yet.
    current_patch: Optional[str]

    # --------------------------------------------------------
    # C. RETRY CONTROL
    # --------------------------------------------------------

    # Tracks the current repair attempt.
    #
    # For example:
    # 0 = no attempt has started yet
    # 1 = first attempt
    # 2 = second attempt
    #
    # Our graph nodes must update this number consistently.
    attempt_count: int

    # The maximum number of repair attempts we allow.
    #
    # Example: 3 means the workflow should not make more than
    # three repair attempts under our chosen counting rule.
    #
    # We must implement this limit in the conditional routing logic.
    max_attempts: int

    # --------------------------------------------------------
    # D. TEST RESULTS
    # --------------------------------------------------------

    # Records whether the latest relevant test run passed.
    #
    # True:  The test run passed.
    # False: The test run failed or has not yet passed.
    #
    # This simple boolean does not distinguish between
    # "not run yet" and "failed". For more detailed workflows,
    # we could use a separate test status field.
    #
    # Passing tests alone does not prove that the code is secure.
    test_passed: bool

    # Normal output produced by the test process.
    #
    # Example:
    # "10 tests passed"
    #
    # This helps us understand what happened during the test run.
    test_stdout: str

    # Error output produced by the test process.
    #
    # Example:
    # "AssertionError: expected 400, got 500"
    #
    # The diagnosis node can inspect this output to understand
    # why a test failed.
    test_stderr: str

    # --------------------------------------------------------
    # E. FAILURE DIAGNOSIS
    # --------------------------------------------------------

    # A simple explanation of why the current repair or test failed.
    #
    # Example:
    # "The invalid-input case raises an unhandled exception."
    #
    # The repair agent can use this information to improve
    # the next patch instead of repeating the same mistake.
    #
    # None means no diagnosis has been recorded.
    error_diagnosis: Optional[str]


