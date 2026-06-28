// ============================================================================
//  Ama AI — Cloudflare Worker that proxies the KNUST hostel chatbot to Google
//  Gemini. The Gemini API key lives ONLY here as an encrypted secret
//  (env.GEMINI_KEY) and is NEVER sent to the browser.
//
//  Flow:  browser  ->  this Worker (holds key)  ->  Gemini  ->  back to browser
//
//  Deploy: Cloudflare dashboard -> Workers & Pages -> Create Worker ->
//          paste this file -> Settings -> Variables -> add SECRET "GEMINI_KEY".
//  See worker/README.md for the click-by-click guide.
// ============================================================================

// The free Flash model. If AI Studio shows a different current name, change it here.
const MODEL = "gemini-2.5-flash";

// Only these site origins may call the Worker from a browser (blocks casual abuse).
// Add/remove as needed. localhost is for testing the page locally.
const ALLOWED_ORIGINS = [
  "https://mutalib713.github.io",
  "http://localhost:8131",
  "http://127.0.0.1:8131",
];

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";

    // CORS preflight
    if (request.method === "OPTIONS") return cors(new Response(null, { status: 204 }), origin);
    if (request.method !== "POST") return cors(json({ error: "POST only" }, 405), origin);

    // Parse the request from the page: { question, hostels: [ ...compact candidates... ] }
    let body;
    try { body = await request.json(); } catch { return cors(json({ error: "bad json" }, 400), origin); }
    const question = String(body.question || "").slice(0, 500);
    const hostels = Array.isArray(body.hostels) ? body.hostels.slice(0, 30) : [];
    if (!question) return cors(json({ error: "no question" }, 400), origin);

    // Ground the model in ONLY the hostels the page sent (prevents hallucination).
    const system =
      "You are Ama, a warm, practical assistant for the KNUST Hostels Directory in Kumasi, Ghana. " +
      "Answer ONLY using the hostel data in the user's message. Keep it to 2-4 sentences. " +
      "When relevant, recommend specific hostels by name and mention price (GHS), area, and distance to campus. " +
      "Never invent hostels, prices, or phone numbers. If the data doesn't answer the question, say so and suggest how to refine the search. " +
      "When money is involved, remind the user to visit and verify before paying.";

    const dataText = hostels.length
      ? "Matching hostels (JSON):\n" + JSON.stringify(hostels)
      : "No hostels matched the current filters.";

    const payload = {
      systemInstruction: { parts: [{ text: system }] },
      contents: [{ role: "user", parts: [{ text: dataText + "\n\nUser question: " + question }] }],
      generationConfig: { temperature: 0.4, maxOutputTokens: 400 },
    };

    const url =
      "https://generativelanguage.googleapis.com/v1beta/models/" +
      MODEL + ":generateContent?key=" + env.GEMINI_KEY;

    let r;
    try {
      r = await fetch(url, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      return cors(json({ error: "network", detail: String(e) }, 502), origin);
    }

    if (!r.ok) return cors(json({ error: "gemini_" + r.status, detail: await r.text() }, 502), origin);

    const data = await r.json();
    const answer =
      (data.candidates &&
        data.candidates[0] &&
        data.candidates[0].content &&
        data.candidates[0].content.parts &&
        data.candidates[0].content.parts.map((p) => p.text).join("")) ||
      "Sorry, I couldn't generate an answer just now.";

    return cors(json({ answer }), origin);
  },
};

function cors(res, origin) {
  const allow = ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0];
  res.headers.set("Access-Control-Allow-Origin", allow);
  res.headers.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.headers.set("Access-Control-Allow-Headers", "content-type");
  res.headers.set("Vary", "Origin");
  return res;
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: { "content-type": "application/json" },
  });
}
