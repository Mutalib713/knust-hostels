# Ama AI — Gemini + Cloudflare Worker (free)

This turns the on-page assistant into a **real conversational AI**, for **$0**, without ever exposing an API key in the website.

```
Browser (your site)  ──►  Cloudflare Worker (holds the key)  ──►  Google Gemini
   filters the 532                 worker.js                       writes the reply
   hostels locally,        (free, ~100k req/day)                  (free tier)
   sends matches + Q
```

The page sends Gemini **only the hostels it already filtered**, so answers stay grounded (no invented prices/contacts) and token use is tiny.

---

## Step 1 — Get a free Gemini API key (2 min)

1. Go to **https://aistudio.google.com/apikey** (sign in with any Google account).
2. Click **Create API key** → copy it (looks like `AIza...`).

Free tier is generous (plenty for a class/portfolio project). No billing required.

## Step 2 — Install the Cloudflare CLI

You need **Node.js** (https://nodejs.org). Then, from this `worker/` folder:

```bash
npm install -g wrangler      # or use: npx wrangler <command>
wrangler login               # opens a browser → create a free Cloudflare account / log in
```

## Step 3 — Add your key as a secret (never committed)

```bash
cd worker
wrangler secret put GEMINI_KEY
# paste your AIza... key when prompted, press Enter
```

## Step 4 — Deploy

```bash
wrangler deploy
```

You'll get a URL like:

```
https://knust-hostel-ai.<your-subdomain>.workers.dev
```

Open it in a browser — you should see `{"ok":true,"service":"knust-hostel-ai"}`.

## Step 5 — Connect it to the site

In **`index.html`**, find this line (inside the Ama script):

```js
const WORKER_URL=""; // ← paste your Cloudflare Worker URL here to enable AI
```

Paste your Worker URL between the quotes, e.g.:

```js
const WORKER_URL="https://knust-hostel-ai.yourname.workers.dev";
```

Save, commit, push. **That's it — Ama now answers with Gemini.** If `WORKER_URL` is empty (or the Worker is unreachable), Ama automatically falls back to the built-in offline keyword search, so the site never breaks.

---

## Test locally first (optional)

```bash
cd worker
wrangler secret put GEMINI_KEY    # (only needed once)
wrangler dev                       # runs at http://localhost:8787
```

Quick check from a terminal:

```bash
curl -X POST http://localhost:8787 \
  -H "Content-Type: application/json" \
  -d '{"message":"cheapest in Ayeduase with a confirmed contact",
       "hostels":[{"name":"Evandy Hostel","area":"Ayeduase","price":2700,"km":1.6,"rating":4.1,"confirmed":true,"phone":"0549678089"}]}'
```

You should get back `{"reply":"..."}`.

---

## Notes & limits

- **Model:** defaults to `gemini-2.0-flash`. If Google changes the free flash model, set `GEMINI_MODEL` in `wrangler.toml` (or check https://aistudio.google.com for the current one).
- **CORS:** `worker.js` allows `https://mutalib713.github.io` and `localhost:8131`. If you fork/rename, edit `ALLOWED_ORIGINS` in `worker.js`.
- **Free tiers (verify current numbers):** Gemini Flash ≈ 15 req/min, ~1,000/day; Cloudflare Workers ≈ 100,000 req/day. Comfortable for a student project.
- **Cost ceiling:** if you ever exceed the Gemini free tier, Flash is extremely cheap; or swap the model in the Worker for Groq/Cloudflare Workers AI with the same shape.
- **Upgrade to Claude later:** point the Worker at the Anthropic API instead (Claude Haiku ≈ $1/$5 per 1M tokens) — same browser code, just change the `fetch` in `worker.js`.
