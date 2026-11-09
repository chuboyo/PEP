# WhatsApp / Meta setup (Slice 9)

Automated tests use the in-memory adapter and do **not** need live Meta credentials. Use this checklist for a manual smoke against the Cloud API.

## Environment variables

| Env var | Source |
| --- | --- |
| `WHATSAPP_TOKEN` | WhatsApp → API Setup temporary token, or a System User permanent token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp → API Setup → Phone number ID |
| `WHATSAPP_APP_SECRET` | App → Settings → Basic → App Secret |
| `WHATSAPP_VERIFY_TOKEN` | Invent a random string; same value in portal webhook config |
| `WHATSAPP_TEMPLATE_START` | Approved start template **name** (default `pep_survey_start`) |
| `WHATSAPP_TEMPLATE_REMINDER` | Approved reminder template **name** (default `pep_survey_reminder`; Slice 10) |

Compose passes these through from the host env (empty → in-memory send adapter).

## Webhook

- Callback URL: `https://<api-host>/api/v1/webhooks/whatsapp`
- Verify token: same as `WHATSAPP_VERIFY_TOKEN`
- Subscribe to `messages`

## Templates

Create two **utility** templates (approve before staging):

1. **Start** (`pep_survey_start`): body params `{{1}}` player name, `{{2}}` questionnaire name; one quick reply with payload **`START`**
2. **Reminder** (`pep_survey_reminder`): same shape and `START` payload

## Manual smoke

1. Invite a player with `phone_e164` in E.164.
2. Assign a questionnaire (no `short_text`) with channel WhatsApp.
3. Player receives start template → taps Start → answers interactive questions → coach dashboard shows a `whatsapp` response.
