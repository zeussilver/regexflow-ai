# Phase 5 Transformations Lead Preflight

## Scope

Implement Phase 5 only:
- PII Redaction Assistant
- Phone number normalization

## Out of Scope

- final UI polish
- deployment
- demo video
- authentication
- README beautification
- large-file streaming
- spreadsheet editing
- full workflow builder
- LLM-based direct table rewriting

## Branches And Worktrees

| Role | Branch | Worktree |
|---|---|---|
| Integration | `phase5-transformations` | `/Users/liuzhenqian/Desktop/worktrees/phase5-transformations-integration` |
| W1A Backend | `phase5-transformations-w1a-backend` | `/Users/liuzhenqian/Desktop/worktrees/phase5-transformations-w1a-backend` |
| W1B Frontend | `phase5-transformations-w1b-frontend` | `/Users/liuzhenqian/Desktop/worktrees/phase5-transformations-w1b-frontend` |
| W1C Tests | `phase5-transformations-w1c-tests` | `/Users/liuzhenqian/Desktop/worktrees/phase5-transformations-w1c-tests` |

## Guardrails

- Do not let the LLM rewrite table data.
- Do not send full tables to the LLM.
- Do not implement final polish or unrelated UI redesign.
- Do not add authentication, deployment, README beautification, streaming, spreadsheet editing, workflow builder, or direct table rewriting.
- Do not commit secrets.
- Preserve the pre-existing main worktree user changes: deleted `checklist.md` and untracked `docs/Phase5.md`.

## Validation Commands

- `python manage.py test apps.transformations apps.regex_engine apps.files`
- `npm run build`

## Merge Order

1. W1A backend implementation
2. W1C backend tests
3. W1B frontend implementation
