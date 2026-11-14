from google.adk.agents.parallel_agent import ParallelAgent
from google.adk.agents.sequential_agent import SequentialAgent

from .agents import intake_agent, planner_agent, reviewer_agent, security_agent

planning_pipeline = SequentialAgent(
    name="PlanningPipeline",
    description="Read-only Intake -> Planning phase.",
    sub_agents=[intake_agent, planner_agent],
)

independent_review_pipeline = ParallelAgent(
    name="IndependentReviewPipeline",
    description="Runs software review and security review independently.",
    sub_agents=[reviewer_agent, security_agent],
)
