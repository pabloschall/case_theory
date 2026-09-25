# EILLEN

EILLEN is a mobile-first collaborative case investigation workspace. The current Phase 1 foundation provides secure cookie authentication, rotating refresh sessions, universal investigation-tool access for authenticated users, PostgreSQL migrations, Redis-backed login rate limiting, a worker process, and a responsive React shell.

The product and deployment design lives in [ARCHITECTURE.md](ARCHITECTURE.md).

## Run locally

Requirements: Docker with Compose and `make`.

```bash
cp .env.example .env
# Replace SECRET_KEY in .env with a random value of at least 32 characters.
make dev
```

Set `APP_NAME` in the root `.env` to control the product name shown by the frontend, browser title, API metadata, legal copy, and invitation messages.

Open the public landing page at <http://localhost:5173>, API documentation at <http://localhost:8000/api/docs>, and Mailpit at <http://localhost:8025>. Compose waits for PostgreSQL and Redis, applies the migration, seeds plans and grants idempotently, then starts the API.

## Account email

Registration sends an email-verification link, and the login page provides password recovery. Configure the full Mailgun domain endpoint and sender in the root `.env`:

```dotenv
MAILGUN_BASE_URL=https://api.mailgun.net/v3/mg.example.com
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_FROM_EMAIL=Case Theory <postmaster@mg.example.com>
```

The API stores only SHA-256 hashes of one-time verification and password-reset tokens. Verification links expire after 24 hours and reset links after 60 minutes by default. Successful password resets revoke every active refresh session for the account.

Guests can continue to the Case Directory to search public cases and read their overviews and timelines. Signed-in users can follow cases and use the collaborative workspace. **My Desk** contains only cases the current user explicitly follows, while **My Cases** contains cases they own. Creating a case does not automatically follow it.

Guests have read-only access to public case records. Manual public cases are unlimited. Other case creation uses a weekly allowance that resets Monday at 00:00 UTC: one case for free accounts and five for paid accounts. My Notes and My Timeline are private to the signed-in user. Free accounts can open these tabs in read-only mode; publishing and managing entries requires a paid plan.

## Development demo accounts

The development seed creates three verified local accounts. They all use the password `EillenDemo2026!`.

| Account | Email | Access |
| --- | --- | --- |
| Admin | `admin@example.com` | Admin |
| Free | `free@example.com` | Free plan |
| Paid | `paid@example.com` | Lead Investigator plan |

These predictable accounts are created only when `ENVIRONMENT=development`; staging and production never seed them.

Administrators use the same login page as every other account and are routed to the admin workspace after authentication. Staging does not create predictable credentials. Register and verify an account there, then grant its initial administrator access with `./scripts/promote-staging-admin you@example.com`.

## OpenAI case generation

Add your key to the root `.env` file:

```dotenv
OPENAI_API_KEY=your-key-here
AI_TEXT_MODEL=gpt-5-mini
AI_IMAGE_MODEL=gpt-image-2.5-flare
```

Then restart the API and worker:

```bash
docker compose up -d --force-recreate backend worker
```

Creating a case saves the intake immediately and queues a worker job. The worker generates a structured overview and candidate timeline with the Responses API, then creates symbolic editorial banner art. Generated text is labeled as AI-assisted and based only on the submitted intake until sourced research is added.

## Evidence storage

Evidence files use the `StorageProvider` interface. Docker Compose starts `fake-gcs-server` at `http://localhost:4443` with a private local bucket named `eillen-evidence`; no Google credentials are needed for local development. The browser uploads directly to that service, then the API validates the stored file signature and size and records its SHA-256 hash.

For Google Cloud, set `STORAGE_PROVIDER=gcs`, `GCS_BUCKET`, and `GCS_PROJECT_ID`, and provide Application Default Credentials to the backend. The production provider issues short-lived V4 upload and download URLs. Bucket objects should remain private.

The Evidence tab accepts supported files up to 25 MB and public YouTube or website links. A stored evidence item can be attached to a discussion thread or timeline event without copying it.

AI-generated case banners also use the configured storage provider. They are stored privately under `cases/{case_id}/covers/{generation_id}.webp`; the database keeps the object key and a stable case-cover endpoint redirects authorized viewers to a short-lived storage URL. Local development uses the GCS emulator, while production uses the same flow with Google Cloud Storage. Manual template banners remain frontend assets.

## FBI case discovery and import

Paid investigators and admins can open **Create Case → Browse Sources → FBI** to search public FBI Wanted records. Eillen calls the FBI from the backend, caches lists for 15 minutes and individual records for one hour, and creates every import as a private draft. The official payload remains in `case_sources`, separate from AI suggestions and community edits. Imported images are validated and copied into the configured private storage provider.

```dotenv
FBI_API_BASE_URL=https://api.fbi.gov/wanted/v1
FBI_API_KEY=
FBI_API_TIMEOUT=15
```

The public Wanted API currently works without a key. `FBI_API_KEY` is optional and stays server-side. Apply database changes with `make migrate`. Backend integration tests mock every FBI response and can be run with:

```bash
make test-backend
```

Eillen is an independent platform and is not affiliated with or endorsed by the Federal Bureau of Investigation.

## Case collaboration invitations

Case owners can create a single-use collaborator invitation from the case header and open a prefilled text message or email in the device's native app. Recipients who need an account are returned to the invitation after registration or login. Accepting an invitation grants contributor access, including access to a private case, and adds the case to My Desk.

Invitation links expire after seven days by default. Configure this with `CASE_INVITATION_EXPIRY_DAYS`. `FRONTEND_URL` must be the public frontend origin so links opened on another phone resolve correctly.

## Direct messaging

Signed-in members can open another contributor's profile from a discussion and start a private one-to-one conversation. Messenger is available in the main navigation. Members can attach photos and files through the device's native picker. Attachments upload directly to private object storage, are validated by the API, and are available only to the conversation participants through signed URLs.

## Development commands

```bash
make test
make lint
make typecheck
make migrate
make migration name=describe_change
make seed
```

For local host tooling, install the backend package with its development extras from `backend/pyproject.toml` and run `npm install` inside `frontend`. Application secrets belong in `.env`; only safe defaults are committed in `.env.example`.

## Phase 1 API

- `GET /health`
- `GET /api/v1/auth/csrf`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/email-verification/request`
- `POST /api/v1/auth/email-verification/confirm`
- `POST /api/v1/auth/password/forgot`
- `POST /api/v1/auth/password/reset`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/users/me`
- `GET /api/v1/subscriptions/plans`
- `GET /api/v1/cases?q=...`
- `GET /api/v1/cases/following`
- `GET /api/v1/cases/mine`
- `POST /api/v1/cases`
- `GET /api/v1/cases/{id}`
- `POST /api/v1/cases/{id}/follow`
- `DELETE /api/v1/cases/{id}/follow`
- `GET /api/v1/integrations/fbi/cases`
- `GET /api/v1/integrations/fbi/cases/{external_id}`
- `POST /api/v1/integrations/fbi/cases/{external_id}/import`
- `POST /api/v1/integrations/fbi/imports/{case_id}/enrich`

State-changing requests require the CSRF token returned by `/auth/csrf` in the `X-CSRF-Token` header. Authentication tokens are only sent in HTTP-only cookies.

## Security baseline

Passwords use Argon2id. Refresh tokens rotate and only SHA-256 token digests are stored. CORS is explicit, authentication endpoints are rate-limited through Redis, and responses carry request IDs and defensive browser headers. Permission decisions remain server-side. Official-source importing, private cases, and administrative access require explicit plan permissions.

Registration requires separate confirmation that the member is at least 18 and accepts the current Terms of Use and Community Standards. The backend stores an immutable acceptance row for each policy with its version, document checksum, acceptance time, request ID, IP address, and user agent.
