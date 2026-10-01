# Scheduled cases

The daily `recent` job searches the live web for public cases with meaningful developments reported in the last 30 days. The daily `historical` job searches online archives, court records, official histories, and established reporting for famous or cold cases whose incidents occurred at least 10 years ago. Neither lane has a fixed case catalog or a single discovery provider. Each search proposes several candidates and ranks them by relevance, recency where applicable, and source coverage. Recent candidates need at least two independent source domains; historical candidates need at least one. Candidate URLs must appear in the web search tool's source list.

Both jobs compare candidates with existing cases and record a source identity plus a daily run key in `case_sources`. The `(source_type, external_id)` pair is unique, so a retry cannot create a second case that day or repeat a source. A separate inactive system account owns the cases; `seed` creates it. Each case stays private while research and generation run. A successful generation publishes it automatically, with no content approval step. A failed generation stays private and is available to administrators under **Admin → Cases** for diagnosis or retry.

## Local use

Run the database seed and set `OPENAI_API_KEY` before previewing or creating a draft. Both previews perform a live web search and incur API usage. A preview does not write to the database.

```bash
make preview-recent-case
make preview-historical-case
make create-recent-case
make create-historical-case
```

Each lane creates at most one case per day, so a successful day publishes one recent and one historical case. If interrupted after claiming a candidate but before research starts, a rerun resumes that queued case. If no eligible candidate remains, it exits successfully without creating one. An administrator can research a failed case again from its case page.

## Google Cloud staging

Terraform defines two Cloud Run Jobs and two Cloud Scheduler triggers. They are off by default. The schedules run daily at 13:00 UTC for recent cases and 14:00 UTC for historical cases. They reuse the backend image and worker service account, and connect to Cloud SQL through the staging VPC. Cloud Scheduler uses a separate invoker account scoped to those jobs.

The staging Terraform workflow reads `ENABLE_SCHEDULED_CASES` from GitHub repository variables. Set it to `true` after deploying a revision with this code, then run the reviewed infrastructure workflow. It takes the current API backend image as the initial job image. Later staging deployments update the jobs to the same backend revision. The jobs remain off while the variable is unset.

For a local Terraform plan or apply, pass all existing staging runtime settings, including Redis, and set:

```hcl
enable_cloud_sql              = true
enable_redis                  = true
enable_scheduled_cases        = true
scheduled_cases_backend_image = "us-central1-docker.pkg.dev/PROJECT/REPOSITORY/backend@sha256:..."
frontend_origin               = "https://staging.example.com"
```

The image should be pinned by digest for a manual apply. Required Secret Manager versions are `database-url`, `secret-key`, `openai-api-key`, `mailgun-api-key`, `mailgun-base-url`, and `mailgun-from-email`. The staging release workflow runs migrations and `python -m app.db.seed`. Review the Terraform plan before applying it. Monitor the first runs for candidate quality, failed research, and API spending.
