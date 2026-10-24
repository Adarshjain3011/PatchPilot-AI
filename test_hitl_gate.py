"""
test_hitl_gate.py

Demonstrates Human-in-the-Loop (HITL) Interrupt & Resume in LangGraph:
1. START fans out to 4 parallel auditor agents.
2. The 'synthesizer' node aggregates findings and calculates risk (HIGH).
3. The 'hitl_gate' node executes interrupt(), pausing the workflow in checkpointer memory.
4. We inspect the snapshot to verify the graph is paused and waiting for human input.
5. We simulate human intervention by passing Command(resume={...}).
6. The graph resumes from the exact paused node with the human's directives!
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
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from state import PRReviewState
from sample_data.mock_diff import SAMPLE_PR_DIFF
from agents import (
    security_auditor_node,
    performance_auditor_node,
    test_auditor_node,
    architecture_auditor_node
)
from nodes import synthesizer_node, hitl_gate_node


def build_audit_with_hitl_graph(checkpointer: MemorySaver):
    """Builds the graph with checkpointer and HITL interrupt gate."""
    builder = StateGraph(PRReviewState)

    # 1. Register all nodes
    builder.add_node("security_auditor", security_auditor_node)
    builder.add_node("performance_auditor", performance_auditor_node)
    builder.add_node("test_auditor", test_auditor_node)
    builder.add_node("architecture_auditor", architecture_auditor_node)
    builder.add_node("synthesizer", synthesizer_node)
    builder.add_node("hitl_gate", hitl_gate_node)

    # 2. Fan-Out: START triggers all 4 auditors in parallel
    builder.add_edge(START, "security_auditor")
    builder.add_edge(START, "performance_auditor")
    builder.add_edge(START, "test_auditor")
    builder.add_edge(START, "architecture_auditor")

    # 3. Fan-In: All 4 auditors converge into the synthesizer
    builder.add_edge("security_auditor", "synthesizer")
    builder.add_edge("performance_auditor", "synthesizer")
    builder.add_edge("test_auditor", "synthesizer")
    builder.add_edge("architecture_auditor", "synthesizer")

    # 4. Route Synthesizer to HITL Gate
    builder.add_edge("synthesizer", "hitl_gate")

    # 5. Route from HITL Gate to END (in next step, this connects to the Repair Subgraph)
    builder.add_edge("hitl_gate", END)

    # Checkpointer is MANDATORY for interrupt() to persist graph state
    return builder.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 LangGraph Human-in-the-Loop (HITL) Interrupt & Resume Test")
    print("=" * 70)

    # 1. Initialize persistent memory checkpointer
    checkpointer = MemorySaver()
    graph = build_audit_with_hitl_graph(checkpointer)

    # Unique thread_id for this Pull Request review session
    thread_config = {"configurable": {"thread_id": "pr-thread-post-service-101"}}

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

    print("\n--- PHASE 1: Running Graph Until Interrupt ---")
    start_time = time.time()
    # This invocation will run until the interrupt() inside hitl_gate
    graph.invoke(initial_state, config=thread_config)
    elapsed = time.time() - start_time

    # 2. Check snapshot of the paused thread
    snapshot = graph.get_state(thread_config)
    print(f"\n[Checkpointer State] Graph execution paused after {elapsed:.2f}s!")
    print(f"  • Next scheduled node : {snapshot.next}")
    print(f"  • Paused Tasks Count  : {len(snapshot.tasks)}")
    
    for task in snapshot.tasks:
        if task.interrupts:
            print(f"  • Interrupt Payload   : {task.interrupts[0].value}")

    print("\n" + "-" * 70)
    print("🧑‍💻 SIMULATING HUMAN INTERACTION (e.g. Developer in Dashboard / Slack)")
    print("Reviewer Decision: 'APPROVE with instructions'")
    print("-" * 70)

    human_response = {
        "approved": True,
        "instructions": "Approved. Refactor using parameterized queries and move JWT_SECRET_KEY to os.environ."
    }

    # 3. Resume the graph using Command(resume=...)
    print("\n--- PHASE 2: Resuming Graph with Human Directives ---")
    final_state = graph.invoke(Command(resume=human_response), config=thread_config)

    print("\n" + "=" * 70)
    print("🎉 Graph Resumed and Completed Successfully!")
    print("=" * 70)
    print(f"  • Final Status       : {final_state['status']}")
    print(f"  • Human Approved     : {final_state['human_approved']}")
    print(f"  • Human Instructions : {final_state['human_instructions']}")
    print(f"  • Next Step Ready    : Ready for Self-Healing Repair Subgraph!")
    print("=" * 70)
