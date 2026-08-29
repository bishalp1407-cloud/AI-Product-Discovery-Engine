# AI Product Discovery Engine

> A production-grade AI-native platform that helps Product Managers transform customer feedback into evidence-backed product opportunities.

## Project Status

🚧 **Currently under active development**


# Vision

Build an AI-native Product Discovery Platform that enables Product Managers to:

* Collect customer feedback from multiple sources
* Normalize heterogeneous data into a unified schema
* Analyze feedback using Large Language Models (LLMs)
* Discover Jobs-to-be-Done (JTBD)
* Identify recurring pain points
* Perform semantic clustering
* Prioritize product opportunities
* Generate evidence-backed product recommendations

This project is **not** a chatbot or sentiment analysis tool. It is an AI-powered decision support system for product teams.

---

# Tech Stack

## Frontend

* Next.js
* TypeScript
* Tailwind CSS
* shadcn/ui

## Backend

* FastAPI
* Python

## Database *(Upcoming)*

* PostgreSQL
* pgvector

## AI *(Upcoming)*

* OpenRouter API

## Monitoring *(Upcoming)*

* Langfuse
* Sentry
* PostHog

---

# Repository Structure

```text
AI-Product-Discovery-Engine/

├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # Next.js frontend
│
├── docs/
│   ├── architecture/
│   ├── decisions/
│   ├── learning-notes/
│   ├── interview-preparation/
│   └── product/
│
├── infrastructure/
├── scripts/
└── .github/
```

---

# Local Development

## Backend

```bash
cd apps/api
.venv\Scripts\activate
python -m uvicorn app.main:app --reload
```

API Documentation:

```
http://127.0.0.1:8000/docs
```

Health Check:

```
http://127.0.0.1:8000/health
```

---

## Frontend

```bash
cd apps/web
npm run dev
```

Application:

```
http://localhost:3000
```

---

# Current Features

* FastAPI backend initialized
* Next.js frontend initialized
* Centralized configuration using `pydantic-settings`
* Environment variable management
* Centralized application logging
* Health endpoint
* Initial automated backend test
* Modular project structure

---

# Upcoming Milestones

* Database & Domain Model Design
* Feedback Ingestion Pipeline
* Data Cleaning & Normalization
* LLM Analysis Pipeline
* Embeddings & Semantic Search
* Semantic Clustering
* Opportunity Prioritization
* Product Discovery Dashboard
* Deployment & Observability

---

# Documentation

Project documentation is organized inside the `docs/` directory.

* Architecture
* Product Decisions
* Learning Notes
* Architecture Decision Records (ADRs)
* Interview Preparation

---

# License

This project is licensed under the MIT License.
