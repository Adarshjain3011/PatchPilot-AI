"""
Verification script to test your Gemini API connection and LangGraph readiness.
Run: python verify_setup.py
"""

import os
from dotenv import load_dotenv

# Load variables from .env
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

import sys

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

if not api_key or api_key == "your_gemini_api_key_here":
    print("[ERROR] Please paste your real Gemini API key into the .env file.")
    print("Open the .env file in your editor and set: GEMINI_API_KEY=AIzaSy...")
    exit(1)

print("[INFO] API Key detected. Testing Gemini connection with LangGraph...")

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import StateGraph, START, END
    from state import PRReviewState

    # Initialize Gemini model (gemini-2.5-flash is ultra fast and capable)
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.2
    )

    # Test an LLM ping
    response = llm.invoke("Respond with exactly: 'Gemini Copilot Ready'")
    print(f"[AI] Model Response: {response.content.strip()}")

    # Test compiling an empty StateGraph with our PRReviewState
    builder = StateGraph(PRReviewState)
    builder.add_node("noop", lambda state: {"status": "RUNNING"})
    builder.add_edge(START, "noop")
    builder.add_edge("noop", END)
    graph = builder.compile()

    print("[SUCCESS] LangGraph PRReviewState compiled successfully!")
    print("\n[VERIFIED] Setup is 100% verified! Ready for Step 2.")

except Exception as e:
    print(f"[ERROR] Verification failed: {e}")

