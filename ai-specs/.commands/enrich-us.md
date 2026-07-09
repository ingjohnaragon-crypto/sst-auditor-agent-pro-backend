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

## Output

Save the enriched content as a markdown file at `ai-specs/changes/enriquecimientos/$ARGUMENTS/$ARGUMENTS_enriched.md`
using this structure:

---

### `# Enriched Ticket: <TICKET-ID> — <Summary>`

### `## Original Description`
(copy of the original ticket description)

### `## Enhanced Description`
Full description of the functionality as refined.

### `## Acceptance Criteria`
- [ ] Criterion 1
- [ ] Criterion 2

### `## Fields & Endpoints`
Table or list of fields to create/update, endpoint URLs, HTTP methods,
request/response shapes.

### `## Files to Create or Modify`
| File | Layer | Action |
|---|---|---|
| `path/to/file.ext` | Domain / Application / Presentation / Infrastructure | Create / Modify |

### `## Unit Test Cases`
- Happy path
- Validation error
- Not found / Conflict
- Edge cases

### `## Non-Functional Requirements`
Security, performance, validation constraints.

### `## Subtasks`
Only include this section if the `## Subtasks` context block lists at least one
subtask. Emit one block per subtask that needed refinement, wrapped in HTML comment
markers so `os-enrich-apply` can upload each one to its own Jira issue:

```markdown
<!-- SUBTASK:<SUBTASK-KEY> -->
### Subtask: <SUBTASK-KEY> — <Summary>

#### Original Description
(copy of the subtask's current description)

#### Enhanced Description
Refined, technically detailed description matching the HU-level rigor from step 5.

#### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
<!-- /SUBTASK:<SUBTASK-KEY> -->
```

Repeat the block for every subtask that was refined. Subtasks that were already
sufficiently detailed are omitted from this section entirely.

---

## Final message format

> Enriched content saved to `ai-specs/changes/enriquecimientos/<ticket-id>/<ticket-id>_enriched.md`.
> N subtask(s) will also be updated.
> Run `os-enrich-apply <TICKET-ID>` to upload it to Jira.