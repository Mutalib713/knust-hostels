/* QA suite for the "Ask Ama" assistant (run: node test_ama.js)
 *
 * Exercises the SAME engine the site ships (ama-brain.js) against the SAME
 * data (data.js) — run it after every data refresh / pipeline run to be sure
 * the bot still recognises everything:
 *
 *   python kosass_merge.py …    # any data update
 *   node test_ama.js            # bot still knows every hostel? ✔
 *
 * Sections:
 *   1. Full-dataset self-check — EVERY hostel findable by its own name
 *   2. Campus nicknames (Hall 7, Conti, Katanga, Brunei, SRC, GUSSS…)
 *   3. Real student phrasings (questions, pidgin, typos, punctuation)
 *   4. Filter searches (area / price / amenities / college / room type…)
 *   5. Counts + small talk + guardrails
 *   6. Gemini payload check — the right hostels get sent to the AI
 */
'use strict';
global.window = {};
require('./data.js');
const AmaBrain = require('./ama-brain.js');
const H = window.HOSTELS, M = window.META;
const B = AmaBrain.create(H, M);

let pass = 0, fail = 0, section = '';
const failures = [];
function check(name, ok, detail) {
  if (ok) { pass++; }
  else { fail++; failures.push(`[${section}] ${name}${detail ? ' — ' + detail : ''}`); }
}
function head(s) { section = s; console.log('\n== ' + s + ' =='); }

const names = a => (a || []).map(h => h.name).join(' | ');
const cardsMatch = (a, re) => (a.cards || []).some(h => re.test(h.name));
const answerHas = (q, re, label) => {
  const a = B.answer(q);
  check(label || q, cardsMatch(a, re), 'cards: ' + (names(a.cards) || '(none)') + ' | text: ' + (a.text || '').replace(/<[^>]+>/g, '').slice(0, 90));
};

/* Replicates the candidate selection in index.html respond() — i.e. what
 * actually gets sent to Gemini for a question. */
function candidates(q) {
  const a = B.answer(q);
  if (a.meta) return { a, cands: a.cards || [] };
  const cands = (a.cards && a.cards.length) ? a.cards : H.slice().sort((x, y) => (y._pop || 0) - (x._pop || 0)).slice(0, 12);
  return { a, cands };
}

/* ---------- 1. full-dataset self-check ---------- */
head('1. Every hostel findable by its own name (' + H.length + ' places)');
{
  let found = 0; const misses = [];
  for (const h of H) {
    const nm = B.named(h.name);
    if (nm.some(x => x === h)) found++;
    else misses.push(h.name + '  →  ' + (names(nm.slice(0, 3)) || '(nothing)'));
  }
  check('all ' + H.length + ' names resolve to themselves', misses.length === 0, misses.length + ' misses:\n      ' + misses.slice(0, 15).join('\n      '));
  console.log('   found ' + found + '/' + H.length);
  // and phrased as a question, for a sample across the alphabet
  const sample = H.filter((_, i) => i % 23 === 0);
  const qMisses = [];
  for (const h of sample) {
    const nm = B.named('where is ' + h.name.toLowerCase() + ' located?');
    if (!nm.some(x => x === h)) qMisses.push(h.name);
  }
  check('"where is X located?" works for a ' + sample.length + '-hostel sample', qMisses.length === 0, 'misses: ' + qMisses.slice(0, 10).join(' | '));
}

/* ---------- 2. campus nicknames ---------- */
head('2. Campus nicknames & halls');
answerHas('hall 7', /chancellor/i);
answerHas('Hall7', /chancellor/i);
answerHas('hall seven', /chancellor/i);
answerHas("chancellor's hall", /chancellor/i);
answerHas('chancellors hall', /chancellor/i);
answerHas('katanga', /katanga/i);
answerHas('conti', /unity hall/i);
answerHas('continental hall', /unity hall/i);
answerHas('unity hall', /unity hall/i);
answerHas('republic hall', /republic/i);
answerHas('queens', /queens hall/i);
answerHas('queen elizabeth hostel', /queen elizabeth/i);
answerHas('africa hall', /africa hall/i);
answerHas('independence hall', /independence/i);
answerHas('brunei', /brunei/i);
answerHas('old brunei', /old brunei/i);
answerHas('gusss', /gusss/i);
answerHas('src hostel', /src/i);
answerHas('otumfuo hostel', /otumfuo/i);
answerHas('tek credit', /tek credit/i);
answerHas('gnat hall', /gnat/i);

/* ---------- 3. real student phrasings ---------- */
head('3. Student phrasings, typos, pidgin');
answerHas('do you have hall 7?', /chancellor/i);
answerHas('is hall 7 in the directory', /chancellor/i);
answerHas('how much is hall 7', /chancellor/i);
answerHas('I want to stay at katanga', /katanga/i);
answerHas('photos of celia royale', /celia royale/i);
answerHas('price of adepa', /adepa/i);
answerHas('adepa contact number', /adepa/i);
answerHas('where is bk hostel', /b\.?\s?k\.?/i);
answerHas('J&J hostel', /j\s*&\s*j|j and j/i);
answerHas('WAGYINGO HOSTEL', /wagyingo/i);
answerHas('abeg any info on hall 7', /chancellor/i, 'pidgin: "abeg any info on hall 7"');
answerHas('victory towers', /victory/i);
// typos → fuzzy "did you mean"
answerHas('adeppa hostel', /adepa/i, 'typo: adeppa → ADEPA');
answerHas('celya royale', /celia royale/i, 'typo: celya → Celia');
answerHas('wagingo hostel', /wagyingo/i, 'typo: wagingo → Wagyingo');
{
  const a = B.answer('adeppa hostel');   // pure typo — no real word overlap with any name
  check('typo reply is phrased as "did you mean"', /did you mean/i.test(a.text) && a.fuzzy === true, a.text);
}

/* ---------- 4. filter searches ---------- */
head('4. Filters: area / price / type / amenities / college');
{
  const a = B.answer('cheapest hostels in ayeduase');
  check('cheapest in Ayeduase → Ayeduase cards, cheapest first',
    (a.cards || []).length > 0 && a.cards.every(h => h.area === 'Ayeduase') &&
    (a.cards[0].price_from || 0) <= (a.cards[a.cards.length - 1].price_from || 1e9), names(a.cards));
}
{
  const a = B.answer('hostels in kotei under 3k');
  check('Kotei under 3k → all Kotei, price ≤ 3000',
    (a.cards || []).length > 0 && a.cards.every(h => h.area === 'Kotei' && h.price_from != null && h.price_from <= 3000), names(a.cards));
}
{
  const a = B.answer('hostels between 2000 and 4000');
  check('between 2000 and 4000', (a.cards || []).length > 0 && a.cards.every(h => h.price_from >= 2000 && h.price_from <= 4000), names(a.cards));
}
{
  const a = B.answer('confirmed hostels near campus');
  check('confirmed near campus', (a.cards || []).length > 0 && a.cards.every(h => h.confirmed), names(a.cards));
}
{
  const a = B.answer('2 in a room in ayeduase');
  check('2-in-a-room in Ayeduase', (a.cards || []).length > 0 && a.cards.every(h => h.area === 'Ayeduase' && (h.rooms || []).some(r => String(r[0]).startsWith('2-'))), names(a.cards));
}
{
  const a = B.answer('hostels with wifi and security');
  check('Wi-Fi + Security amenity filter', (a.cards || []).length > 0 && a.cards.every(h => (h.amenities || []).includes('Wi-Fi') && (h.amenities || []).includes('Security')), names(a.cards));
}
{
  const a = B.answer('hostels for engineering students');
  check('Engineering college filter', (a.cards || []).length > 0 && a.cards.every(h => (h.colleges || []).includes('Engineering')), names(a.cards));
}
{
  const a = B.answer('knust registered hostels');
  check('registered → only KOSASS-registered', (a.cards || []).length > 0 && a.cards.every(h => h.registered), names(a.cards));
}
{
  const a = B.answer('guest houses in bomso');
  check('guest house type + Bomso', (a.cards || []).length > 0 && a.cards.every(h => h.type === 'Guest house & Hotel' && h.area === 'Bomso'), names(a.cards));
}
{
  const a = B.answer('hostels not in ayeduase');
  check('exclusion: NOT in Ayeduase', (a.cards || []).length > 0 && a.cards.every(h => h.area !== 'Ayeduase'), names(a.cards));
}
// every area in the data must be reachable by name (auto-synonyms guard —
// catches a NEW area added by the pipeline that the bot can't parse yet)
{
  const bad = [];
  for (const area of (M.areas || [])) {
    const q = 'hostels in ' + area.toLowerCase().replace(/\(.*?\)/g, '').trim();
    const s = B.parse(q);
    if (!s.areas.includes(area)) bad.push(area);
  }
  check('every area in META parseable (' + (M.areas || []).length + ' areas)', bad.length === 0, 'unparseable: ' + bad.join(', '));
}
// area typo tolerance
{
  const s = B.parse('hostels in ayeduasee');
  check('area typo: ayeduasee → Ayeduase', s.areas.includes('Ayeduase'), JSON.stringify(s.areas));
}

/* ---------- 5. counts, small talk, guardrails ---------- */
head('5. Counts, small talk, guardrails');
{
  const a = B.answer('how many hostels are there in total?');
  check('total count uses META total', a.meta === true && a.text.includes(String(M.total)), a.text);
}
{
  const a = B.answer('how many hostels in gaza');
  check('area count answered', a.meta === true && /\d/.test(a.text) && /gaza/i.test(a.text.replace(/<[^>]+>/g, '') + names(a.cards)), a.text);
}
['hi', 'hello', 'good morning', 'ete sen', 'who are you'].forEach(g => {
  const a = B.answer(g);
  check('greeting: "' + g + '"', a.meta === true && /ama/i.test(a.text), a.text.slice(0, 60));
});
{
  const a = B.answer('thanks');
  check('thanks acknowledged', a.meta === true, a.text.slice(0, 60));
}
{
  const a = B.answer('tell me a joke');
  check('off-topic → steer back (no cards, help text)', !(a.cards || []).length, a.text.slice(0, 80));
}
{
  const a = B.answer('');
  check('empty input handled', typeof a.text === 'string' && a.text.length > 0);
}

/* ---------- 6. what Gemini actually receives ---------- */
head('6. Gemini payload (candidate selection)');
[
  ['hall 7', /chancellor/i],
  ['is hall 7 available?', /chancellor/i],
  ['price of adepa', /adepa/i],
  ['brunei', /brunei/i],
  ['cheapest in gaza', /./],
].forEach(([q, re]) => {
  const { cands } = candidates(q);
  check('candidates for "' + q + '" include ' + re, cands.some(h => re.test(h.name)), names(cands.slice(0, 6)));
});
{
  const { a, cands } = candidates('any nice place to stay?');
  check('vague question → popular slice (Gemini still gets data)', cands.length >= 5, 'got ' + cands.length + '; text: ' + (a.text || '').slice(0, 60));
}

/* ---------- summary ---------- */
console.log('\n' + '='.repeat(52));
console.log(`RESULT: ${pass} passed, ${fail} failed  (dataset: ${H.length} places, META ${M.generated})`);
if (failures.length) { console.log('\nFAILURES:'); failures.forEach(f => console.log('  ✗ ' + f)); }
process.exit(fail ? 1 : 0);
