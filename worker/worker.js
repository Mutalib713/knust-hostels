/**
 * KNUST Hostels — Gemini proxy (Cloudflare Worker)
 * -------------------------------------------------
 * Holds your Gemini API key as a SECRET (never exposed to the browser) and
 * answers chat requests from the directory, grounded ONLY on the hostels the
 * page sends it. Free on Cloudflare Workers + Google AI Studio free tier.
 *
 * Deploy two ways (see worker/README.md): paste this file into the Cloudflare
 * dashboard (easiest, no install), or run `wrangler deploy`.
 * Secret needed:  GEMINI_KEY   (dashboard: Settings → Variables → add secret)
 * Optional var:   GEMINI_MODEL (defaults to gemini-2.0-flash — answers directly.
 *                 gemini-2.5-flash also works but "thinks" first, which can eat
 *                 the reply's token budget unless you raise maxOutputTokens a lot.)
 */

// Origins allowed to call this Worker. Add your own if you rename the repo.
const ALLOWED_ORIGINS = [
  "https://mutalib713.github.io", // your live GitHub Pages site
  "http://localhost:8131",        // local preview
  "http://127.0.0.1:8131",
];

const SYSTEM_PROMPT = `You are Ama, a warm, practical assistant for the KNUST Hostels Directory in Kumasi, Ghana.
RULES:
- Answer ONLY using the hostels in the provided JSON. NEVER invent hostels, prices, phone numbers, distances, or ratings.
- Prices are in Ghana cedis (GHS), per person, per academic year. Distances are straight-line km to KNUST campus.
- Be concise (2-4 sentences) and friendly. When recommending, name 1-3 hostels and say why (price, km to campus, rating, or confirmed contact).
- A "confirmed contact" means the phone number was verified — point it out, it's valuable.
- If nothing in the JSON fits the request, say so plainly and suggest relaxing one filter (wider area or higher budget).
- Plain text only. No markdown tables, no code blocks, no asterisks.`;

function corsHeaders(origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  return {
    "Access-Control-Allow-Origin": allow,
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Vary": "Origin",
  };
}

function json(obj, status, cors) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "Content-Type": "application/json", ...cors },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin);

    if (request.method === "OPTIONS") return new Response(null, { headers: cors });
    if (request.method === "GET") return json({ ok: true, service: "knust-hostel-ai" }, 200, cors);
    if (request.method !== "POST") return json({ error: "POST only" }, 405, cors);

    if (!env.GEMINI_KEY) return json({ error: "Server not configured (missing GEMINI_KEY)" }, 500, cors);

    let body;
    try { body = await request.json(); } catch { return json({ error: "Invalid JSON" }, 400, cors); }

    const message = String(body.message || "").slice(0, 500).trim();
    if (!message) return json({ error: "Empty message" }, 400, cors);
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

    const model = (env.GEMINI_MODEL || "gemini-2.0-flash").trim().replace(/^models\//, "");
    const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_KEY}`;
    // Thinking effort. Gemini 3 (and 2.5) reason before answering, which can eat
    // the output-token budget and truncate the reply. `thinking_level` dials it:
    //   minimal ≈ near-instant — we already send pre-filtered, EXACT hostel data,
    //             so the model is phrasing, not calculating (little reasoning needed)
    //   low | medium | high → progressively more reasoning, slightly slower.
    // Override per deployment with the THINKING_LEVEL env var (no redeploy needed).
    // maxOutputTokens stays generous so even "medium" leaves plenty of room.
    const thinkingLevel = (env.THINKING_LEVEL || "minimal").trim();

    const payload = {
      systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
      contents,
      generationConfig: { temperature: 0.4, maxOutputTokens: 2048 },
      thinkingConfig: { thinking_level: thinkingLevel },
    };

    let res;
    try {
      res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      return json({ error: "Could not reach Gemini" }, 502, cors);
    }
    if (!res.ok) {
      const detail = (await res.text()).slice(0, 300);
      return json({ error: `Gemini ${res.status}`, detail }, 502, cors);
    }

    const data = await res.json();
    const reply = (data?.candidates?.[0]?.content?.parts || [])
      .map((p) => p.text || "")
      .join("")
      .trim();

    return json({ reply: reply || "Sorry, I couldn't come up with an answer — try rephrasing." }, 200, cors);
  },
};
