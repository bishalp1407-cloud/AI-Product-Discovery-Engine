# ADR-001: Use a Monorepo

## Status

Accepted

## Context

The product includes a Next.js frontend, FastAPI backend, documentation, deployment configuration, and future shared resources.

## Decision

Store all product components inside one Git repository using an `apps`-based monorepo structure.

## Reasons

- Keeps frontend and backend changes synchronized
- Simplifies portfolio presentation
- Centralizes documentation
- Supports shared CI/CD workflows
- Reduces repository-management overhead

## Alternatives considered

### Separate repositories

Separate frontend and backend repositories provide stronger isolation but increase coordination, versioning, and documentation overhead.

### Backend-only repository

A backend-only repository would reduce initial complexity but would not represent the full product experience.

## Consequences

The repository requires clear module boundaries and consistent naming. Individual services may later be extracted if system scale or team ownership demands it.