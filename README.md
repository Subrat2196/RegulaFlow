# RegulaFlow

A production-grade, multi-agent regulatory intelligence and compliance automation platform.

## What It Does

RegulaFlow continuously ingests regulatory documents and internal policies, detects regulatory changes, retrieves relevant policy evidence, identifies compliance gaps, recommends remediation, and routes high-risk findings to human reviewers — all with end-to-end auditability.

## Architecture Overview

```
Regulatory Documents → Ingestion → Versioning → Chunking + Embedding
                                                        ↓
                                              Hybrid Search (FTS + pgvector + RRF)
                                                        ↓
                                              LangGraph Agent Workflow
                                           ┌──────────┴──────────┐
                                  Regulation Monitor   Policy Analyzer   Gap Detector
                                           └──────────┬──────────┘
                                              Deterministic Validator
                                                        ↓
                                              Severity Engine → HITL (if HIGH/CRITICAL)
                                                        ↓
                                              Audit Trail
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Pydantic v2 |
| Agents | LangGraph |
| Database | PostgreSQL + pgvector + FTS |
| Cache / Queue | Redis + Celery |
| LLM | OpenAI (abstracted behind ModelProvider interface) |
| Observability | Langfuse + OpenTelemetry |
| UI | Gradio |
| Infra | Docker Compose + GitHub Actions CI |

## Getting Started

```powershell
# 1. Clone the repo
git clone <repo-url>
cd RegulaFlow

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# 3. Install the project with dev dependencies
pip install -e ".[dev]"

# 4. Copy the environment template
cp .env.example .env
# Edit .env and fill in your values

# 5. Run the development server
uvicorn app.main:app --reload
```

## Project Status

Currently in active development — Session 1 of 49.

| Phase | Status |
|-------|--------|
| Phase 1: Engineering Foundation | 🚧 In Progress |
| Phase 2: Ingestion | ⏳ Planned |
| Phase 3: Retrieval | ⏳ Planned |
| Phase 4: Agent Workflow | ⏳ Planned |
| Phase 5: Durability | ⏳ Planned |
| Phase 6: Human-in-the-Loop | ⏳ Planned |
| Phase 7: Evaluation | ⏳ Planned |
| Phase 8: Security | ⏳ Planned |
| Phase 9: Observability | ⏳ Planned |
| Phase 10: Production Hardening | ⏳ Planned |
