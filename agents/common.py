"""
agents/common.py

Shared utilities, Pydantic schemas, and structured LLM initialization
for all 4 specialized auditor agents.
"""

import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from state import AuditFinding

load_dotenv()


class AuditFindingModel(BaseModel):
    """Pydantic model ensuring Gemini outputs strictly typed audit findings."""
    id: str = Field(description="Unique ID for this finding, e.g. SEC-001, PERF-001")
    category: Literal["SECURITY", "PERFORMANCE", "TEST_COVERAGE", "ARCHITECTURE"] = Field(
        description="The domain of the finding"
    )
    severity: Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"] = Field(
        description="Severity level of the issue"
    )
    file_path: str = Field(description="Relative path of the affected file")
    line_start: int = Field(description="Start line number of the problematic code")
    line_end: int = Field(description="End line number of the problematic code")
    issue_title: str = Field(description="Concise headline of the problem")
    description: str = Field(description="Detailed explanation of the flaw and its potential impact")
    suggested_fix: Optional[str] = Field(
        default=None,
        description="Concrete recommended code fix or strategy"
    )


class AuditorOutput(BaseModel):
    """Container schema for the list of findings returned by an auditor."""
    findings: List[AuditFindingModel] = Field(
        default_factory=list,
        description="List of detected audit findings"
    )


def get_structured_auditor_llm(temperature: float = 0.1):
    """
    Returns a Gemini LLM configured with structured output.
    Guarantees the model response strictly adheres to the AuditorOutput schema.
    """
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Missing GEMINI_API_KEY in environment or .env file.")

    base_llm = ChatGoogleGenerativeAI(
        model="gemini-3.5-flash-lite",
        google_api_key=api_key,
        temperature=temperature
    )
    return base_llm.with_structured_output(AuditorOutput)


def convert_findings_to_dicts(model_findings: List[AuditFindingModel]) -> List[AuditFinding]:
    """Helper to convert Pydantic objects to dicts for LangGraph State."""
    return [finding.model_dump() for finding in model_findings]
