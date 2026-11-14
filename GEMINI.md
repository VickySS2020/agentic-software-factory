# Coding Agent Guidance

Follow `AGENTS.md`.

This is a teaching repository. Preserve deliberate TODOs unless the current milestone requires implementing them.

Factory work:
- prefer current Google ADK patterns;
- prompts live in `factory_app/prompts.py`;
- deterministic tools live in `factory_app/tools.py`;
- preserve human gates.

CampusFlow work:
- business rules live in `campusflow/service.py`;
- persistence lives in repository code;
- HTTP adapters delegate to the service layer.
