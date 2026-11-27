import os

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
from .tools import (
    get_coder_diff,
    list_repo_files,
    read_repo_file,
    run_limited_command,
    write_code_file,
    write_coder_report,
    write_run_evidence,
    write_test_analysis_report,
    write_test_file,
)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
READ_TOOLS = [list_repo_files, read_repo_file]
CODER_TOOLS = [*READ_TOOLS, write_code_file, run_limited_command, write_coder_report]
TEST_ANALYST_TOOLS = [
    *READ_TOOLS,
    get_coder_diff,
    write_test_file,
    run_limited_command,
    write_test_analysis_report,
]

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
    description=(
        "Implements an approved plan on an isolated branch with bounded write "
        "and limited test execution tools."
    ),
    instruction=CODER_INSTRUCTION,
    tools=CODER_TOOLS,
    output_key="coder_report",
)

test_analyst_agent = LlmAgent(
    name="TestAnalystAgent",
    model=GEMINI_MODEL,
    description=(
        "Inspects coder changes, identifies negative/boundary/regression test gaps, "
        "and writes authorized tests without modifying application code."
    ),
    instruction=TEST_ANALYST_INSTRUCTION,
    tools=TEST_ANALYST_TOOLS,
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
