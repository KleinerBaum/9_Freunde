# Private staff pilot release gate

This checklist controls the first deployment that may use real family and child
data. A checked item must have evidence retained by the childcare provider
outside this repository. Do not store personal data, credentials, resource IDs,
contracts, consent records, or incident details here.

## Current release state

- [x] The Sites project uses custom access with only the owner allowed and no
  user or group allowlists.
- [ ] The deployed release has been verified to remain in fictional `demo`
  mode until the newly hardened version is published.
- [x] The browser portal is the only pilot surface; the MCP endpoint is not
  connected to ChatGPT.
- [ ] `GOOGLE_CALENDAR_IMPERSONATED_USER_EMAIL` is configured in Sites with the
  dedicated managed Workspace organizer account.
- [ ] The final staff allowlist contains only active workspace accounts approved
  for the pilot.
- [ ] The hardened source version and hosted environment have been deployed and
  independently checked; repository changes alone do not change the live app.

## Governance approval

The provider's accountable owner must approve every item before
`DATA_MODE=google` is deployed.

- [ ] A GDPR-compliant data-processing agreement covers Sites, Google Workspace,
  and every relevant subprocesser.
- [ ] A retention and deletion schedule covers Sheets rows, Drive photos,
  Calendar events, generated documents, logs, and backups.
- [ ] Consent handling has been reviewed for photos, downloads, communications,
  and parent-visible information.
- [ ] Backup, restore, and access-revocation procedures have been tested.
- [ ] Incident response names an owner, contact path, containment steps, and
  notification process.
- [ ] Invoice and contract templates have completed legal and operational review.
- [ ] The pilot scope, staff membership, start date, review date, and stop
  criteria have written approval.

Approval record (kept outside this repository):

```text
Accountable owner:
Approval reference:
Approval date:
Next review date:
```

## Hosted configuration

Before saving the production version, verify the Sites runtime configuration
without copying values into source control:

- `DATA_MODE=google`
- `REAL_DATA_APPROVED=true` (only after signed approval)
- `AUTH_MODE=sites`
- `MANAGED_STAFF_EMAIL_DOMAIN` is the reviewed managed domain
- `PARENT_ACCESS_ENABLED=false`
- `MCP_ENABLED=false`
- `APP_BASE_URL` is the production `https://...chatgpt.site` URL
- `SESSION_SECRET` is at least 32 random characters and stored as a secret
- `AUDIT_HASH_SECRET` is independent, random, and stored as a secret
- all privacy and legal-notice variables in `.env.example` are complete and
  legally reviewed
- `GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY` is stored as a secret
- `GOOGLE_WORKSPACE_DOMAIN` matches the managed organizer domain
- the service-account email, Sheet, private Drive root, Calendar, and delegated
  organizer values reference the reviewed managed Workspace resources
- the service account has only the documented Sheets and Drive access, and
  domain-wide delegation authorizes only `calendar.events`

Any hosted environment change requires a newly saved and deployed Sites
version before it becomes active.

## Owner-only production validation

Deploy to owner-only access first. The acceptance evidence must show:

- `/api/health` reports `mode: "google"` with Sheets, Drive, and Calendar
  configured and all release gates ready
- an authenticated administrator receives successful sanitized results from
  `/api/admin/integrations/health`
- an unauthorized account cannot open the site
- a managed account absent from the `users` tab cannot create an application
  session
- `staff_read` cannot write; `staff_write` cannot perform admin-only consent or
  privacy actions
- changing `active=false` or incrementing `session_version` blocks an existing
  session on its next protected request
- missing, restricted, or withdrawn photo consent blocks the relevant upload,
  listing, preview, and download operation
- a request to `/api/mcp` without the bearer token receives `401`
- a request to `/api/mcp` while `MCP_ENABLED=false` receives `404`
- application and worker logs contain no personal data or secret values

External write tests require a separate explicit confirmation. Use one
fictional record and controlled staff recipients only. Record the results for
Sheets, private Drive upload/download, Calendar create/update, and PDF drafting.
Removing the test artifacts also requires explicit confirmation.

## Staff rollout and rollback

After owner-only validation, add only the approved active staff workspace
accounts to the Sites custom allowlist. Keep parent accounts and all groups
excluded from this pilot.

If validation fails:

1. Keep Sites access custom and owner-only.
2. Restore `DATA_MODE=demo`.
3. Deploy the previous known-good saved version.
4. Confirm `/api/health` reports demo mode.
5. Record the failure and remediation outside the repository without personal
   data or credentials.
