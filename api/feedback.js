/**
 * KNUST Hostels — feedback / contact relay (Vercel Serverless Function)
 * --------------------------------------------------------------------
 * Receives a short message from the site's "Message the owner" form and delivers it
 * to the owner. Pick ONE delivery channel by setting env vars in Vercel:
 *
 *   Telegram (instant, free):  FEEDBACK_TELEGRAM_TOKEN  + FEEDBACK_TELEGRAM_CHAT_ID
 *   Email via Web3Forms:       FEEDBACK_WEB3FORMS_KEY   (emails the address on the key)
 *
 * If both are set, Telegram wins. If neither is set, the endpoint reports "not configured".
 * Endpoint: /api/feedback  (same origin as the site → no CORS needed)
 */
export default async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");

  if (req.method === "OPTIONS") return res.status(204).end();
  if (req.method !== "POST") return res.status(405).json({ error: "POST only" });

  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch { return res.status(400).json({ error: "Invalid JSON" }); }
  }
  body = body || {};

  // Honeypot: bots fill the hidden "website" field; humans never do. Pretend success.
  if (body.website) return res.status(200).json({ ok: true });

  const message = String(body.message || "").slice(0, 2000).trim();
  if (message.length < 2) return res.status(400).json({ error: "Empty message" });
  const name = String(body.name || "").slice(0, 80).trim();
  const contact = String(body.contact || "").slice(0, 120).trim();
  const page = String(body.page || "").slice(0, 200).trim();

  const text =
    `📩 New KNUST Hostels message\n\n${message}\n\n` +
    `— from: ${name || "anonymous"}${contact ? ` (${contact})` : ""}` +
    (page ? `\npage: ${page}` : "");

  const tgToken = process.env.FEEDBACK_TELEGRAM_TOKEN;
  const tgChat = process.env.FEEDBACK_TELEGRAM_CHAT_ID;
  const w3key = process.env.FEEDBACK_WEB3FORMS_KEY || "64d8f535-9c86-4060-ad42-4e67720bf8b3"; // Web3Forms public key → emails mosman40@st.knust.edu.gh

  try {
    if (tgToken && tgChat) {
      const r = await fetch(`https://api.telegram.org/bot${tgToken}/sendMessage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ chat_id: tgChat, text, disable_web_page_preview: true }),
      });
      if (!r.ok) return res.status(502).json({ error: "Telegram delivery failed", detail: (await r.text()).slice(0, 200) });
      return res.status(200).json({ ok: true });
    }
    if (w3key) {
      const r = await fetch("https://api.web3forms.com/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({
          access_key: w3key,
          subject: "New KNUST Hostels message",
          from_name: name || "KNUST Hostels visitor",
          replyto: /\S+@\S+\.\S+/.test(contact) ? contact : undefined,
          name: name || "anonymous",
          contact,
          page,
          message,
        }),
      });
      if (!r.ok) return res.status(502).json({ error: "Email delivery failed", detail: (await r.text()).slice(0, 200) });
      return res.status(200).json({ ok: true });
    }
    return res.status(500).json({ error: "Feedback not configured" });
  } catch (e) {
    return res.status(502).json({ error: "Could not deliver message" });
  }
}
