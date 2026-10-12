# AI providers (OpenRouter & Gemini) — beginner friendly

JobPilot can rewrite your CV and write cover letters using an AI model. This is
**optional**. Here's everything you need to know in plain language.

## Do I even need this?

No. Without any AI key, JobPilot still:
- scans jobs,
- ranks them against your query and CV,
- and produces CV + cover-letter drafts using built-in **templates**.

Adding an AI key just makes the CV/cover-letter writing *smarter* (fully rewritten and
tailored, instead of filled-in templates). Everything else works the same.

## "Isn't the Gemini key paid?"

Common worry, but **no — Google Gemini has a free tier.** The model JobPilot uses by
default, `gemini-1.5-flash`, is free up to a daily request limit that's plenty for
personal use. You only pay if you opt into paid models or exceed free limits. So the
Gemini key you already added on Render costs you nothing at normal usage.

That said, you asked about **OpenRouter**, which is also excellent and gives you a menu
of models. JobPilot now supports **both** — you pick whichever you like.

## Which provider does JobPilot use?

It auto-selects, in this order:

1. **OpenRouter** — if you set `OPENROUTER_API_KEY`.
2. **Gemini** — if you set `GEMINI_API_KEY` (and no OpenRouter key).
3. **Neither** — falls back to free templates.

So if you set *both*, OpenRouter wins. If you want Gemini to be used, leave
`OPENROUTER_API_KEY` empty.

## Option 1 — OpenRouter (free models)

1. Go to <https://openrouter.ai> and sign up (GitHub/Google login works).
2. Open <https://openrouter.ai/keys> and click **Create Key**. Copy it (starts with
   `sk-or-...`).
3. In Render: your service → **Environment** → **Add Environment Variable**:
   - Key: `OPENROUTER_API_KEY`
   - Value: *(paste your key)*
4. (Optional) also add `OPENROUTER_MODEL`. Default is a free model:
   `meta-llama/llama-3.1-8b-instruct:free`. Other free models exist — look for the
   `:free` suffix in OpenRouter's model list.
5. Save. Render redeploys automatically. Done.

> Note on free models: OpenRouter's free models have rate limits and can occasionally be
> busy. If a request fails, JobPilot quietly falls back to the template — it never
> crashes. You may need to wait or switch models.

## Option 2 — Gemini (what you already added)

1. Get a key at <https://aistudio.google.com/apikey> (free).
2. In Render: **Environment** → add:
   - Key: `GEMINI_API_KEY`
   - Value: *(your key)*  ← **you already did this**
3. (Optional) `GEMINI_MODEL`, default `gemini-1.5-flash` (free tier).
4. Save → auto-redeploy.

Because you already set `GEMINI_API_KEY` on Render and have **not** set an OpenRouter
key, your live app is currently using **Gemini**. If you later add an OpenRouter key,
it will switch to OpenRouter automatically.

## How to tell which one is active

The home page shows a small banner when **no** AI key is detected ("running in free
template mode"). If you don't see that banner, an AI provider is active. Provider
priority is OpenRouter → Gemini (see above).

## The relevant code (for when you want to peek)

- `app/config.py` — the keys/models and the `active_provider` logic.
- `app/services/llm.py` — `complete()` routes to OpenRouter or Gemini, and returns
  `None` on any failure so the template fallback kicks in.

## Cost summary

| Provider | Free? | Notes |
|----------|-------|-------|
| None (templates) | 100% free | Always works, no key |
| Gemini `*-flash` | Free tier | Daily request limit; fine for personal use |
| OpenRouter `*:free` | Free | Rate-limited; many model choices |

You never have to spend money to use JobPilot.
