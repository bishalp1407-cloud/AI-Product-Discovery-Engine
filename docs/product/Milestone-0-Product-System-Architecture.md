Milestone 0 --- Product & System Architecture

Project

DiscoveryOS --- An AI-native Product Discovery Platform

Demo Project: Blinkit (used as the initial reference implementation)

Vision

Build a production-quality AI Product Discovery Platform that helpsProduct Managers transform large volumes of customer feedback intoevidence-backed product opportunities.

This is not a chatbot or sentiment analysis tool. It is adecision-support system for AI-first product teams.

Product Goal

Enable Product Managers to:

Collect customer feedback from multiple sources

Normalize heterogeneous data into one schema

Analyze feedback using LLMs

Extract structured insights

Identify Jobs-to-be-Done (JTBD)

Detect pain points

Perform semantic clustering

Prioritize opportunities

Recommend evidence-backed product improvements

Explore results through a modern dashboard

Product Strategy

The platform is generic.

It is not built specifically for Blinkit, Spotify, Slack, or any singlecompany.

Instead, users create Projects inside the platform.

Example:

Blinkit

Spotify

Notion

Swiggy

Internal SaaS Product

Each project has its own feedback sources, insights, and opportunities.

Blinkit serves only as the first real-world dataset to validate thearchitecture.

Primary User

Product Managers

Product Analysts

UX Researchers

Customer Experience Teams

Job-to-be-Done

When I receive thousands of customer feedback items from multiplechannels, help me discover recurring unmet needs and prioritizeproduct opportunities with supporting evidence.

MVP Feedback Sources

Phase 1:

Google Play Reviews

Apple App Store Reviews

Reddit

YouTube Comments

Future phases:

G2

Capterra

Trustpilot

Product Hunt

Zendesk

Intercom

CSV Upload

Survey Platforms

Unified Feedback Philosophy

Every feedback source is converted into the same internal schema.

Common fields include:

project_id

source

author

rating

title

text

created_at

metadata

This allows downstream AI pipelines to remain source-agnostic.

Architecture Principles

Modular Monolith

Separation of Concerns

Deterministic logic before AI

Traceable AI outputs

Structured LLM responses

Human-in-the-loop decision support

High-Level Pipeline

Feedback Ingestion

Data Cleaning & Normalization

Unified Storage

LLM Analysis

Embedding Generation

Semantic Clustering

Insight Generation

Opportunity Prioritization

Dashboard Visualization

High-Level Technology Stack

Frontend: - Next.js - TypeScript - Tailwind CSS - shadcn/ui

Backend: - FastAPI - Python

Database: - PostgreSQL - pgvector

AI: - OpenRouter API

Monitoring: - Langfuse - Sentry - PostHog

Deployment: - GitHub - Vercel - Railway / Render

Why a Modular Monolith?

Advantages:

Simpler development

Easier debugging

Lower operational overhead

Clear module boundaries

Easy migration to microservices later

Microservices are intentionally postponed until scale requires them.

Development Philosophy

For every feature:

Product concept

AI concept

Engineering concept

Architecture

Production implementation

Code walkthrough

Interview preparation

Milestone Roadmap

Product & System Architecture

Repository Setup

Database & Unified Schema

Feedback Ingestion

Data Cleaning

LLM Analysis

Embeddings & Semantic Search

Semantic Clustering

JTBD & Insight Generation

Opportunity Prioritization

FastAPI APIs

Next.js Dashboard

Background Workers

Monitoring & Evaluation

Testing, Deployment & Documentation

Key Architectural Decisions

Build a reusable platform, not a Blinkit-specific application.

Use Blinkit as the first reference implementation.

Validate every milestone using real data.

Ensure adding a new product requires configuration rather than codechanges.

Interview Talking Points

Be able to explain:

Why not sentiment analysis?

Why modular monolith?

Why PostgreSQL + pgvector?

Why structured LLM outputs?

Why normalize all feedback?

Why use Blinkit only as a reference implementation?

How the platform scales to support multiple products and datasources?