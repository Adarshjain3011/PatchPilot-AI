"""
test_synthesizer.py

Demonstrates Fan-In Synchronization in LangGraph:
1. START fans out to 4 parallel auditor agents.
2. The graph pauses at the 'synthesizer' node until ALL 4 agents finish.
3. The 'synthesizer' fan-in node combines findings, deduplicates issues,
   calculates the composite risk score, and flags whether human approval is required.
"""

import sys
import time

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from langgraph.graph import StateGraph, START, END
from state import PRReviewState
from sample_data.mock_diff import SAMPLE_PR_DIFF
from agents import (
    security_auditor_node,
    performance_auditor_node,
    test_auditor_node,
    architecture_auditor_node
)
from nodes import synthesizer_node


def build_audit_and_synthesis_graph():
    """Builds the parallel fan-out and fan-in synthesis graph."""
    builder = StateGraph(PRReviewState)

    # 1. Register Nodes
    builder.add_node("security_auditor", security_auditor_node)
    builder.add_node("performance_auditor", performance_auditor_node)
    builder.add_node("test_auditor", test_auditor_node)
    builder.add_node("architecture_auditor", architecture_auditor_node)
    builder.add_node("synthesizer", synthesizer_node)

    # 2. Fan-Out: START triggers all 4 auditors concurrently
    builder.add_edge(START, "security_auditor")
    builder.add_edge(START, "performance_auditor")
    builder.add_edge(START, "test_auditor")
    builder.add_edge(START, "architecture_auditor")

    # 3. Fan-In: All 4 auditors converge into the 'synthesizer' node
    # LangGraph guarantees that 'synthesizer' will NOT execute until
    # all 4 parallel auditors have completed.
    builder.add_edge("security_auditor", "synthesizer")
    builder.add_edge("performance_auditor", "synthesizer")
    builder.add_edge("test_auditor", "synthesizer")
    builder.add_edge("architecture_auditor", "synthesizer")

    # 4. Route from Synthesizer to END (or next: HITL gate)
    builder.add_edge("synthesizer", END)

    return builder.compile()


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Running Parallel Multi-Agent Audit + Fan-In Synthesizer")
    print("=" * 70)

    initial_state = {
        "pr_id": "PR-101",
        "repo_name": "enterprise/post-service",
        "diff_content": SAMPLE_PR_DIFF,
        "files_changed": ["backend/routes/posts.py"],
        "audit_findings": [],
        "risk_score": 0,
        "risk_level": "LOW",
        "requires_approval": False,
        "human_approved": None,
        "human_instructions": None,
        "final_patch": None,
        "status": "RUNNING"
    }

    graph = build_audit_and_synthesis_graph()

    start_time = time.time()
    final_state = graph.invoke(initial_state)
    elapsed = time.time() - start_time

    print(f"\n✨ Execution Completed in {elapsed:.2f} seconds!")
    print(f"Final PR State:")
    print(f"  • Status             : {final_state['status']}")
    print(f"  • Risk Score         : {final_state['risk_score']}/100")
    print(f"  • Risk Level         : {final_state['risk_level']}")
    print(f"  • Requires Approval  : {final_state['requires_approval']}")
    print(f"  • Total Findings in State: {len(final_state['audit_findings'])}")
