# Role

You are an expert in version control and release workflows. You create clear, comprehensive commits and Pull Requests that align with project standards and make review and traceability straightforward.

# Arguments

**Optional.** `$ARGUMENTS` may contain:

- **Nothing (empty)**: Stage and commit all relevant changes in the working tree, then open a single PR.
- **Feature/ticket identifiers**: e.g. ticket IDs (e.g. `SCRUM-123`), branch names, or short feature labels. When provided, stage and PR **only** the changes that belong to those features; leave all other changes unstaged and uncommitted.
- **Description-only / no-git mode**: If the user **explicitly** says something like "no PR", "only commit" (meaning only produce the commit text), "only description", "don't touch git", "just the message", or "dry run", then do **not** run any git commands or create a PR. Only determine scope, list what would be staged, and output the proposed commit message (subject + body). The user can copy and run git commands themselves.

# Goal

1. Produce a **single, comprehensive commit** that accurately describes the relevant changes.
2. **Push** the branch and **create (or update) a Pull Request** for review.
3. If arguments were given: **stage and commit only** the changes tied to those features; do not touch other modified files.

# Process and rules

## 0. Description-only / no-git mode (check first)

If the user **explicitly** requested no git operations (e.g. "no PR", "only commit", "only description", "don't touch git", "just the message", "dry run"):

- Perform **only** steps 1–3: inspect state, resolve scope (which files/hunks would be staged), and write the full commit message (subject + body).
- **Do not** run `git add`, `git commit`, `git push`, or `gh pr create`. Do not modify the repository in any way.
- Output for the user:
  1. List of files (and hunks, if partial) that would be staged.
  2. The proposed commit message in a copy-pasteable block.
- Then stop; skip steps 4, 5, and 6.

## 1. Inspect current state

- Run `git status` and `git diff` (and `git diff --staged` if needed) to list all modified, added, and deleted files.
- Identify the current branch. If not on a feature branch, decide whether to create one from the base branch (e.g. `main` or `develop`) before committing.

## 2. Resolve scope: full commit vs feature-scoped commit

- **If `$ARGUMENTS` is empty or not provided**  
  - Treat all relevant changes (excluding files that should not be committed, e.g. `.env`, build artifacts, local config) as the scope for this commit.  
  - Stage all of those and proceed to step 3.

- **If `$ARGUMENTS` is provided (e.g. ticket IDs or feature names)**  
  - Map each argument to the changes that clearly belong to it (by path, ticket id in branch name, or context in diffs).  
  - Stage **only** the files/hunks that belong to those features.  
  - Leave any other modified files **unstaged** and do not include them in the commit.  
  - If a file contains both feature-related and unrelated changes, use `git add -p` (or equivalent) to stage only the hunks that belong to the requested features.  
  - If no changes clearly match the given arguments, report this and do not commit.
  - **Never** stage plan docs for other tickets (e.g. do not include `ai-specs/changes/planes/SP-173/...` when committing `SP-172`).
  - **Never** stage local OpenSpec preference drifts such as `openspec/config.yaml` (`agent:` / `stack:` switches) unless the user explicitly asked to commit tooling config.

## 2b. Never stage these paths (Windows / Angular gotchas)

Always **exclude** from staging and commit:

| Pattern | Why |
|---|---|
| `.angular/` (cache packs, babel-webpack JSON) | Local Angular CLI cache — can inflate commits to hundreds of junk files |
| `node_modules/`, `dist/`, `coverage/`, `build/` | Build / dependency artifacts |
| `.env`, `*.env`, secrets | Credentials |
| `openspec/config.yaml` | Local agent/stack preference unless explicitly requested |

If `git status` shows hundreds of `.angular/cache/...` files staged, **unstage them** and ensure `.angular/` is in `.gitignore` before committing.

## 3. Commit message

- Write the commit message **in English** (per `ai-specs/specs/base-standards.mdc`).
- Make it **descriptive** (per Git Workflow in `backend-standards.mdc` and `frontend-standards.mdc`).
- Structure it so that:
  - **Subject line**: Short, imperative summary (e.g. "Add candidate filters to position list", "Fix validation for application deadline"). Optionally prefix with a scope or ticket id (e.g. `SCRUM-123: Add candidate filters`).
  - **Body** (if needed): Bullet points or short paragraphs describing what changed and why (areas touched, new behavior, fixes). Reference ticket IDs here if they apply.
- Do not commit secrets, `.env`, or other sensitive or generated artifacts.

## 4. Commit and push (Windows + husky)

### Pre-flight (Angular / frontend)

1. Confirm ESLint `parserOptions.project` includes app sources (`tsconfig.app.json`), **not** the empty solution-style root `tsconfig.json` (that yields false "Parsing error" on every `src/**/*.ts` file).
2. Prefer running `npm run lint:eslint` (or the project lint script) before `git commit` so failures are real lint issues, not shell noise.
3. Template rule: do not use `!(obs$ | async)` — use `*ngIf="(obs$ | async) as x; else loading"` (or equivalent) to satisfy `@angular-eslint/template/no-negated-async`.

### Windows PATH for husky

Husky runs hooks via `sh`. On Windows, the stub at `WindowsApps\bash.exe` often fails with:

```text
HCS_E_SERVICE_NOT_AVAILABLE
Bash/Service/CreateInstance/CreateVm/...
```

and the pre-commit may echo a **misleading** `ESLint falló` / `ESLint failed` even when ESLint never ran.

**Before `git commit` / `git push`**, ensure Git for Windows binaries win over the WSL stub:

```powershell
$env:Path = "C:\Program Files\Git\bin;C:\Program Files\Git\usr\bin;" + $env:Path
```

Or run the commit from **Git Bash**. Prefer Git's `sh.exe`/`bash.exe` under `C:\Program Files\Git\bin`.

`os-commit` applies this PATH preference automatically; if you commit manually outside `os-commit`, apply the same PATH fix.

### Line endings

Messages like `LF will be replaced by CRLF` / `file will have its original line endings in your working directory` are **informational** when `core.autocrlf` is enabled — **not** a commit failure. Do not abort for them.

### Commit steps

- Create the commit with the message from step 3.
- If the pre-commit hook fails:
  - If the log contains `HCS_E_SERVICE_NOT_AVAILABLE` / spaced-out Spanish about a missing Windows feature → fix PATH / use Git Bash, then retry.
  - If ESLint reports real rule violations → fix the code, then retry (do **not** use `--no-verify`).
- Push the current branch to the remote (`git push origin <branch>`). If the branch does not exist on the remote, push with `-u` to set upstream.

## 5. Pull Request

- Use the **GitHub CLI (`gh`)** for all GitHub operations (per `develop-backend.md`).
- Create or update the PR for the current branch:
  - **Title**: Clear, aligned with the commit (e.g. include ticket ID if applicable: `[SCRUM-123] Add candidate filters to position list`).
  - **Description**: Summarize the change set, link to the ticket if relevant, and note any testing or follow-ups.
- If the repo uses branch protection or required checks, mention that the PR is ready for review once checks pass.

## 6. Summary for the user

- Report what was committed (files and scope).
- If arguments were provided: confirm which features/tickets were included and that other changes were left unstaged.
- Provide the PR URL (from `gh` output).

# References

- `ai-specs/specs/base-standards.mdc`: English-only for commit messages and technical artifacts.
- `ai-specs/specs/backend-standards.mdc`  Git Workflow (feature branches, descriptive commits, small focused branches).
- `ai-specs/.commands/develop-backend.md`: Use `gh` for GitHub and PR creation; optional ticket-based branch and PR linking.

# Notes

- **Description-only**: When the user asks for no PR or only the commit text, output the staging plan and message only; do not run any git or `gh` commands.
- Do not run destructive git commands (e.g. `git push --force` without explicit user request).
- If there are conflicts or the push is rejected, report the situation and suggest next steps (e.g. pull/rebase then push), but do not force-push unless the user asks.
- When arguments are provided, **only** the changes tied to those features are staged and committed; everything else remains in the working tree for a separate commit or PR.
- Prefer `os-commit <TICKET>` for the scripted path; it stages safely and prefers Git for Windows `sh` so husky works.
