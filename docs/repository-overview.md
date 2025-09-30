# Repository Overview

This document provides a quick reference for the major components contained in the AutoGPT mono-repo.

## Platform Stack (`autogpt_platform/`)
- **backend/** – FastAPI service that powers the hosted platform APIs and integrates with Prisma and PostgreSQL.
- **autogpt_libs/** – Shared Python packages used by both the backend and supporting services.
- **frontend/** – Next.js + TypeScript client application for building and managing agents.
- **docker-compose.yml** – Local development stack for running the platform services together.

## Classic Agents (`classic/`)
- **forge/** – Toolkit and tutorials for building bespoke agents and benchmarking workflows.
- **benchmark/** – Evaluation harnesses used to measure agent performance.
- **frontend/** – React-based graphical interface for the classic AutoGPT experience.
- **run/** – Scripts and helpers for running the original AutoGPT CLI.

## Shared Assets and Documentation
- **docs/** – Source for the public documentation site, including platform and classic guides.
- **assets/** – Images and other media shared across documentation and marketing.
- **README.md** – High-level instructions for hosting options, licensing, and classic AutoGPT resources.
