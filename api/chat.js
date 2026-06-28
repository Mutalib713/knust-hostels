/**
 * KNUST Hostels — Gemini proxy (Vercel Serverless Function)
 * ---------------------------------------------------------
 * Holds your Gemini API key as an environment variable (never exposed to the
 * browser) and answers chat requests from the directory, grounded ONLY on the
 * hostels the page sends it. Free on Vercel Hobby + Google AI Studio free tier.
 *
 * Endpoint:  /api/chat   (same origin as the site → no CORS needed)
 * Required env var:  GEMINI_KEY      (Vercel → Project → Settings → Environment Variables)
 * Optional env vars: GEMINI_MODEL    (defaults to gemini-2.0-flash)
 *                    THINKING_LEVEL  (defaults to minimal)
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

  const model = (process.env.GEMINI_MODEL || "gemini-2.0-flash").trim().replace(/^models\//, "");
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${process.env.GEMINI_KEY}`;

  // Thinking effort — Gemini 3 uses thinking_level, Gemini 2.5 uses thinkingBudget.
  // Try the v3 form, fall back to v2.5, then to no thinking control, retrying ONLY
  // when the model rejects the field. minimal ≈ near-instant (data is pre-filtered).
  const thinkingLevel = (process.env.THINKING_LEVEL || "minimal").trim();
  const base = { temperature: 0.4, maxOutputTokens: 2048 };
  const attempts = [
    { ...base, thinkingConfig: { thinking_level: thinkingLevel } },                          // Gemini 3
    { ...base, thinkingConfig: { thinkingBudget: thinkingLevel === "minimal" ? 0 : 512 } },  // Gemini 2.5
    base,                                                                                     // none
  ];
  const callGemini = (genConfig) =>
    fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: SYSTEM_PROMPT }] },
        contents,
        generationConfig: genConfig,
      }),
    });

  let geminiRes;
  try {
    geminiRes = await callGemini(attempts[0]);
    let i = 1;
    while (geminiRes.status === 400 && i < attempts.length) {
      const t = await geminiRes.text();
      if (!/thinking/i.test(t)) return res.status(502).json({ error: "Gemini 400", detail: t.slice(0, 300) });
      geminiRes = await callGemini(attempts[i++]); // model rejected the thinking field — try the next form
    }
  } catch (e) {
    return res.status(502).json({ error: "Could not reach Gemini" });
  }
  if (!geminiRes.ok) {
    const detail = (await geminiRes.text()).slice(0, 300);
    return res.status(502).json({ error: `Gemini ${geminiRes.status}`, detail });
  }

  const data = await geminiRes.json();
  const reply = (data?.candidates?.[0]?.content?.parts || [])
    .map((p) => p.text || "")
    .join("")
    .trim();

  return res.status(200).json({ reply: reply || "Sorry, I couldn't come up with an answer — try rephrasing." });
}
