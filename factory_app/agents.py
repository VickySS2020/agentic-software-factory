from google.adk.agents.llm_agent import LlmAgent

from .prompts import (
    CODER_INSTRUCTION,
    EVIDENCE_INSTRUCTION,
    INTAKE_INSTRUCTION,
    PLANNER_INSTRUCTION,
    REVIEWER_INSTRUCTION,
    SECURITY_INSTRUCTION,
    TEST_ANALYST_INSTRUCTION,
)
from .tools import list_repo_files, read_repo_file, run_baseline_verification, write_run_evidence

GEMINI_MODEL = "gemini-3.8-flash"
READ_TOOLS = [list_repo_files, read_repo_file]

intake_agent = LlmAgent(
    name="IntakeAgent",
    model=GEMINI_MODEL,
    description="Analyzes a Change Request and determines whether it is ready for planning.",
    instruction=INTAKE_INSTRUCTION,
    tools=READ_TOOLS,
    output_key="intake_report",
)

planner_agent = LlmAgent(
    name="PlannerAgent",
    model=GEMINI_MODEL,
    description="Creates an implementation plan without changing code.",
    instruction=PLANNER_INSTRUCTION + "\n\nIntake report:\n{intake_report}",
    tools=READ_TOOLS,
    output_key="implementation_plan",
)

coder_agent = LlmAgent(
    name="CoderAgent",
    model=GEMINI_MODEL,
    description="Implements an approved plan. Write tooling is intentionally absent in starter.",
    instruction=CODER_INSTRUCTION,
    tools=READ_TOOLS,
    output_key="coder_report",
)

test_analyst_agent = LlmAgent(
    name="TestAnalystAgent",
    model=GEMINI_MODEL,
    description="Finds test gaps and interprets deterministic verification evidence.",
    instruction=TEST_ANALYST_INSTRUCTION,
    tools=[*READ_TOOLS, run_baseline_verification],
    output_key="test_analysis",
)

reviewer_agent = LlmAgent(
    name="ReviewerAgent",
    model=GEMINI_MODEL,
    description="Independent read-only software reviewer.",
    instruction=REVIEWER_INSTRUCTION,
    tools=READ_TOOLS,
    output_key="review_report",
)

security_agent = LlmAgent(
    name="SecurityAgent",
    model=GEMINI_MODEL,
    description="Independent read-only security reviewer.",
    instruction=SECURITY_INSTRUCTION,
    tools=READ_TOOLS,
    output_key="security_report",
)

evidence_agent = LlmAgent(
    name="EvidenceAgent",
    model=GEMINI_MODEL,
    description="Consolidates evidence without making the final release decision.",
    instruction=EVIDENCE_INSTRUCTION,
    tools=[*READ_TOOLS, write_run_evidence],
    output_key="evidence_summary",
)
