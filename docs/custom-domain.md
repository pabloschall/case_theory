# case-researcher.com on staging

The frontend Cloud Run service proxies `/api` and `/media` to the API service, so the public domain needs one HTTPS entry point. Terraform can create a global external Application Load Balancer in front of `case-theory-stg-frontend`, with a fixed IPv4 address, HTTP-to-HTTPS redirect, and a Google-managed certificate for `case-researcher.com` and `www.case-researcher.com`. This is disabled until `STAGING_CUSTOM_DOMAIN` is set. A load balancer has ongoing Google Cloud charges; review the Terraform plan and [pricing](https://cloud.google.com/load-balancing/pricing) before enabling it.

## Rollout

1. Run **Terraform staging** with `apply=true` while `STAGING_CUSTOM_DOMAIN` is unset. This grants the apply account the Compute permissions needed for the load balancer. Allow several minutes for IAM propagation.
2. Set the GitHub repository Actions variable `STAGING_CUSTOM_DOMAIN=case-researcher.com`. Run **Terraform staging** again with `apply=true`. The plan should add the load balancer and certificate. The apply output `custom_domain_ipv4` is the address to use in DNS.
3. In the HostGator Customer Portal, open **Domains → case-researcher.com → DNS**. Replace the parking-page A record for `@` with an A record pointing to `custom_domain_ipv4`. Add an A record for `www` with the same address. Leave NS, MX, TXT, and mail-related records alone. The Google-managed certificate becomes active after both names resolve to the load balancer; this can take time.
4. Once `https://case-researcher.com` loads the app, set the GitHub repository Actions variable `STAGING_FRONTEND_ORIGIN=https://case-researcher.com`. Run **Terraform staging** again to update GCS CORS, then run **Deploy staging** to update the API's `FRONTEND_URL` and future migration jobs. Scheduled case jobs receive the new origin on the Terraform apply.
5. Verify the homepage, sign in, a case page, evidence upload, `www.case-researcher.com`, and HTTP-to-HTTPS redirect. The original `run.app` URLs remain available during the cutover.

HostGator is the DNS provider; the domain registration does not need to move to Google Cloud. Do not point an A or CNAME record directly to the Cloud Run `run.app` URL: Google Cloud must first be configured to accept the custom domain and serve its certificate.
