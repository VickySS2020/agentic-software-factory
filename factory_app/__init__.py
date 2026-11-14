# Lazy import: do not import root_agent at package level.
# Tests that import factory_app.tools must not trigger the ADK agent graph.
# The ADK CLI / App entrypoint imports agent.py directly.

