# GitHub Actions

`workflows/ci.yml` validates backend, frontend, Terraform, and production container builds on pull requests and pushes to `main`.

`workflows/deploy-staging.yml` is a manually triggered staging release. Protect the GitHub `staging` environment with required reviewers before enabling it. The workflow authenticates with Workload Identity Federation; do not add a service-account JSON key.

`workflows/terraform-staging.yml` plans staging infrastructure changes and can apply the exact saved plan when manually invoked with `apply` enabled. Protect the `staging-infrastructure` environment with required reviewers. This workflow explicitly enables the Cloud SQL and Memorystore modules; application releases do not modify those resources.

Configure these repository or `staging` environment variables before the first deployment:

| Variable | Staging value |
| --- | --- |
| `GCP_PROJECT_ID` | `case-theory` |
| `GCP_REGION` | `us-central1` |
| `GCP_ARTIFACT_REPOSITORY` | `case-theory` |
| `GCP_API_SERVICE` | `case-theory-stg-api` |
| `GCP_FRONTEND_SERVICE` | `case-theory-stg-frontend` |
| `GCP_WORKER_POOL` | `case-theory-stg-worker` |
| `GCP_MIGRATION_JOB` | `case-theory-stg-migration` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full Workload Identity Provider resource name |
| `GCP_DEPLOY_SERVICE_ACCOUNT` | Deployment service-account email |
| `GCP_TERRAFORM_PLAN_SERVICE_ACCOUNT` | Read-only Terraform planning service-account email |
| `GCP_TERRAFORM_APPLY_SERVICE_ACCOUNT` | Terraform apply service-account email |
| `STAGING_FRONTEND_ORIGIN` | Public staging frontend origin used for GCS CORS |

The deployment workflow creates the Cloud Run services, worker pool, and migration job on its first run, then updates them on later runs. It discovers the API URL after deployment and uses that URL for the smoke test.

Before the first deployment, add enabled versions to these Google Secret Manager secrets: `secret-key`, `database-url`, `openai-api-key`, `mailgun-api-key`, `mailgun-base-url`, `mailgun-from-email`, and `fbi-api-key`. Terraform creates the secret containers and grants the runtime identities access; it does not store secret values in Terraform state.

After applying the infrastructure changes, seed the empty secrets and create the staging database user from the local `.env` without printing secret values:

```bash
./scripts/bootstrap-staging-secrets
```

Set `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, and `GCP_TERRAFORM_PLAN_SERVICE_ACCOUNT` as repository variables so same-repository pull-request plans can read them. Scope `GCP_TERRAFORM_APPLY_SERVICE_ACCOUNT` to the protected `staging-infrastructure` environment. The remaining application deployment values may be scoped to the `staging` environment.

The first Workload Identity pool and Terraform service account must be bootstrapped from an already authenticated workstation or Cloud Shell. After that one-time setup, GitHub Actions can plan and apply infrastructure without stored Google Cloud keys.

After the first local Terraform apply creates federation, obtain the exact GitHub values with:

```bash
./scripts/terraform -chdir=infra/environments/staging output -json github_actions
```

Set `GCP_WORKLOAD_IDENTITY_PROVIDER` to `workload_identity_provider`, then map the `plan`, `apply`, and `deploy` service-account outputs to their corresponding GitHub variables. The provider currently admits the exact repository name `pabloschall/case_theory`. Set `github_repository_id` once the immutable private-repository ID is available through authenticated GitHub access.
