# Project: Dify-Agentic-Heal
## Core Mission
Eliminate "Vector Poisoning" caused by Schema Drift in Dify RAG pipelines. 
We follow a **Zero-Trust** architecture: Deterministic Validation (Python) + Probabilistic Remediation (Agent) + Human Verification (HITL).

## Technical Standards
- **Validation:** Use Pydantic V2 for strict type-safety and JSON diffing.
- **Dify Version:** v1.13.0 (targeting native Human Input Nodes).
- **Security:** Python nodes must be pure logic; external calls go through HTTP nodes or specific Sandbox images.
- **Performance:** Optimize for token efficiency. Only use LLMs when the "Sentinel" catches a drift.

## Team Roles
- Principal: Architect & Coordinator.
- Sentinel-Eng: Pydantic & Data Contracts specialist.
- Reasoning-Agent: Prompt Engineering & Mapping specialist.
- Infra-Healer: Dify API & Transformation specialist.