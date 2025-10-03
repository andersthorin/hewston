# ADR-002: Frontend TypeScript Path Aliases & Boundary Enforcement

Date: 2025-10-03
Status: Proposed
Decision Type: Frontend/Tooling

## Context
The frontend codebase organizes code by layers (components, services, utils, etc.) and relies on relative imports. Tests are partially co-located, and integration tests live in various places. No TS path aliases are defined, making boundary enforcement and refactoring harder.

## Decision
Introduce TypeScript path aliases and define import/boundary rules to support component- and feature-centric structure. Establish the principle that UI components remain "dumb" (presentational) and depend on externalized, modular logic.

### Aliases (tsconfig.app.json)
- @components/* -> src/components/*
- @features/* -> src/features/*
- @utils/* -> src/utils/*
- @services/* -> src/services/*

### Boundary Rules
- Components are presentational ("dumb components"): 
  - Stateless or local-UI-state only; receive data and callbacks via props.
  - No direct data-fetching, global state management, or cross-feature knowledge.
  - Logic is externalized to hooks (e.g., useXyz), containers, or service modules.
- Features expose a public surface via index.ts. Cross-feature imports must go through this surface (no deep imports).
- Prefer test colocation: Component.test.tsx next to the component.

### ESLint (proposal)
Adopt an ESLint configuration (e.g., eslint-plugin-boundaries or custom rules) to:
- Disallow deep imports across features.
- Enforce usage of @components/@features aliases for cross-tree imports.
- Flag components that import services directly (except via injected props/hook abstractions).

## Rationale
- Aliases stabilize imports and simplify refactors.
- Explicit boundaries encourage modular design and make code more testable.
- "Dumb" components improve reusability and limit blast radius of changes.

## Consequences
- Requires updating imports to use aliases.
- Minor learning curve for contributors; payback in maintainability and velocity.

## Alternatives Considered
- Continue with relative imports: rejected due to fragility and lack of boundary enforcement.

## Implementation Notes (Pilot)
- Add aliases; migrate a representative component (RunsTable) to component directory with barrel export.
- Create a sample container/hook that orchestrates logic and injects props into RunsTable.

