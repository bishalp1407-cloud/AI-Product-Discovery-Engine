# AI Product Discovery Engine

**Turn scattered customer feedback into prioritized product opportunities.**

Product teams rarely have a shortage of customer feedback.

The harder problem is figuring out what actually deserves attention.

Reviews are spread across app stores, videos, support channels, communities, and other sources. Reading them manually works at a small scale, but as feedback grows, identifying recurring problems — and separating important signals from noise — becomes increasingly difficult.

I built the **AI Product Discovery Engine** to explore a simple question:

> **Can AI help Product Managers move from thousands of pieces of unstructured feedback to a smaller set of evidence-backed problems worth investigating?**

The result is a deployed end-to-end product that collects customer feedback, analyzes it using LLMs, groups semantically similar problems, and ranks recurring pain points for Product Managers.

---

## Live Product

**Dashboard:** http://ai-product-discovery-engine.vercel.app

**API:** https://ai-product-discovery-engine-production.up.railway.app

> The current deployment uses Blinkit customer feedback as the validation dataset.

---

## What the Product Does

Instead of asking a Product Manager to manually read hundreds of reviews, the engine turns raw feedback into a discovery pipeline:

```text
Customer Feedback
        ↓
Ingestion
        ↓
Cleaning & Normalization
        ↓
AI Analysis
        ↓
Problem Candidate Filtering
        ↓
Embeddings
        ↓
Semantic Clustering
        ↓
Opportunity Prioritization
        ↓
Evidence-backed Product Insights
```

Today, the system can ingest feedback from:

- Google Play
- Apple App Store
- YouTube

The architecture is designed so additional sources can be introduced later.

---

## From Feedback to Product Opportunity

Imagine customers write:

> “Delivery charges have become way too expensive.”

> “The delivery fee makes small orders not worth it anymore.”

> “Extra delivery charges are getting ridiculous.”

These reviews are different sentences, but they may describe the **same underlying customer problem**.

The engine converts feedback into embeddings and compares semantic similarity.

Related feedback is grouped into recurring problem clusters rather than treated as isolated complaints.

Those clusters then become potential product opportunities.

---

## How Prioritization Works

Finding recurring complaints isn't enough.

A Product Manager still needs to answer:

> **Which problem should I investigate first?**

The MVP uses a prioritization framework based on:

**Opportunity Score = Reach × Impact × Confidence**

Where:

- **Reach** — how frequently the problem appears
- **Impact** — how severe the underlying customer problem appears
- **Confidence** — how strong and coherent the supporting evidence is

This is intentionally a **problem-prioritization score**, not a feature-prioritization score.

The engine is deciding which customer problems deserve investigation — not automatically deciding what should be built.

---

## A Product Decision I Had to Make

One of the interesting challenges was deciding:

> **How similar should two pieces of feedback be before we consider them the same problem?**

The current semantic clustering pipeline uses a configurable similarity threshold of **0.62**.

A lower threshold produced broader clusters but increased the risk of combining different problems.

A higher threshold produced more precise clusters but could fragment the same underlying problem across multiple clusters.

For the current Blinkit validation dataset, **0.62 provided a useful MVP balance between cluster cohesion and fragmentation.**

It is deliberately configurable rather than treated as a universal threshold.

This is something I would continue evaluating with larger datasets and human PM feedback.

---

## Evidence Before Recommendations

One design principle behind the product is:

> **AI-generated insights should be inspectable.**

The dashboard therefore doesn't just tell a PM:

> “Delivery pricing is a major customer problem.”

Each insight can be traced back to the customer feedback supporting it.

This allows the PM to inspect the evidence before deciding whether the problem deserves deeper discovery.

AI assists the decision.

It doesn't replace the Product Manager.

---

## Product Experience

The dashboard provides:

- Project-level feedback overview
- Source distribution
- Relevant vs. non-relevant feedback analysis
- Ranked customer pain points
- Opportunity scores
- Insight-level supporting evidence
- Recent customer feedback
- Manual data synchronization
- Persistent sync status across sessions

[Add dashboard screenshot]

[Add insight-detail screenshot]

---

## Architecture

```text
Google Play ─┐
App Store ───┼──→ Ingestion
YouTube ─────┘
                  ↓
             Normalization
                  ↓
              PostgreSQL
                  ↓
             LLM Analysis
                  ↓
          Problem Filtering
                  ↓
              Embeddings
                  ↓
        Semantic Clustering
                  ↓
     Opportunity Prioritization
                  ↓
          Insight Generation
                  ↓
               FastAPI
                  ↓
          Next.js Dashboard
```

The product is built as a monorepo with the frontend and backend separated so that AI processing and data orchestration remain server-side while the frontend focuses on the product experience.

---

## Tech Stack

### Product

**Frontend**
- Next.js
- TypeScript
- Tailwind CSS

**Backend**
- FastAPI
- Python
- SQLAlchemy
- Alembic

**Data**
- PostgreSQL
- pgvector

**AI**
- OpenRouter
- Sentence Transformers
- LLM structured analysis
- Semantic embeddings

### Deployment

- Vercel — frontend
- Railway — backend
- Neon — PostgreSQL

---

## Reliability Lessons

Building the product beyond a local prototype exposed several problems that weren't obvious during initial development.

For example, sync jobs were initially stored in application memory.

That worked locally.

But when the production API process restarted, the frontend could lose track of an active synchronization job.

Sync state was therefore moved into PostgreSQL so job status could survive process restarts.

Other reliability work included:

- feedback deduplication
- duplicate evidence protection
- LLM provider retry handling
- persistent sync jobs
- stale-job recovery
- duplicate sync protection
- cross-session sync-state recovery

These were useful reminders that getting an AI pipeline to **work once** and turning it into a **usable product** are very different problems.

---

## What I Learned Building This

This project started as an experiment around customer-feedback analysis and eventually became an exploration of **AI-native product discovery**.

Some of the questions I had to work through were:

- What feedback should actually count as a product problem?
- How do you distinguish recurring problems from isolated complaints?
- How much semantic similarity is enough to represent the same problem?
- How should AI confidence influence prioritization?
- How do you prevent positive feedback from contaminating pain-point ranking?
- How much evidence should an AI-generated insight expose?
- What happens when an LLM provider fails halfway through processing?
- What happens when a production process restarts during a long-running AI job?
- Where should AI make decisions, and where should the Product Manager remain in control?

Those decisions became as important to the project as the implementation itself.

---

## What I'd Build Next

The current version proves the core feedback → opportunity workflow.

The next iteration would focus less on adding AI features and more on validating whether the resulting insights actually improve Product Manager decision-making.

Areas I'd explore include:

- PM feedback on cluster quality
- human validation of AI-generated opportunities
- configurable prioritization models
- additional feedback sources
- team collaboration
- longitudinal problem tracking
- cluster evolution over time
- improved observability
- scheduled ingestion
- durable background workers for long-running AI jobs

---

## Repository Structure

```text
AI-Product-Discovery-Engine/

├── apps/
│   ├── api/          # FastAPI backend
│   └── web/          # Next.js frontend
│
├── docs/             # Product + architecture documentation
├── infrastructure/
├── scripts/
└── .github/
```

---

## Running Locally

### Backend

```bash
cd apps/api
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd apps/web
npm install
npm run dev
```

Application:

```text
http://localhost:3000
```

Environment variables required for the API and web application are documented in the respective `.env.example` files.

---

## Why I Built This

I'm a Computer Science graduate moving into Product Management, and I wanted to go beyond creating another static PM case study.

I wanted to take a product problem through:

**Problem framing → product decisions → AI architecture → MVP → testing → production deployment**

AI-assisted development was used extensively during implementation, while I focused on understanding and making the product, architecture, prioritization, validation, and reliability decisions behind the system.

The goal wasn't to demonstrate that AI can generate code.

It was to understand:

> **How far can a Product Manager take an idea when AI dramatically reduces the cost of building and testing it?**

---

## License

MIT