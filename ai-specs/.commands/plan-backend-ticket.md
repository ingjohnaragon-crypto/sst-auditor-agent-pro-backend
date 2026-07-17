# plan-backend-ticket

Ticket ID: $ARGUMENTS

## Goal
Generate a step-by-step backend implementation plan for a Jira ticket, ready to hand
off to a developer for autonomous implementation.

## Pre-flight checklist

1. Read `openspec/config.yaml` and resolve:
   - Active stack (`stack:` key)
   - Stack agent path and load it
   - Stack standards path and load it
   - Tooling commands: `build_command`, `test_command`, `run_command`, `coverage_command`
2. Read `ai-specs/specs/base-standards.mdc`
3. Read any existing plans under `ai-specs/changes/planes/` for related context
4. Fetch ticket details from Jira MCP (if available) or from a provided description

## Process

1. Adopt the role defined in the active stack agent
2. Analyze the ticket: identify affected layers (Domain, Application, Presentation, Infrastructure)
3. Propose the implementation plan following the output format below
4. **Always estimate Story Points** (Fibonacci: 1, 2, 3, 5, 8, 13) for the HU and for each mapped subtask
5. Save the plan at `ai-specs/changes/planes/<ticket-id>/<ticket-id>_backend.md`
6. **Do not write any implementation code — plan only**

## Language

Write the entire plan (including section headers) in the Active Language from the prompt.
When Active Language is Spanish, use headers like `# Plan de implementación backend: …`,
`## 1. Resumen`, `## Estimación de puntos de historia`, etc. Do not leave English headers
when the active language is `es`.

## Output format

Save a markdown file at `ai-specs/changes/planes/<ticket-id>/<ticket-id>_backend.md` with this structure
(English labels below — translate headers when Active Language is not English):

---

### `# Backend Implementation Plan: <TICKET-ID> <Feature Name>`

### `## 1. Overview`
Brief description of the feature and relevant architecture principles.
State the active stack.

### `## Story Points Estimate` / `## Estimación de puntos de historia` (mandatory)
Always include this section — never omit it.

```markdown
<!-- STORY_POINTS:<N> -->
- **HU total**: <N> (Fibonacci: 1, 2, 3, 5, 8, 13)
- **Justification**: one short paragraph (complexity, uncertainty, testing effort)
- **Subtasks** (if any):
  | Subtask | Points | Note |
  |---|---|---|
  | SP-XXX | 2 | … |
<!-- /STORY_POINTS -->
```

If the ticket already has story points in Jira, confirm or propose an adjustment with rationale.

### `## 2. Architecture Context`
- Active stack: `<stack>` (`<label>`)
- Layers involved and which files are affected per layer

### `### Subtask Mapping`
If the `## Subtasks` context block lists Jira subtasks, add a table mapping each
subtask to the Implementation Step(s) below that fulfill it:

| Subtask key | Summary | Implementation Step(s) |
|---|---|---|
| `<SUBTASK-KEY>` | `<summary>` | Step `<n>`, Step `<n>` |

If the context block reports no subtasks, write: "No subtasks — plan derived
directly from the HU."

### `## 3. Implementation Steps`

#### Step 0: Create Feature Branch
- **Action**: Create and switch to a new feature branch
- **Branch**: `feature/<ticket-id>-backend`
- **Commands**:
  ```bash
  git checkout main && git pull origin main
  git checkout -b feature/<ticket-id>-backend
  ```

#### Step 1: [Schema Migration — if needed]
- File: migration script path (stack-specific location)
- Content: SQL or migration DSL changes

#### Step 2: [Domain Entity / Model]
- File: domain model file path
- Changes: new fields, factory methods, domain methods

#### Step 3: [Repository Interface]
- File: repository interface path
- Changes: new methods required

#### Step 4: [DTOs]
- Files: request and response DTO paths
- Fields and validation rules

#### Step 5: [Service]
- File: service file path
- Method signature and business logic summary

#### Step 6: [Controller / Router / Handler]
- File: presentation layer file path
- HTTP method, path, request/response contract

#### Step 7: [Exception Handling]
- New domain exceptions and their HTTP mappings

#### Step 8: [Unit Tests]
- Test file paths
- Cases to cover: happy path, validation error, not found, conflict, edge cases

#### Step N: Update Technical Documentation
- `ai-specs/specs/data-model.md` — if schema changed
- `ai-specs/specs/api-spec.yml` — if endpoints changed
- Relevant standards file — if libraries or patterns changed

---

### `## 4. Implementation Order`
Numbered list of steps in sequence. Must start with Step 0 and end with documentation.

### `## 5. Testing Checklist`
Post-implementation verification:
- [ ] `{{test_command}}` passes with 0 failures
- [ ] `{{coverage_command}}` shows >= 90%
- [ ] All new endpoints manually tested (happy path + all error cases)
- [ ] Existing tests not broken

### `## 6. Tooling Reference`
Commands resolved from `openspec/config.yaml` for the active stack:

| Purpose | Command |
|---|---|
| Build | `{{build_command}}` |
| Test | `{{test_command}}` |
| Run | `{{run_command}}` |
| Coverage | `{{coverage_command}}` |

### `## 7. Error Response Format`
```json
{
  "success": false,
  "code": "ERROR_CODE",
  "message": "Human-readable description",
  "details": ["field: validation message"]
}
```
HTTP mapping: 400 VALIDATION_ERROR | 404 NOT_FOUND | 409 CONFLICT | 422 BUSINESS_RULE_VIOLATION | 500 INTERNAL_ERROR

### `## 8. Dependencies`
New libraries or tools required (if any), with install instructions for the active stack.

### `## 9. Notes`
Business rules, constraints, and important reminders.

### `## 10. Implementation Verification Checklist`
- [ ] Code quality: no compilation errors, linting passes, constructor injection used
- [ ] Domain: entities/models enforce invariants via factory methods
- [ ] Application: services use DTOs, delegate to repositories — no raw DB access
- [ ] Presentation: handlers are thin, all inputs validated before reaching service
- [ ] Migrations: schema changes applied via migration scripts, not ORM auto-migrate
- [ ] Tests: all green, coverage >= 90%, all HTTP status codes covered
- [ ] Documentation: data-model.md, api-spec.yml, and standards files updated

---

## Final message format

Your final message must include the plan file path:

> I've created a plan at `ai-specs/changes/planes/<ticket-id>/<ticket-id>_backend.md`.
> Please review it before proceeding with implementation.