# 9 Freunde Sites app

This is the recommended application in this repository. It is a responsive staff and parent portal built with Next.js/React, vinext with its Cloudflare worker adapter for ChatGPT Sites, and the ChatGPT Apps SDK over MCP.

The original Streamlit app remains available during migration. The new app intentionally keeps the operating model small: Google Sheets is the database, Google Drive stores private child photos, Google Calendar sends invitations and updates, and invoices/contracts are deterministic PDFs that always require human review. No paid LLM call is needed for normal portal use.

## What works

- Staff dashboard with children, parents, onboarding tasks, documents, events, and consent status.
- Parent login scoped to assigned children, documents, events, and Drive photos.
- Parent updates for contact, emergency, dietary, allergy, language, and parent-visible care information.
- Staff CRUD for child records and document status.
- Deterministic invoice and contract PDF drafts; contract output includes a mandatory review notice.
- Private Google Drive galleries with JPG/PNG/WebP signature validation, a 15 MB limit, and no public sharing links.
- Google Calendar event creation and editing with attendee updates and email reminders.
- ChatGPT tools for search/fetch, operational overview, document drafting, and confirmed Calendar writes.
- A compact interactive ChatGPT widget rendered from `ui://9-freunde/dashboard-v1.html`.
- Fictional, non-persistent demo data for safe evaluation.

## Local demo

Requirements: Node.js 22 or newer.

```bash
npm install
copy .env.example .env.local
npm run dev
```

Open `http://localhost:3000`. The login screen provides fictional staff and parent demo accounts. Never use the demo mode or demo accounts with real child data.

Run all checks:

```bash
npm run check
```

## Production Google Workspace mode

1. Create a Google Cloud service account and enable Google Sheets, Drive, and Calendar APIs.
2. Create one private spreadsheet with tabs named `children`, `parents`, `users`, and `documents`.
3. Put the spreadsheet and the child-photo root in a Google Workspace Shared Drive. Add the service account as a Content Manager so newly created folders and photos belong to the organization rather than an individual account.
4. Create a dedicated Workspace organizer account and facility Calendar.
5. Enable domain-wide delegation for the service account, then authorize only `https://www.googleapis.com/auth/calendar.events` in Google Admin Console. Set `GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL` to the dedicated organizer. Sheets and Drive continue to use the service account directly.
6. Copy `.env.example` to the deployment environment, set `DATA_MODE=google`, and provide the listed server-side values. Keep the private key, session secret, and MCP bearer token in the Sites secret store only.
7. Deploy a new Sites version after changing hosted environment values; saved environment revisions do not alter an already-running release.

Recommended first-row headers:

```text
children: child_id,name,birthdate,start_date,group,status,primary_parent_id,parent_email,allergies,dietary,languages_at_home,care_hours_per_week,care_fee_cents,meal_fee_cents,folder_id,photo_consent,download_consent,notes_parent_visible,notes_internal,updated_at
parents: parent_id,name,email,phone,phone2,address,preferred_language,emergency_contact_name,emergency_contact_phone,notifications_opt_in,child_ids,updated_at
users: user_id,email,name,role,parent_id,child_ids,password_salt,password_hash,active
documents: document_id,child_id,type,status,title,number,period,care_fee_cents,meal_fee_cents,total_cents,due_date,created_at,drive_file_id
```

The app adds missing columns when it writes a row, but the four tabs must exist before first login. Values in `role` are `admin` or `parent`; `child_ids` is a comma-separated list. Create a password hash locally and copy only the resulting salt and hash into the `users` tab:

```bash
node scripts/hash-password.mjs "a-long-unique-password"
```

Production access rules are enforced server-side:

- Admins can manage all records, upload photos, generate documents, and write Calendar events.
- Parents can see only their assigned children and can update only the allowed family-provided fields.
- Internal notes are never returned to parent sessions.
- Photos are streamed through an authenticated application route; Drive files remain private.
- Calendar writes use `sendUpdates=all` so invitations and edits reach attendees.
- MCP writes require explicit confirmation and, in Google mode, `MCP_BEARER_TOKEN`.
- `GET /api/health` reports liveness and whether required configuration is present.
- `GET /api/admin/integrations/health` requires an authenticated admin session and performs sanitized, read-only checks against the Sheet schema, writable Drive root, and delegated Calendar.

The Calendar organizer must be a managed Google Workspace user. Personal Gmail accounts cannot be used for service-account domain-wide delegation.

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
- Face recognition, automatic child tagging, and public photo links are deliberately out of scope.
- The connected Google Drive and Calendar accounts were inspected only for availability during development; resource IDs and personal data are not committed.
