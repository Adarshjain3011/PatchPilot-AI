"""
test_parallel_auditors.py

Demonstrates parallel execution (fan-out and fan-in) in LangGraph.
1. START branches concurrently into 4 specialized auditor agents.
2. Each agent scans the PR diff independently for its domain.
3. LangGraph's 'operator.add' reducer automatically merges all findings into one list.
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

def build_parallel_audit_graph():
    """Builds and compiles the parallel multi-agent audit graph."""
    builder = StateGraph(PRReviewState)

    # 1. Register the 4 specialized auditor nodes
    builder.add_node("security_auditor", security_auditor_node)
    builder.add_node("performance_auditor", performance_auditor_node)
    builder.add_node("test_auditor", test_auditor_node)
    builder.add_node("architecture_auditor", architecture_auditor_node)

    # 2. Fan-Out: START triggers all 4 nodes simultaneously
    builder.add_edge(START, "security_auditor")
    builder.add_edge(START, "performance_auditor")
    builder.add_edge(START, "test_auditor")
    builder.add_edge(START, "architecture_auditor")

    # 3. Fan-In: All 4 nodes route to END (or next synthesizer step)
    builder.add_edge("security_auditor", END)
    builder.add_edge("performance_auditor", END)
    builder.add_edge("test_auditor", END)
    builder.add_edge("architecture_auditor", END)

    return builder.compile()

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 Starting Parallel Multi-Agent Code Audit with LangGraph")
    print("=" * 70)

    # Prepare initial state with the mock Git diff
    initial_state = {
        "pr_id": "PR-101",
        "repo_name": "enterprise/post-service",
        "diff_content": SAMPLE_PR_DIFF,
        "files_changed": ["backend/routes/posts.py"],
        "audit_findings": [],          # Will be populated by operator.add reducer
        "risk_score": 0,
        "risk_level": "LOW",
        "requires_approval": False,
        "human_approved": None,
        "human_instructions": None,
        "final_patch": None,
        "status": "RUNNING"
    }

    graph = build_parallel_audit_graph()

    start_time = time.time()
    final_state = graph.invoke(initial_state)
    elapsed = time.time() - start_time

    findings = final_state["audit_findings"]

    print("\n" + "=" * 70)
    print(f"📊 Audit Complete in {elapsed:.2f}s | Total Findings Combined: {len(findings)}")
    print("=" * 70)

    # Display findings grouped by category
    for idx, finding in enumerate(findings, 1):
        print(f"\n[{idx}] {finding['category']} ({finding['severity']}) - {finding['id']}")
        print(f"    File: {finding['file_path']} (Lines {finding['line_start']}-{finding['line_end']})")
        print(f"    Issue: {finding['issue_title']}")
        print(f"    Details: {finding['description']}")
        if finding.get("suggested_fix"):
            print(f"    Fix: {finding['suggested_fix'][:120]}...")
