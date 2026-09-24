# EILLEN User Tier Plan

This document is the working plan for EILLEN user tiers. It should be reviewed before tier rules are implemented in the database, backend permissions, and frontend.

## Tier definitions

| Tier | Working name | Purpose |
|---|---|---|
| Tier 0 | Admin | Platform administration, moderation, and unrestricted product access |
| Tier 1 | Free | Read-only access to selected public case material |
| Tier 2 | Investigator | Paid collaboration tools and private manual cases |
| Tier 3 | Lead Investigator | Full investigation workspace with AI research and generation |

## Display behavior

- **Available** means the user can open and use the feature.
- **Read only** means the user can inspect the feature but cannot add or change content.
- **List only** means the user can see that records exist but cannot open their detail, preview, download, or attachment actions.
- **Visible — upgrade required** means the control or tab remains visible. Clicking it explains which tier is required.
- Admins use Tier 0. Tier 0 is a special unrestricted tier and is not numerically compared with paid tiers.
- Backend permissions remain authoritative. A locked frontend control never grants access by itself.

## Proposed feature matrix

| Feature | Tier 0 — Admin | Tier 1 — Free | Tier 2 — Investigator | Tier 3 — Lead Investigator |
|---|---|---|---|---|
| Browse and search public cases | Available | Available | Available | Available |
| Open public case overview | Available | Available | Available | Available |
| View public summary | Available | Available | Available | Available |
| View public timeline | Available | Available | Available | Available |
| View public map locations | Available | Available | Available | Available |
| View public people list | Available | Visible — upgrade required | Available | Available |
| View public discussions | Available | Read only | Available | Available |
| See public evidence list | Available | List only | Available | Available |
| Open evidence detail | Available | Visible — upgrade required | Available | Available |
| Preview or download evidence files | Available | Visible — upgrade required | Available | Available |
| Open external evidence links | Available | Visible — upgrade required | Available | Available |
| Follow or unfollow a public case | Available | Available | Available | Available |
| Use My Desk | Available | Available | Available | Available |
| Use Messenger | Available | Visible — upgrade required | Available | Available |
| Edit own profile and profile picture | Available | Available | Available | Available |
| Block or unblock another user | Available | Available | Available | Available |
| Report a comment, evidence item, or user | Available | Available | Available | Available |
| Invite a friend through text or email | Available | Visible — upgrade required | Available | Available |
| Create a public case manually | Available | Visible — upgrade required | Available | Available |
| Write a manual case summary | Available | Visible — upgrade required | Available | Available |
| Select a template case banner | Available | Visible — upgrade required | Available | Available |
| Create a private case manually | Available | Visible — upgrade required | Available | Available |
| Change a public case to private | Available | Visible — upgrade required | Available | Available |
| Create a case with AI | Available — unlimited | Available — 1 lifetime public-case trial | Available — 2 per day | Available — 5 per day |
| Run AI research on an existing case | Available | Visible — upgrade required | Visible — upgrade required | Available |
| Initial AI summary during case creation | Available | Included with lifetime trial | Included within daily limit | Included within daily limit |
| Initial AI timeline during case creation | Available | Included with lifetime trial | Included within daily limit | Included within daily limit |
| Initial AI case banner during case creation | Available | Included with lifetime trial | Included within daily limit | Included within daily limit |
| Review and edit initial AI overview | Available | Available for trial case | Available | Available |
| Approve or reject initial AI timeline suggestions | Available | Available for trial case | Available | Available |
| Regenerate a section during initial review | Available | 1 per section for trial case | 1 per section for each new case | 1 per section for each new case |
| Publish an AI-created case after review | Available | Available for trial case | Available | Available |
| Regenerate an AI case summary | Available | Visible — upgrade required | Visible — upgrade required | Available |
| Regenerate an AI timeline | Available | Visible — upgrade required | Visible — upgrade required | Available |
| Regenerate an AI case banner | Available | Visible — upgrade required | Visible — upgrade required | Available |
| Browse official research sources | Available | Visible — upgrade required | Available | Available |
| Browse FBI records | Available | Visible — upgrade required | Available | Available |
| Import an FBI record as a draft case | Available | Visible — upgrade required | Available | Available |
| View own private notes workspace | Available | Available — read only | Available | Available |
| Add or edit own private notes | Available | Visible — upgrade required | Available | Available |
| View own private timeline workspace | Available | Available — read only | Available | Available |
| Add or edit own timeline entries | Available | Visible — upgrade required | Available | Available |
| Add map locations | Available | Visible — upgrade required | Available | Available |
| Add people | Available | Visible — upgrade required | Available | Available |
| Link people and evidence to case items | Available | Visible — upgrade required | Available | Available |
| Create discussion threads | Available | Visible — upgrade required | Available | Available |
| Comment and react in discussions | Available | Visible — upgrade required | Available | Available |
| Upload evidence files | Available | Visible — upgrade required | Available | Available |
| Add evidence links | Available | Visible — upgrade required | Available | Available |
| Invite case collaborators | Available | Visible — upgrade required | Available | Available |
| Manage case collaborators | Available | Visible — upgrade required | Available | Available |
| Approve contributed timeline events | Available | Visible — upgrade required | Available | Available |
| Approve contributed evidence | Available | Visible — upgrade required | Available | Available |
| Manage people relationships | Available | Visible — upgrade required | Available | Available |
| Publish or unpublish manually created cases | Available | Visible — upgrade required | Available | Available |
| Open a private-case invitation while signed out | Sign in required | Sign in or account creation required | Sign in or account creation required | Sign in or account creation required |
| Accept a private-case invitation | Available | Available | Available | Available |
| Access private cases through an invitation | Available | Read only | Available | Available |
| Access Admin area | Available | Hidden | Hidden | Hidden |
| Delete any case | Available | Not available | Not available | Not available |
| Moderate reports and users | Available | Not available | Not available | Not available |
| Manage plans and tier assignments | Available | Not available | Not available | Not available |

## Proposed limits

The values below are placeholders for review. They should be stored in the database rather than scattered through application code.

| Limit | Tier 0 — Admin | Tier 1 — Free | Tier 2 — Investigator | Tier 3 — Lead Investigator |
|---|---:|---:|---:|---:|
| Active owned cases | Unlimited | 1 AI trial case | 5 | 20 |
| Private owned cases | Unlimited | 0 | 5 | 20 |
| AI-created cases | Unlimited | 1 lifetime | 2 per day | 5 per day |
| Additional AI research runs on existing cases | Unlimited | 0 | 0 | 20 per month |
| Included initial-review regenerations | Unlimited | 1 per generated section on trial case | 1 per generated section on each new case | 1 per generated section on each new case |
| AI usage/cost budget | Unlimited | Trial budget — value to be decided | Daily budget — value to be decided | Daily and monthly budget — value to be decided |
| Storage | Unlimited | 0 | 5 GB | 25 GB |
| Collaborators per case | Unlimited | 0 | 10 | 30 |

## Rules to preserve during implementation

1. Every feature should use a named backend permission such as `case.private` or `ai.research`.
2. Tier numbers should describe product levels, but application code should authorize actions through permissions.
3. Tier 0 should be handled explicitly as Admin because zero is not a lower-access tier.
4. Locked product features should remain visible to Tier 1 and Tier 2 users unless the feature is administrative.
5. Selecting a locked feature should open a short explanation with the required tier and an upgrade action.
6. The backend must return a consistent upgrade-required error if a user bypasses the frontend.
7. Case roles and subscription tiers remain separate. An invitation can grant access to a private case without granting the ability to create private cases.
8. Changing a user's tier must not remove or publish existing private cases automatically.
9. Tier 1 API access is read only for ordinary case content. The backend must reject manual case creation, new case objects, uploads, reactions, invitations, and messaging. Following cases and the specific trial-case review actions below are explicit exceptions.
10. Evidence returned to Tier 1 must contain safe list metadata only. File URLs, external links, signed URLs, and detail endpoints must remain inaccessible.
11. Links to evidence from timelines, discussions, maps, or people must render as locked references for Tier 1.
12. A private-case invitation never grants anonymous access. The recipient must sign in or create an account before accepting it.
13. After registration or login, the recipient should return directly to the pending invitation instead of losing the invitation flow.
14. Accepting an invitation adds the private case to the recipient's workspace. Tier 1 access remains read only and follows the same overview, timeline, discussion, map, and evidence-list restrictions.
15. The Tier 1 AI trial is the only exception to the rule that Free users cannot create cases. It creates one public case and can never be reset by deleting that case.
16. AI case-creation limits must be enforced server-side using persisted usage records. Browser state and frontend counters are not authoritative.
17. Tier 2 and Tier 3 daily limits reset at 00:00 UTC. The UI should display the remaining allowance and next reset time. A failed run should not consume quota unless a case and research job were successfully created.
18. Initial summary, timeline, and banner generation belong to the same AI case-creation run and consume one case-creation allowance, not separate allowances.
19. A verified email is required before starting the Tier 1 lifetime AI trial.
20. The lifetime trial is recorded in a persisted usage ledger and cannot be restored by deleting the case, deleting a research job, or changing browsers.
21. Each AI-created case includes one regeneration per generated section during its initial review. These regenerations do not consume another case allowance, but they count toward the user's AI cost budget.
22. AI quotas must include a provider-cost or token budget in addition to case counts so an unusually expensive research run can be stopped safely.
23. If a user downgrades, existing private cases and content remain stored and keep their current privacy. Editing becomes read only until the user upgrades again.
24. A Tier 1 user may edit the generated overview, approve or reject initial timeline suggestions, use the included review regenerations, and publish the one trial case. After initial review, all other Tier 1 creation restrictions apply.
25. Reporting is a safety function available to every signed-in account. A report enters moderator review and does not by itself hide content or lock another account.
26. Only administrators can hide reported content, restore it, lock or unlock an account pending review, and resolve or dismiss a report. These actions must be retained in the moderation audit history.

## Decisions reflected in this draft

- Tier 1 cannot create cases manually or create private cases.
- As a single exception, a verified Tier 1 member receives one lifetime AI-created public case.
- During the trial case's initial review, Tier 1 can edit the generated overview, approve or reject timeline suggestions, regenerate each generated section once, and publish the result.
- After initial review, the trial case follows normal Tier 1 read-only restrictions unless the user upgrades.
- Tier 1 cannot manually create, upload, link, comment, react, invite, or message.
- Tier 1 can follow public cases and use My Desk.
- Tier 1 can view public case overviews, summaries, timelines, discussions, and maps.
- Tier 1 can see the public evidence list but cannot open evidence detail, external evidence links, previews, or downloads.
- Tier 1 sees locked options and receives a Tier 2 upgrade explanation when selecting them.
- Private case creation begins at Tier 2.
- Tier 2 can create up to two cases with AI per day.
- Tier 3 can create up to five cases with AI per day.
- Admin AI case creation is unlimited.
- Re-running AI research and regenerating individual AI sections remain Tier 3 features for now.
- Tier 2 and Tier 3 daily allowances reset at 00:00 UTC.
- AI use is constrained by both creation counts and a separate provider-cost budget.
- Downgrading never publishes, deletes, or changes the privacy of an existing case; restricted content becomes read only.
- Invited Tier 1 users can view the permitted sections of a private case but cannot contribute objects or messages.
- A signed-out invitation recipient must log in or create an account before the private case is revealed.
- After authentication, the recipient returns to the invitation, accepts it, and the private case is added to their workspace.
- Editing an account profile and blocking users remain available at every tier as account and safety functions.
