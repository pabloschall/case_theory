# Scheduled YouTube Shorts

The scheduled reel job runs at 04:00 and 16:00 UTC. Each run selects the highest-interest public, fully researched case that has not already received an automated reel. It creates a source-constrained short script from the current case overview, generates symbolic portrait backgrounds, synthesizes AI narration, mixes one of the two bundled landing tracks quietly beneath the voice, renders a 1080×1920 MP4 with scene text, and ends with `case-researcher.com` for four seconds. The music alternates between morning and evening slots and fades out during the final two seconds.

The rendered MP4 is saved in private object storage before upload. YouTube publication uses an OAuth refresh token and the resumable `videos.insert` protocol. Each upload receives a unique case description, source links, the site URL, an AI-media disclosure, up to two hashtags derived from the case title and location, and the fixed `#CaseResearcher` brand hashtag. A database row records the schedule slot, processing status, object key, YouTube video ID, URL, error, and publication time. The unique schedule slot prevents duplicate uploads when Cloud Scheduler retries a run.

The video and YouTube description disclose AI-generated narration and imagery. Background prompts require symbolic, non-graphic editorial scenes without real-person likenesses or readable generated text.

## Required configuration

```dotenv
OPENAI_API_KEY=...
AI_TEXT_MODEL=gpt-5-mini
AI_IMAGE_MODEL=gpt-image-2.5-flare
AI_SPEECH_MODEL=gpt-4o-mini-tts
AI_SPEECH_VOICE=cedar
YOUTUBE_CLIENT_ID=...
YOUTUBE_CLIENT_SECRET=...
YOUTUBE_REFRESH_TOKEN=...
YOUTUBE_CHANNEL_ID=...
YOUTUBE_REDIRECT_URI=http://localhost:8000/api/v1/integrations/youtube/callback
YOUTUBE_PRIVACY_STATUS=public
REEL_SITE_LABEL=case-researcher.com
REEL_MUSIC_VOLUME=0.10
REEL_VIDEO_PERSON_GENERATION=allow_adult
```

`REEL_VIDEO_PERSON_GENERATION=allow_adult` lets Veo render adults and faces. The script and negative prompt still
prohibit identifiable recreations of real case participants. If Veo filters a scene, the job retries it as an empty,
object-based reconstruction before falling back to a generated still image.

The Google OAuth grant must include `https://www.googleapis.com/auth/youtube.upload` for publishing and `https://www.googleapis.com/auth/youtube.readonly` for verifying the destination channel. YouTube may restrict uploads from an unaudited API project to private visibility until the project passes its compliance audit.

After configuring the client ID, client secret, and redirect URI, sign in to the application as an administrator and open `/api/v1/integrations/youtube/connect`. Approve access using the Google account that owns the destination channel. The callback verifies and displays the authorized channel, then displays the refresh token and stable channel ID once while preventing the response from being cached. Confirm the channel is `@CaseResearcher`, then store both values in `.env` locally and in the production secret store; do not commit them.

Before issuing the production refresh token, set the Google OAuth app's publishing status to **In production**.
Refresh tokens from an external app in **Testing** expire after seven days when the app requests YouTube scopes.
After changing the publishing status, complete the authorization flow again and replace the old refresh token in the
production secret store. Existing testing-mode tokens do not become permanent automatically.

## Local verification

These commands use the backend container, which includes FFmpeg:

```bash
make preview-reel  # script only; no database write, rendering, or upload
make render-reel   # create and store an MP4 without YouTube upload
make publish-reel  # complete production path
```

## Staging activation

Add secret versions for `youtube-client-id`, `youtube-client-secret`, `youtube-refresh-token`, and `youtube-channel-id`. Set the GitHub repository variable `ENABLE_SCHEDULED_REELS=true` and apply the reviewed Terraform plan. The job uses the same immutable backend image setting as scheduled case generation.
