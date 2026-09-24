# Remote-state bootstrap

This root initially used local state because the GCS state bucket had to exist before Terraform could use it as a backend. The bucket has now been created and `backend.tf` configures the remote backend.

The configured backend is:

```hcl
bucket = "case-theory-tf-state"
prefix = "bootstrap"
```

If the backend changes later, run `terraform init -migrate-state` and confirm the migration. Never remove a previous state copy before confirming that `terraform state list` works with the new backend.
