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
2. Click **Create API key** → copy it (looks like `AIza...`). No billing required.

## Step 2 — Deploy the Worker (pick ONE route)

### Route A — Cloudflare dashboard (easiest, no installs) ⭐

1. Go to **https://dash.cloudflare.com** → create a free account.
2. **Workers & Pages → Create → Create Worker** → give it a name (e.g. `knust-hostel-ai`) → **Deploy**.
3. Click **Edit code**, delete the sample, **paste the whole of `worker.js`**, then **Deploy**.
4. **Settings → Variables and Secrets → Add → Secret**: name `GEMINI_KEY`, value = your `AIza...` key → **Save and deploy**.
5. Copy the Worker URL at the top, e.g. `https://knust-hostel-ai.yourname.workers.dev`.

### Route B — Command line (wrangler)

Needs **Node.js** (https://nodejs.org). From this `worker/` folder:

```bash
npm install -g wrangler      # or prefix commands with: npx
wrangler login               # opens a browser to create / log in (free)
wrangler secret put GEMINI_KEY   # paste your AIza... key
wrangler deploy                  # prints your Worker URL
```

Either way, open the URL in a browser — you should see `{"ok":true,"service":"knust-hostel-ai"}`.

## Step 3 — Connect it to the site

In **`index.html`**, find this line (inside the Ama script):

```js
const WORKER_URL=""; // ← paste your Cloudflare Worker URL here to enable Gemini AI
```

Paste your Worker URL between the quotes:

```js
const WORKER_URL="https://knust-hostel-ai.yourname.workers.dev";
```

Save, commit, push. **Ama now answers with Gemini.** If `WORKER_URL` is empty (or the Worker is unreachable), Ama automatically falls back to the built-in offline keyword search, so the site never breaks.

---

## Test it quickly

After deploying, from any terminal (matches the site's request shape):

```bash
curl -X POST https://knust-hostel-ai.yourname.workers.dev \
  -H "Content-Type: application/json" \
  -d '{"message":"cheapest in Ayeduase with a confirmed contact",
       "hostels":[{"name":"Evandy Hostel","area":"Ayeduase","price":2700,"km":1.6,"rating":4.1,"confirmed":true,"phone":"0549678089"}]}'
```

You should get back `{"reply":"..."}`.

(Route B only) run it locally with `wrangler dev` → `http://localhost:8787`.

---

## Notes & limits

- **Request/response shape** (what the page and Worker agree on): page POSTs
  `{ message, history, hostels }`; Worker returns `{ reply }`. Keep these in
  sync if you edit either side.
- **Model:** defaults to `gemini-2.0-flash`, which answers directly. You can
  override it with a `GEMINI_MODEL` variable (dashboard, or `[vars]` in
  `wrangler.toml`). Note: `gemini-2.5-flash` "thinks" before replying, which
  eats the output-token budget and can truncate answers — if you use it, raise
  `maxOutputTokens` in `worker.js` to ~1500.
- **CORS:** `worker.js` allows `https://mutalib713.github.io` and
  `localhost:8131`. If you fork/rename, edit `ALLOWED_ORIGINS` in `worker.js`.
- **Free tiers (verify current numbers):** Gemini Flash ≈ 15 req/min, ~1,000/day;
  Cloudflare Workers ≈ 100,000 req/day. Comfortable for a student project.
- **Upgrade to Claude later:** point the Worker at the Anthropic API instead
  (Claude Haiku ≈ $1/$5 per 1M tokens) — same browser code, just change the
  `fetch` call in `worker.js`.
