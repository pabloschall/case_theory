# Case Theory infrastructure

Terraform manages the Google Cloud infrastructure. The `bootstrap` root creates the remote-state bucket once; environment roots then use that bucket through the GCS backend.

## Prerequisites

- Terraform 1.7 or newer. A checksum-verified Terraform 1.14.7 binary is installed in the ignored `.tools` directory and exposed through `./scripts/terraform`.
- Google Cloud CLI authenticated with an account that can administer project `case-theory`. Google Cloud SDK 586.0.0 is installed in `.tools` and exposed through `./scripts/gcloud`.
- Application Default Credentials when running outside Cloud Shell.

For local macOS use, authenticate once from the repository root:

```bash
./scripts/gcloud auth login --update-adc --force
./scripts/gcloud config set project case-theory
./scripts/gcloud auth application-default set-quota-project case-theory
```

On Google's consent page, approve the requested Google Cloud Platform access. The Terraform provider requires the `cloud-platform` scope. If that permission is left unchecked or declined, Google returns credentials that Terraform cannot use and `gcloud` rejects the login.

The wrappers keep Google Cloud credentials in the ignored `.tools/gcloud-config` directory and point Terraform at those credentials. They do not change the global shell profile or global Google Cloud configuration.
The `gcloud` wrapper opens authentication in Google Chrome when Chrome is installed. Set `BROWSER` before running it if you want to override that choice.

## 1. Bootstrap remote state

Run this once from Cloud Shell:

```bash
./scripts/terraform -chdir=infra/bootstrap init
./scripts/terraform -chdir=infra/bootstrap plan -out=bootstrap.tfplan
./scripts/terraform -chdir=infra/bootstrap apply bootstrap.tfplan
```

This creates `case-theory-tf-state`, with uniform access, public-access prevention, and object versioning. The bootstrap state remains local initially. Preserve its state file securely until it is migrated into the new bucket as described in `bootstrap/README.md`.

## 2. Plan staging foundations

```bash
cp infra/environments/staging/terraform.tfvars.example infra/environments/staging/terraform.tfvars
./scripts/terraform -chdir=infra/environments/staging init
./scripts/terraform fmt -check -recursive infra
./scripts/terraform -chdir=infra/environments/staging validate
./scripts/terraform -chdir=infra/environments/staging plan -out=staging.tfplan
```

The default staging variables leave Cloud SQL and Memorystore disabled. Review and apply the foundation plan before enabling recurring-cost data services.

## 3. Enable data services deliberately

After reviewing instance sizing and cost, set these in the untracked `terraform.tfvars` file:

```hcl
enable_cloud_sql = true
enable_redis     = true
```

Generate and review a new saved plan before applying it. Terraform creates the Cloud SQL instance and database, but it does not create a database password or secret versions. Provision those values separately through Secret Manager so credentials do not enter Terraform configuration or state.

## Authentication and state

The GCS backend supports state locking. Do not disable locking, commit state, commit saved plans, or commit `terraform.tfvars`. Commit `.terraform.lock.hcl` after the first successful `terraform init`.

Terraform creates Secret Manager containers and IAM access bindings only. Insert secret versions separately using `gcloud secrets versions add` with input that is not echoed or stored in shell history.

## Validation status

The bootstrap and staging roots pass `terraform validate` with Terraform 1.14.7 and Google provider 7.46.1. A refresh-disabled structural plan of the default staging configuration resolves to 43 additions, zero changes, and zero deletions. That structural plan was used only to verify the dependency graph; it must not be applied because it was generated without live Google Cloud refresh.

The staging foundation has been applied and a live Terraform refresh reports no changes. Cloud SQL and Memorystore remain disabled by the default variables and are absent from the current infrastructure.
