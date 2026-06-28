/**
 * KNUST Hostels — Gemini proxy (Vercel Serverless Function)
 * ---------------------------------------------------------
 * Holds your Gemini API key as an environment variable (never exposed to the
 * browser) and answers chat requests from the directory, grounded ONLY on the
 * hostels the page sends it. Free on Vercel Hobby + Google AI Studio free tier.
 *
 * Endpoint:  /api/chat   (same origin as the site → no CORS needed)
 * Required env var:  GEMINI_KEY      (Vercel → Project → Settings → Environment Variables)
 * Optional env vars: GEMINI_MODEL           (primary, defaults to gemini-3.5-flash)
 *                    GEMINI_FALLBACK_MODEL  (used when primary is overloaded, defaults to gemini-2.0-flash)
 *                    THINKING_LEVEL         (defaults to minimal)
 *
 * Ported from the old Cloudflare Worker (worker/worker.js).
 */

const SYSTEM_PROMPT = `You are Ama, a warm, practical assistant for the KNUST Hostels Directory in Kumasi, Ghana.
RULES:
- Answer ONLY using the hostels in the provided JSON. NEVER invent hostels, prices, phone numbers, distances, or ratings.
- Prices are in Ghana cedis (GHS), per person, per academic year. Distances are straight-line km to KNUST campus.
- Be concise (2-4 sentences) and friendly. When recommending, name 1-3 hostels and say why (price, km to campus, rating, or confirmed contact).
- A "confirmed contact" means the phone number was verified — point it out, it's valuable.
- If nothing in the JSON fits the request, say so plainly and suggest relaxing one filter (wider area or higher budget).
- Plain text only. No markdown tables, no code blocks, no asterisks.`;

export default async function handler(req, res) {
  // Same-origin calls don't need CORS, but these keep it usable from other domains too.
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method === "GET") return res.status(200).json({ ok: true, service: "knust-hostel-ai" });
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  if (!process.env.GEMINI_KEY) {
    return res.status(500).json({ error: "Server not configured (missing GEMINI_KEY)" });
  }

  // Vercel auto-parses JSON bodies, but guard against strings / missing bodies.
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { return res.status(400).json({ error: "Invalid JSON" }); }
  }
  body = body || {};

  const message = String(body.message || "").slice(0, 500).trim();
  if (!message) return res.status(400).json({ error: "Empty message" });
  const hostels = Array.isArray(body.hostels) ? body.hostels.slice(0, 25) : [];
  const history = Array.isArray(body.history) ? body.history.slice(-6) : [];

  // Build Gemini conversation: prior turns, then context + current question.
  const contents = [];
  for (const h of history) {
    const role = h.role === "model" ? "model" : "user";
    contents.push({ role, parts: [{ text: String(h.text || "").slice(0, 800) }] });
  }
  const context = `Available hostels (JSON):\n${JSON.stringify(hostels)}`;
  contents.push({ role: "user", parts: [{ text: `${context}\n\nUser question: ${message}` }] });

  // Models tried in order: primary first, then a stabler fallback. Google's free tier
  // returns 503 "high demand" for hot new models like gemini-3.5-flash, so we retry the
  // transient overload once, then drop to gemini-2.0-flash so students always get a reply.
  const clean = (m) => m.trim().replace(/^models\//, "");
  const primary = clean(process.env.GEMINI_MODEL || "gemini-3.5-flash");
  const fallback = clean(process.env.GEMINI_FALLBACK_MODEL || "gemini-2.0-flash");
  const models = primary === fallback ? [primary] : [primary, fallback];
  const endpoint = (m) =>
    `https://generativelanguage.googleapis.com/v1beta/models/${m}:generateContent?key=${process.env.GEMINI_KEY}`;

  // Thinking effort — Gemini 3 uses thinking_level, Gemini 2.5 uses thinkingBudget, older
  // flash models take neither. Try the v3 form, fall back to v2.5, then to none, retrying
  // ONLY when the model rejects the field. minimal ≈ near-instant (data is pre-filtered).
  const thinkingLevel = (process.env.THINKING_LEVEL || "minimal").trim();
  const base = { temperature: 0.4, maxOutputTokens: 2048 };
  const genConfigs = [
    { ...base, thinkingConfig: { thinking_level: thinkingLevel } },                          // Gemini 3
    { ...base, thinkingConfig: { thinkingBudget: thinkingLevel === "minimal" ? 0 : 512 } },  // Gemini 2.5
    base,                                                                                     // none
  ];
  // Each call gets an abort timeout so a hanging/overloaded model can't stall the chat —
  // when it fires we move straight to the fallback instead of waiting.
  const callGemini = (m, genConfig, timeoutMs) => {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    return fetch(endpoint(m), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents,
        generationConfig: genConfig,
      }),
      signal: ctrl.signal,
    }).finally(() => clearTimeout(timer));
  };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  // 503/429/500 or an "overloaded / high demand" body = temporary; fall back / retry.
  const isOverloaded = (status, body) =>
    status === 503 || status === 429 || status === 500 || /UNAVAILABLE|overload|high demand/i.test(body || "");

  // Run the thinking-config cascade for one model. Returns { res } — plus { body } when the
  // body was already consumed to inspect a 400 (so the caller doesn't re-read the stream).
  async function tryModel(m, timeoutMs) {
    let r = await callGemini(m, genConfigs[0], timeoutMs);
    let i = 1;
    while (r.status === 400 && i < genConfigs.length) {
      const t = await r.text();
      if (!/thinking/i.test(t)) return { res: r, body: t }; // genuine 400, not the thinking field
      r = await callGemini(m, genConfigs[i++], timeoutMs);
    }
    return { res: r };
  }

  // Fail fast on the (often overloaded) primary, then give the stabler fallback more room
  // plus one retry. Primary timeout tunable via GEMINI_TIMEOUT_MS.
  const primaryTimeout = Number(process.env.GEMINI_TIMEOUT_MS) || 4500;
  const plan = models.map((m, idx) => {
    const isLast = idx === models.length - 1;
    return { m, timeoutMs: isLast ? Math.max(primaryTimeout, 12000) : primaryTimeout, retries: isLast ? 2 : 1 };
  });

  let data;
  let lastErr = { status: 502, detail: "no response" };
  outer: for (const { m, timeoutMs, retries } of plan) {
    for (let attempt = 0; attempt < retries; attempt++) {
      let r;
      try {
        r = await tryModel(m, timeoutMs);
      } catch {
        lastErr = { status: 502, detail: `timeout or network error (${m})` }; // aborted/network → transient
      }
      if (r) {
        if (r.res.ok) { data = await r.res.json(); break outer; }
        const detail = (r.body ?? (await r.res.text())).slice(0, 300);
        lastErr = { status: r.res.status, detail };
        if (!isOverloaded(r.res.status, detail)) break; // genuine error → try next model
      }
      if (attempt < retries - 1) await sleep(400); // only the fallback model retries
    }
  }

  if (!data) {
    return res.status(502).json({ error: `Gemini ${lastErr.status}`, detail: lastErr.detail });
  }

  const reply = (data?.candidates?.[0]?.content?.parts || [])
    .filter((p) => !p.thought)            // never surface internal reasoning, only the final answer
    .map((p) => p.text || "")
    .join("")
    .trim();

  return res.status(200).json({ reply: reply || "Sorry, I couldn't come up with an answer — try rephrasing." });
}
