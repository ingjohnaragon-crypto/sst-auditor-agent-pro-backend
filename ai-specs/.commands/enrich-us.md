Please analyze and fix the Jira ticket: $ARGUMENTS.

Follow these steps:

1. The ticket's details (type, status, summary, assignee, description) are already provided above under `## Jira Ticket: $ARGUMENTS` — use that content as the source of truth. Do not attempt to fetch it again via Jira MCP or any other tool; none is available in this context.
2. You will act as a product expert with technical knowledge
3. Understand the problem described in the ticket
4. Decide whether or not the User Story is completely detailed according to product's best practices: Include a full description of the functionality, a comprehensive list of fields to be updated, the structure and URLs of the necessary endpoints, the files to be modified according to the architecture and best practices, the steps required for the task to be considered complete, how to update any relevant documentation or create unit tests, and non-functional requirements related to security, performance, etc
5. If the user story lacks the technical and specific detail necessary to allow the developer to be fully autonomous when completing it, provide an improved story that is clearer, more specific, and more concise in line with product best practices described in step 4. Use the technical context you will find in
@documentation. Return it in markdown format.
6. Do NOT update Jira yourself — do not call any Jira tool or MCP. Writing back to Jira is a separate, human-confirmed step handled by `os-enrich-apply` after you finish. Your only job here is to produce the markdown described below and save it to disk.
7. Do NOT transition the ticket's status. Status transitions are handled separately via `os-transition`, not as part of this task.
8. Look at the `## Subtasks` context block provided (fetched from Jira via `parent = <ticket-id>`). For each subtask listed there, apply the same detail bar as step 4: if its description lacks the technical specifics needed for autonomous implementation, write an enhanced version following step 5's criteria, scoped to that subtask. If a subtask is already sufficiently detailed, or if no subtasks exist, skip it — do not invent subtasks that aren't in the context block.

## Language for section headers (mandatory)

**All section headers in the saved file MUST be written in the Active Language**
(see `## Active Language` in the prompt). Do **not** copy English headers when the
active language is Spanish (or vice versa).

Use exactly these headers when Active Language is Spanish (`es`):

| Sección | Encabezado obligatorio |
|---|---|
| Título | `# Ticket enriquecido: <TICKET-ID> — <Summary>` |
| Descripción original | `## Descripción original` |
| Descripción mejorada | `## Descripción mejorada` |
| Criterios de aceptación | `## Criterios de aceptación` |
| Campos y endpoints | `## Campos y endpoints` |
| Archivos | `## Archivos a crear o modificar` |
| Pruebas | `## Casos de prueba unitarios` |
| No funcionales | `## Requisitos no funcionales` |
| Puntos de historia | `## Puntos de historia` |
| Subtareas | `## Subtareas` |

Use exactly these headers when Active Language is English (`en`):

| Section | Required header |
|---|---|
| Title | `# Enriched Ticket: <TICKET-ID> — <Summary>` |
| Original | `## Original Description` |
| Enhanced | `## Enhanced Description` |
| AC | `## Acceptance Criteria` |
| Fields | `## Fields & Endpoints` |
| Files | `## Files to Create or Modify` |
| Tests | `## Unit Test Cases` |
| NFR | `## Non-Functional Requirements` |
| Story points | `## Story Points` |
| Subtasks | `## Subtasks` |

## Output

Save the enriched content as a markdown file at `ai-specs/changes/enriquecimientos/$ARGUMENTS/$ARGUMENTS_enriched.md`
using this structure (headers in Active Language — Spanish example below):

---

```markdown
# Ticket enriquecido: <TICKET-ID> — <Summary>

## Descripción original
<!-- jira-skip -->
(copy of the original ticket description — kept for local archive only;
`os-enrich-apply` strips this block before uploading to Jira)
<!-- /jira-skip -->

## Descripción mejorada
Full description of the functionality as refined. Prefer short paragraphs and
bullet lists — this section is what developers read in Jira.

## Criterios de aceptación
- [ ] Criterion 1
- [ ] Criterion 2

## Campos y endpoints
Prefer bullet lists over wide markdown tables when possible (tables render poorly
in Jira). Include endpoint URLs, HTTP methods, and request/response shapes.

## Archivos a crear o modificar
- `path/to/file.ext` — Domain|Application|Presentation|Infrastructure — Create|Modify

## Casos de prueba unitarios
- Happy path
- Validation error
- Not found / Conflict
- Edge cases

## Requisitos no funcionales
Security, performance, validation constraints.

## Puntos de historia
<!-- STORY_POINTS:<N> -->
Estimate using Fibonacci (1, 2, 3, 5, 8, 13). One short justification line.
Example: **5** — pool + compose + Alembic flags + tests; no new endpoints.
<!-- /STORY_POINTS -->

## Subtareas
Only include this section if the `## Subtasks` context block lists at least one
subtask. Emit one block per subtask that needed refinement, wrapped in HTML comment
markers so `os-enrich-apply` can upload each one to its own Jira issue:

<!-- SUBTASK:<SUBTASK-KEY> -->
### Subtarea: <SUBTASK-KEY> — <Summary>

#### Descripción original
<!-- jira-skip -->
(copy)
<!-- /jira-skip -->

#### Descripción mejorada
Refined, technically detailed description.

#### Criterios de aceptación
- [ ] Criterion 1
- [ ] Criterion 2

#### Puntos de historia
<!-- STORY_POINTS:<N> -->
Fibonacci estimate for this subtask only.
<!-- /STORY_POINTS -->
<!-- /SUBTASK:<SUBTASK-KEY> -->
```

Repeat the block for every subtask that was refined. Subtasks that were already
sufficiently detailed are omitted from this section entirely.

### Jira readability rules
- Keep paragraphs short; prefer bullets over long walls of text.
- Avoid markdown tables when a bullet list conveys the same information.
- Put fenced code blocks only when an exact snippet/API shape is needed.
- Wrap archive-only content (original description, internal notes) in
  `<!-- jira-skip -->` … `<!-- /jira-skip -->` so it is **not** uploaded to Jira.

---

## Final message format

> Enriched content saved to `ai-specs/changes/enriquecimientos/<ticket-id>/<ticket-id>_enriched.md`.
> N subtask(s) will also be updated.
> Run `os-enrich-apply <TICKET-ID>` to upload it to Jira.
