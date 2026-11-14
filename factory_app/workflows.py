from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from .agents import (
    intake_agent,
    planner_agent,
    reviewer_agent,
    security_agent,
)

# M1 slice: read-only planning pipeline used by the ADK web UI / eval harness.
# Human gates and the VerificationGate are NOT ADK agents; they are enforced
# by scripts/run_factory.py between pipeline stages.
planning_pipeline = SequentialAgent(
    name="PlanningPipeline",
    description="Read-only Intake -> Planning phase.",
    sub_agents=[intake_agent, planner_agent],
)

# M3 parallel review (Reviewer + Security are independent and read-only).
independent_review_pipeline = ParallelAgent(
    name="IndependentReviewPipeline",
    description="Runs software review and security review independently.",
    sub_agents=[reviewer_agent, security_agent],
)

