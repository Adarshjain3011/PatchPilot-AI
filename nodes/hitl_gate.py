"""
nodes/hitl_gate.py

Human-in-the-Loop (HITL) Interrupt Gate:
1. Inspects the state produced by the Synthesizer.
2. If requires_approval == False:
     Passes through automatically.
3. If requires_approval == True:
     Calls LangGraph's native interrupt() function, freezing the workflow state
     in the checkpointer and waiting for human decision.
4. Resumes upon receiving Command(resume={"approved": bool, "instructions": str}).
"""

from langgraph.types import interrupt, Command
from state import PRReviewState


def hitl_gate_node(state: PRReviewState) -> dict:
    """
    HITL Interrupt Gate Node.
    Pauses graph execution when high-risk vulnerabilities are detected.
    """
    # If no high risk, auto-approve and advance
    if not state.get("requires_approval", False):
        print("\n[HITL Gate] Risk is LOW. Auto-approved without human intervention.")
        return {
            "human_approved": True,
            "human_instructions": None,
            "status": "REPAIRING"
        }

    print("\n" + "=" * 70)
    print("🛑 [HITL Gate] HIGH RISK DETECTED! Pausing workflow execution...")
    print("=" * 70)
    print(f"  • Risk Score    : {state.get('risk_score')}/100 ({state.get('risk_level')})")
    print(f"  • Total Findings: {len(state.get('audit_findings', []))}")
    print("  • Action        : Freezing state in checkpointer. Waiting for human approval...")
    print("=" * 70)

    # Freeze the graph and surface payload to the caller / dashboard
    decision = interrupt({
        "reason": "High-risk issues detected in Pull Request. Human approval required before repair.",
        "risk_score": state.get("risk_score"),
        "risk_level": state.get("risk_level"),
        "total_findings": len(state.get("audit_findings", [])),
        "options": ["APPROVE", "REJECT", "CUSTOM_INSTRUCTIONS"]
    })

    # When Command(resume=...) is passed to graph.invoke(), execution resumes right here!
    print("\n" + "=" * 70)
    print("🟢 [HITL Gate] Human Decision Received! Resuming workflow...")
    print("=" * 70)

    is_approved = decision.get("approved", False) if isinstance(decision, dict) else bool(decision)
    custom_instructions = decision.get("instructions") if isinstance(decision, dict) else None

    if is_approved:
        print(f"  • Decision    : ✅ APPROVED by human reviewer.")
        if custom_instructions:
            print(f"  • Directive   : 📝 \"{custom_instructions}\"")
        return {
            "human_approved": True,
            "human_instructions": custom_instructions,
            "status": "REPAIRING"
        }
    else:
        print("  • Decision    : ❌ REJECTED by human reviewer. Halting remediation.")
        return {
            "human_approved": False,
            "human_instructions": custom_instructions,
            "status": "REJECTED"
        }
