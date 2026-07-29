# 9 Freunde Sites app

This is the recommended application in this repository. It is a responsive staff and parent portal built with Next.js/React, vinext with its Cloudflare worker adapter for ChatGPT Sites, and the ChatGPT Apps SDK over MCP.

The original Streamlit app remains available during migration. The new app intentionally keeps the operating model small: Google Sheets is the database, Google Drive stores private child photos, Google Calendar sends invitations and updates, a dedicated Gmail mailbox sends confirmed notices and reviewed PDFs, and invoices/contracts are deterministic PDFs that always require human review. No paid LLM call is needed for normal portal use.

## What works

- Separate `admin`, `staff_write`, `staff_read`, and `parent` roles enforced by
  the server.
- Staff dashboard with children, parents, onboarding tasks, documents, events,
  and versioned consent status.
- Parent access scoped to assigned children, documents, events, and consented
  Drive photos; parent access is disabled by default for the staff pilot.
- Parent updates for contact, emergency, dietary, allergy, language, and parent-visible care information.
- Staff CRUD for child records and document status.
- Deterministic invoice and contract PDF drafts; contract output includes a mandatory review notice.
- Private Google Drive galleries with JPG/PNG/WebP signature validation, a 15
  MB limit, no public sharing links, and server-side consent enforcement.
- Google Calendar event creation and editing with attendee updates and email reminders.
- Admin-only Gmail delivery for opted-in parent notices and reviewed PDF
  drafts. Recipients are resolved server-side and every recipient receives an
  individual message without a visible distribution list.
- ChatGPT tools for search/fetch, operational overview, document drafting, and confirmed Calendar writes.
- A compact interactive ChatGPT widget rendered from `ui://9-freunde/dashboard-v1.html`.
- Pseudonymized audit events, revocable sessions, confirmed privacy-request
  workflows, login throttling, same-origin checks, and global security headers.
- Fictional, non-persistent demo data for safe evaluation. Google mode remains
  locked unless the separate real-data release flag is explicitly enabled.

## Local demo

Requirements: Node.js 22 or newer. The recommended local baseline is the
version pinned in `.nvmrc`.

In WSL or another Bash environment:

```bash
nvm use
npm ci
cp .env.example .env.local
npm run dev
```

To copy the environment template on native Windows, use
`Copy-Item .env.example .env.local` in PowerShell or
`copy .env.example .env.local` in Command Prompt.

Open `http://localhost:3000`. The login screen provides fictional staff and parent demo accounts. Never use the demo mode or demo accounts with real child data.

Run all checks:

```bash
TMPDIR=/tmp WRANGLER_LOG_PATH=/tmp/codex-wrangler npm run check
```

The environment prefix keeps Vitest and Wrangler artifacts in a WSL-native
temporary directory when the command is launched from Codex. Outside Codex,
`npm run check` is sufficient when the shell already provides Linux-native
temporary paths.

## Production Google Workspace mode

Before enabling real data, complete the
[private staff pilot release gate](PRIVATE_STAFF_PILOT.md). Keep Sites access
owner-only until the governance approval, hosted configuration, and production
health checks have all passed.

1. Create a Google Cloud service account and enable Google Sheets, Drive,
   Calendar, and Gmail APIs.
2. Create one private spreadsheet with tabs named `children`, `parents`,
   `users`, `documents`, `consents`, `audit`, and `privacy_requests`.
3. Put the spreadsheet and the child-photo root in a Google Workspace Shared Drive. Add the service account as a Content Manager so newly created folders and photos belong to the organization rather than an individual account.
4. Create a dedicated Workspace organizer account and facility Calendar, plus
   a separate managed portal Gmail mailbox.
5. Enable domain-wide delegation for the service account, then authorize only
   `https://www.googleapis.com/auth/calendar.events` and
   `https://www.googleapis.com/auth/gmail.send` in Google Admin Console. Set
   `GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL` to the dedicated organizer and
   `GOOGLE_GMAIL_IMPERSONATED_USER_EMAIL` to the separate portal mailbox.
   Sheets and Drive continue to use the service account directly and are not
   domain-wide delegated.
6. Complete and sign the [data-protection release
   record](DATA_PROTECTION_RELEASE.md). Only then set `DATA_MODE=google` and
   `REAL_DATA_APPROVED=true`. Use `AUTH_MODE=sites`,
   `PARENT_ACCESS_ENABLED=false`, `MCP_ENABLED=false`, `GMAIL_ENABLED=true`,
   and the managed staff domain for the first pilot. The application remains
   in fictional demo mode unless approval, managed identity, legal notices,
   HTTPS base URL, and all four Google integrations are configured together.
7. Copy `.env.example` to the deployment environment and provide the listed
   server-side values. Keep the private key, session secret, independent audit
   HMAC secret, and any later MCP bearer token in the Sites secret store only.
   A Google project number, OAuth client secret, and OpenAI API key are not
   application configuration and must not be added to Sites. Domain-wide
   delegation needs the service account's numeric client ID only once in Google
   Admin Console.
8. Configure Sites custom access with individually approved managed staff
   accounts. The application reads the authenticated Sites identity and maps it
   to the `users` tab; an allowlist entry alone does not grant an application
   role.
9. Deploy a new Sites version after changing hosted environment values; saved
   environment revisions do not alter an already-running release.

Recommended first-row headers:

```text
children: child_id,name,birthdate,start_date,group,status,primary_parent_id,parent_email,allergies,dietary,languages_at_home,care_hours_per_week,care_fee_cents,meal_fee_cents,folder_id,photo_consent,download_consent,notes_parent_visible,notes_internal,updated_at
parents: parent_id,name,email,phone,phone2,address,preferred_language,emergency_contact_name,emergency_contact_phone,notifications_opt_in,child_ids,updated_at
users: user_id,email,name,role,parent_id,child_ids,password_salt,password_hash,active,session_version
documents: document_id,child_id,type,status,title,number,period,care_fee_cents,meal_fee_cents,total_cents,due_date,created_at,drive_file_id
consents: consent_id,child_id,purpose,status,scope,document_version,source,evidence_ref,recorded_at,recorded_by,withdrawn_at
audit: event_id,occurred_at,actor_ref,actor_role,action,resource_type,resource_ref,outcome,request_ref
privacy_requests: request_id,type,subject_type,subject_ref,status,requested_at,requested_by,reviewed_at,reviewed_by,due_at,confirmation
```

All seven tabs must exist before the first Google-mode login. The app validates
the required columns and adds missing columns when it writes a row, but it does
not create missing tabs.

Values in `role` are `admin`, `staff_write`, `staff_read`, or `parent`;
`child_ids` is a comma-separated list. Use the least-privileged role:

- `admin`: user/consent/privacy administration and all staff operations
- `staff_write`: operational child, document, photo, and Calendar changes
- `staff_read`: read-only operational access
- `parent`: only assigned children; disabled during the first staff pilot

Set `active=false` to revoke an account immediately. Increment
`session_version` to invalidate all of that account's existing sessions after a
role or security change. Approved administrative tooling can perform both as a
confirmed operation through `PATCH /api/admin/users/access`; every such change
increments `session_version` and writes a pseudonymized audit event.

Password columns are retained only for local/migration compatibility. Do not
use spreadsheet passwords as the production identity. If a local migration
test explicitly needs one, create a password hash locally and copy only the
resulting salt and hash into the `users` tab:

```bash
node scripts/hash-password.mjs "a-long-unique-password"
```

Production access rules are enforced server-side:

- Admins can manage records and versioned consent decisions.
- Write staff can perform operational changes; read staff cannot mutate data.
- Parents can see only their assigned children and can update only the allowed family-provided fields.
- Internal notes are never returned to parent sessions.
- Photo upload, listing, preview, and download are denied unless the latest
  applicable consent record permits the requested operation.
- Photos are streamed through authenticated application routes; Drive files
  remain private.
- Every protected request validates the account's current role, active state,
  and session version. Sessions expire after 30 minutes.
- Unsafe API requests require a same-origin request in real-data mode.
- Login attempts are throttled and temporarily locked after repeated failures.
- Audit rows contain HMAC-pseudonymized actor/resource references and no
  business payload or names.
- Calendar writes use `sendUpdates=all` so invitations and edits reach attendees.
- `POST /api/communications/send` is admin-only, requires a same-origin request
  plus explicit confirmation, accepts no recipient addresses, and sends no
  more than 100 individual messages.
- Parent notices honor `notifications_opt_in`. Reviewed PDFs go only to the
  assigned primary contact; document status changes to `sent` only after a
  successful Gmail delivery.
- Gmail uses a distinct delegated auth context and token cache with only
  `gmail.send`. Audit rows never contain recipient addresses, subject lines,
  message bodies, or provider error details.
- MCP is disabled unless `MCP_ENABLED=true`; writes additionally require
  explicit confirmation and a bearer token in Google mode.
- `GET /api/health` reports liveness and whether required configuration is present.
- `GET /api/admin/integrations/health` requires an authenticated admin session
  and performs sanitized checks against the Sheet schema, writable Drive root,
  delegated Calendar, and Gmail delegated-token issuance. The health check
  never sends a message.

The Calendar organizer and Gmail sender must be distinct users in
`GOOGLE_WORKSPACE_DOMAIN`. Personal Gmail accounts are rejected by
configuration validation. The provider must also enforce MFA for staff in the
managed identity system; the application cannot configure that external policy
itself.

## ChatGPT App setup

The MCP endpoint is `/api/mcp`. ChatGPT Sites reserves the root `/mcp` path, so in ChatGPT developer mode connect the deployed HTTPS URL ending in `/api/mcp`. The server exposes:

- `search` and `fetch` for record discovery.
- `get_overview` and `render_overview` for the interactive staff dashboard.
- `draft_document` for reviewable invoice/contract drafts.
- `create_calendar_event` and `update_calendar_event` for confirmed Google Calendar writes.

For current Apps SDK requirements, see the official [MCP server guide](https://developers.openai.com/apps-sdk/build/mcp-server/), [UI guide](https://developers.openai.com/apps-sdk/build/chatgpt-ui/), and [deployment guide](https://developers.openai.com/apps-sdk/deploy/).

## Sites packaging

`.openai/hosting.json` is created when the Sites project is provisioned. After committing the exact source state:

```bash
npm run sites:archive
```

The archive contains the vinext standalone server and the Sites metadata for that commit. Source deployments use the Cloudflare worker entry declared in `wrangler.jsonc`. Production publishing uses the exact commit pushed to Sites; the archive is retained as a reproducible local verification artifact. Deploy this application privately until real authentication, legal templates, retention rules, and the Google Workspace resources have been reviewed by the childcare provider.

## Privacy and operating assumptions

- The published demo contains only fictional names, contacts, records, and illustrations.
- The production operator is responsible for a GDPR-compliant processing agreement, retention/deletion policy, consent records, backup strategy, and legal review of contract/invoice templates.
- The repository includes working drafts for the
  [processing register](PROCESSING_REGISTER.md),
  [DPIA](DPIA_TEMPLATE.md), and
  [retention/incident procedure](RETENTION_AND_INCIDENT_RUNBOOK.md). They are
  not legal approval and must be completed and signed externally.
- Face recognition, automatic child tagging, and public photo links are deliberately out of scope.
- Google resource IDs, delegated account addresses, private keys, and personal
  data are never committed.
