"""Starter ADK root: safe read-only planning only."""

from google.adk.apps import App

from .workflows import planning_pipeline

# ADK expects the exported root agent to be named root_agent.
root_agent = planning_pipeline

# Agents CLI serving/eval wrapper. Name matches agent_directory.
app = App(root_agent=root_agent, name="factory_app")
