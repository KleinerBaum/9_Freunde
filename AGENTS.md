# AGENTS.md — 9_Freunde

Coding-agent instructions for the 9 Freunde family and administration portal.

## Active architecture

- The TypeScript ChatGPT Sites application is the primary product path.
- The Python/Streamlit application is a legacy and migration path.
- Do not implement a feature twice or modify the legacy application unless the
  task explicitly includes it.
- Read `package.json`, `.env.example`, `.openai/hosting.json`,
  `docs/SITES_APP.md` and relevant tests before changing the Sites app.

## Environment

```bash
export NVM_DIR="$HOME/.nvm"
. "$NVM_DIR/nvm.sh"
nvm use
```

- Local Node is selected by `.nvmrc`.
- Use `npm ci` for a clean installation; do not use global npm packages.
- Keep `.env.local` ignored and use it only for local configuration.
- Use `DATA_MODE=demo` and fictional users unless production integration work
  is explicitly requested.
- In Codex/WSL, keep `TMPDIR=/tmp` and
  `WRANGLER_LOG_PATH=/tmp/codex-wrangler`.

## Primary commands

```bash
npm run dev
npm run lint
npm run typecheck
npm test
npm run build
npm run check
```

The complete handoff gate is:

```bash
TMPDIR=/tmp WRANGLER_LOG_PATH=/tmp/codex-wrangler npm run check
```

The Cloudflare Vite plugin queries WSL network interfaces during
`npm run dev`. In a restricted Codex sandbox, request a narrow escalation for
the development server rather than weakening the default sandbox globally.

## Legacy Streamlit path

Use only when explicitly required:

```bash
uv venv --python /usr/bin/python3 .venv
uv pip install --python .venv/bin/python -r requirements-dev.txt
TMPDIR=/tmp .venv/bin/python -m pytest
TMPDIR=/tmp .venv/bin/python -m streamlit run app.py
```

Do not add new Sites behavior to the legacy application by default.

## Data and privacy invariants

- This application handles highly sensitive family and child data.
- Never use real names, contact details, health data, photos, documents,
  calendars or identifiers in tests, prompts, logs or screenshots.
- Parents may access only resources authorized for their own child.
- Administrative actions require an authenticated authorized role.
- Photos and documents remain private; never create public Drive links.
- File names, generated logs and object keys must not expose personal data.
- Demo mode must remain clearly marked and contain fictional data only.

## Google integration

- Keep Google Sheets, Drive and Calendar integrations server-side.
- Use least-privilege scopes and document any scope change.
- Keep service-account credentials and private keys outside the repository.
- Domain-wide delegation or impersonation requires an explicitly approved
  managed Google Workspace design; do not emulate it with personal Gmail.
- External writes require explicit user confirmation and auditable results.

## Contracts and synchronization

When data fields, roles or permissions change, update together:

- canonical Zod schemas and types
- API and MCP tool contracts
- authorization and ownership checks
- server logic and adapters
- UI state and labels
- generated documents and exports
- demo fixtures
- tests and documentation

Avoid raw duplicated role, status, tab and environment strings when a canonical
constant or enum exists.

## ChatGPT Apps and Sites

- Preserve the exact project ID in `.openai/hosting.json`.
- Keep MCP tool schemas narrow and annotate read-only, destructive and
  open-world behavior correctly.
- Require confirmation for Calendar, Drive, document and administrative writes.
- Keep resource domains and CSP minimal.
- Do not deploy, save a Sites version or change access controls without an
  explicit request.

## Handoff

- Reproduce defects and report expected versus actual behavior.
- Keep changes PR-sized and avoid unrelated refactors.
- Report exact checks and actual outcomes.
- Finish with `git status --short --branch`.
- Do not commit, push, create a PR or deploy without explicit authorization.
