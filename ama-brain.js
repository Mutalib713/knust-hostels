/* AmaBrain — the matching + answer engine behind the "Ask Ama" assistant.
 *
 * Lives OUTSIDE data.js on purpose: every pipeline script rewrites data.js
 * wholesale, so anything stored there would be lost on the next data refresh.
 * The brain instead reads the live dataset at runtime — update data.js (any
 * pipeline run) and the bot automatically knows the new hostels, areas and
 * counts. Nothing here needs regenerating.
 *
 * Dual environment:
 *   browser:  <script src="ama-brain.js"> → window.AmaBrain.create(H, M)
 *   node:     const AmaBrain = require('./ama-brain.js')   (used by test_ama.js)
 */
(function (root, factory) {
  if (typeof module !== 'undefined' && module.exports) module.exports = factory();
  else root.AmaBrain = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  const nrm = s => (s || '').toLowerCase().replace(/[^a-z0-9]/g, '');
  const esc = s => (s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  /* Hand-tuned area synonyms (typos + local names). Areas NOT covered here are
   * auto-added from META.areas in create(), so a brand-new area in the data is
   * recognised without touching this file. */
  const HAND_AREA_SYN = [
    [/ayeduase|ayeduasi|ayiduase|new ?site/, 'Ayeduase'],
    [/kotei|kotie\b/, 'Kotei'],
    [/bomso/, 'Bomso'],
    [/gaza|ghana hostels?/, 'Gaza'],
    [/kentin?krono|kentos|nsenie/, 'Kentinkrono'],
    [/oduom/, 'Oduom'],
    [/boadi|buadi/, 'Boadi'],
    [/anloga/, 'Anloga Junction'],
    [/ayigya|ayija/, 'Ayigya'],
    [/deduako/, 'Deduako'],
    [/oforikrom/, 'Oforikrom'],
    [/anwomaso/, 'Anwomaso'],
    [/gyinyase|gyinase/, 'Gyinyase'],
    [/emena/, 'Emena'],
    [/appiadu/, 'Appiadu'],
    [/susuanso|campus edge/, 'Susuanso (campus edge)'],
    [/on ?campus|\bhalls\b|traditional halls?|school campus|inside knust/, 'On Campus (KNUST)'],
  ];

  const COLLEGE_SYN = [
    [/engineer/, 'Engineering'],
    [/\bscience\b|\bcos\b/, 'Science'],
    [/\bart\b|built environment|architect|cabe/, 'Art & Built Environment'],
    [/business|\bksb\b|humanities|social scien|\blaw\b/, 'Humanities & Social Sciences (KSB)'],
    [/health|medic|pharmac|nursing|\bchs\b/, 'Health Sciences'],
    [/agric|natural resource|\bcanr\b/, 'Agriculture & Natural Resources'],
  ];

  const AMEN_SYN = [
    [/wi-?fi|wi fi|internet|wireless/, 'Wi-Fi'],
    [/air ?cond|conditioned|\bac\b|aircon/, 'Air-conditioned'],
    [/pool|swimming/, 'Pool'],
    [/parking|car ?park/, 'Parking'],
    [/kitchen|kitchenette|cook/, 'Kitchen'],
    [/\bwater\b|borehole/, 'Water'],
    [/security|cctv|guard|gated|surveillance/, 'Security'],
    [/generator|backup|standby|dumsor/, 'Backup power'],
    [/\btv\b|television|dstv/, 'TV'],
    [/study room|reading room|study area/, 'Study room'],
    [/self[- ]?contain/, 'Self-contained'],
    [/laundry/, 'Laundry service'],
    [/gym|fitness/, 'Fitness center'],
    [/restaurant|canteen/, 'Restaurant'],
  ];

  /* Campus nicknames students actually use → a phrase that appears in the stored
   * hostel name. Resolution happens against the LIVE dataset, so if a hall is
   * renamed in data.js the alias simply follows (or gracefully finds nothing). */
  const ALIASES = [
    [/\bhall ?(7|seven)\b/, 'hall 7'],                 // Chancellor's Hall (Hall 7)
    [/\bchancell/, 'chancellor'],                       // chancellors / chancellor's
    [/\bconti(nental)?\b/, 'unity hall'],               // Unity Hall = "Conti"
    [/\bkatanga\b/, 'katanga'],                         // University Hall
    [/\brepu\b/, 'republic hall'],
    [/\bindece\b/, 'independence hall'],
    [/\bqueens\b(?!\s+eliza)/, 'queens hall'],          // "Queens" alone = the hall (Queen Elizabeth Hostel is a separate Boadi place)
    [/\bsrc hostel\b|\botumfuo\b/, 'src'],              // Otumfuo Osei Tutu II Hostel (SRC Hostel)
    [/\bgu[s]{1,3}\b/, 'gusss'],                        // GUSSS Hostels (gus/guss/gusss)
    [/\bbrunei\b|\bbruney\b/, 'brunei'],                // Brunei Complex / Old / New / Baby
    [/\btek credit\b|\btek\b/, 'tek'],                  // TEK Credit
  ];

  /* words dropped before name-matching: generic type words, question words, info
   * words and Ghanaian chat filler, so "abeg wey de photos of Celia Royale" still
   * finds the hostel */
  const NAME_STOP = /\b(hostels?|hostle|hotels?|lodges?|lodging|apartments?|inns?|house|homes?|guest|the|an?|is|are|am|was|be|in|at|on|of|for|to|near|by|around|knust|kumasi|please|pls|plz|abeg|chale|charle|dey|wey|na|find|show|tell|give|list|looking|search|want|need|get|book|renting?|me|my|it|about|what|whats|where|which|who|when|how|much|many|located|locate|location|cost|costs|price|prices|priced|do|does|did|you|your|u|have|has|got|any|some|there|here|number|contact|details?|info|stay|place|room|rooms|booking|photos?|pictures?|images?|register|registered|registration|confirmed|verified|available|directory|listed|with|without|ltd|limited|and)\b/g;
  const GEN_WORDS = /\b(hostels?|homestels?|hostle|lodges?|apartments?|court|inns?|hall|residence|guest|house|hotels?|ltd|limited|annex|the|and)\b/g;
  const GENSET = new Set(['hostel', 'hostels', 'homestel', 'homestels', 'hostle', 'lodge', 'lodges', 'apartment', 'apartments', 'court', 'inn', 'inns', 'hall', 'residence', 'guest', 'house', 'hotel', 'hotels', 'ltd', 'limited', 'annex', 'the', 'and', 'tower', 'towers', 'plaza', 'place', 'palace', 'executive', 'block', 'main', 'new', 'site']);

  /* bounded edit distance for typo tolerance ("adeppa" → ADEPA, "celya" → Celia) */
  function lev(a, b, max) {
    if (a === b) return 0;
    const la = a.length, lb = b.length;
    if (Math.abs(la - lb) > max) return max + 1;
    let prev = [], cur = [];
    for (let j = 0; j <= lb; j++) prev[j] = j;
    for (let i = 1; i <= la; i++) {
      cur[0] = i; let best = i;
      for (let j = 1; j <= lb; j++) {
        cur[j] = Math.min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
        if (cur[j] < best) best = cur[j];
      }
      if (best > max) return max + 1;
      const t = prev; prev = cur; cur = t;
    }
    return prev[lb];
  }
  const fuzzyEq = (a, b) => { const mx = Math.min(a, b).length >= 8 ? 2 : 1; return Math.abs(a.length - b.length) <= mx && lev(a, b, mx) <= mx; };

  function create(H, M) {
    H = H || []; M = M || {};

    // popularity score — same formula as the dashboard; computed here too so the
    // brain works standalone (Node tests) where the page hasn't run yet
    if (H.some(h => h._pop === undefined)) {
      let s = 0, n = 0; H.forEach(h => { if (h.rating) { s += h.rating; n++; } });
      const meanR = n ? s / n : 4;
      H.forEach((h, i) => {
        if (h._i === undefined) h._i = i;
        const base = (h.rating || meanR) * Math.log10((h.reviews || 0) + 1);
        h._pop = (h.closed ? base * 0.05 : base) + (h.confirmed ? 0.2 : 0) + (h.images && h.images.length ? 0.1 : 0) + (h.price_from ? 0.1 : 0);
      });
    }

    /* area synonyms = hand list (only those present in the data) + auto-generated
     * regex for any NEW area the pipeline adds later */
    const AREA_SYN = (() => {
      const areas = M.areas || [];
      const syn = HAND_AREA_SYN.filter(([, a]) => areas.includes(a));
      const covered = new Set(syn.map(([, a]) => a));
      areas.forEach(a => {
        if (covered.has(a)) return;
        const w = a.toLowerCase().replace(/\(.*?\)/g, ' ').trim().split(/\s+/).filter(Boolean)[0];
        if (w && w.length >= 3) syn.push([new RegExp('\\b' + w.replace(/[^a-z0-9]/g, '') + '\\b'), a]);
      });
      return syn;
    })();
    const AREA_WORDS = (M.areas || []).map(a => {
      const w = a.toLowerCase().replace(/\(.*?\)/g, ' ').trim().split(/\s+/).filter(Boolean)[0] || '';
      return [w, a];
    }).filter(([w]) => w.length >= 5);

    function parse(t) {
      const s = { areas: [], exAreas: [], college: null, priceMin: null, priceMax: null, confirmed: false, photos: false, near: false, walk: false, best: false, cheapest: false, roomType: null, type: null, minRating: null, amenities: [] };
      AREA_SYN.forEach(([re, a]) => { if (re.test(t) && !s.areas.includes(a)) s.areas.push(a); });
      // typo tolerance for area names ("ayeduasee", "kotai") — only when nothing matched exactly
      if (!s.areas.length) {
        const toks = t.replace(/[^a-z0-9 ]/g, ' ').split(/\s+/).filter(w => w.length >= 5 && !GENSET.has(w));
        const hit = new Set();
        toks.forEach(w => AREA_WORDS.forEach(([aw, a]) => { if (fuzzyEq(w, aw)) hit.add(a); }));
        if (hit.size === 1) s.areas.push([...hit][0]);
      }
      if (/\b(not|except|excluding|besides|outside|other than|apart from|aside from|avoid|away from)\b/.test(t) && s.areas.length) { s.exAreas = s.areas; s.areas = []; } // "NOT in Ayeduase" -> exclude
      AMEN_SYN.forEach(([re, a]) => { if (re.test(t) && !s.amenities.includes(a)) s.amenities.push(a); });
      for (const [re, c] of COLLEGE_SYN) { if (re.test(t) && (M.colleges || []).includes(c)) { s.college = c; break; } }
      s.confirmed = /confirm|verified|trusted|with (a )?(number|contact)|can call|reachable/.test(t);
      s.photos = /photo|picture|image|see inside|\bpics?\b/.test(t);
      s.near = /near|close to|closest|nearest|walking|by campus/.test(t);
      s.walk = /walk(ing)? ?distance|walkable|walk to/.test(t);
      s.best = /best|top[- ]?rated|highly rated|good rating|good review|popular/.test(t);
      s.cheapest = /cheap|cheapest|affordable|budget|low(est)? ?price/.test(t);
      if (/2 ?in ?(a|1|one)|two in|double/.test(t)) s.roomType = '2'; else if (/1 ?in ?(a|1|one)|single/.test(t)) s.roomType = '1'; else if (/3 ?in ?(a|1|one)|three in/.test(t)) s.roomType = '3'; else if (/4 ?in ?(a|1|one)|four in|quad/.test(t)) s.roomType = '4';
      if (/hotel|guest ?house|\blodge\b|lodging|motel|\binn\b/.test(t)) s.type = 'Guest house & Hotel'; else if (/homestel|home ?stay|family home/.test(t)) s.type = 'Homestel (family home)'; else if (/apartment|self[- ]?contain|\bflat\b/.test(t)) s.type = 'Apartment / Self-contained';
      if (/well rated|good rating|4 ?\+|highly rated|top rated/.test(t)) s.minRating = 4;
      const nums = []; t.replace(/(\d[\d,\.]*)\s*(k)?/gi, (m, n, k) => { let v = parseFloat(n.replace(/,/g, '')); if (k) v *= 1000; if (v >= 300) nums.push(Math.round(v)); return m; });
      const between = /between|–|—/.test(t) || /\d\s*(?:-|to)\s*\d/.test(t);
      if (between && nums.length >= 2) { s.priceMin = Math.min(...nums); s.priceMax = Math.max(...nums); }
      else if (/under|below|less than|max|up to|within|cheaper than|budget of|<=?/.test(t) && nums.length) s.priceMax = nums[0];
      else if (/over|above|more than|at least/.test(t) && nums.length) s.priceMin = nums[0];
      else if (/around|about|approximately|~/.test(t) && nums.length) { s.priceMin = Math.round(nums[0] * .85); s.priceMax = Math.round(nums[0] * 1.15); }
      else if (nums.length && /ghs|cedis|budget|price|afford|spend/.test(t)) s.priceMax = nums[0];
      return s;
    }
    const has = s => s.areas.length || s.exAreas.length || s.college || s.priceMin != null || s.priceMax != null || s.confirmed || s.photos || s.near || s.best || s.cheapest || s.roomType || s.type || s.minRating != null || s.amenities.length;

    function search(s) {
      let r = H.filter(h => {
        if (s.areas.length && !s.areas.includes(h.area)) return false;
        if (s.exAreas.length && s.exAreas.includes(h.area)) return false;
        if (s.amenities.length && !s.amenities.every(a => (h.amenities || []).includes(a))) return false;
        if (s.college && !(h.colleges || []).includes(s.college)) return false;
        if (s.confirmed && !h.confirmed) return false;
        if (s.photos && !(h.images && h.images.length)) return false;
        if (s.type && h.type !== s.type) return false;
        if (s.minRating != null && (h.rating || 0) < s.minRating) return false;
        if (s.priceMax != null && (h.price_from == null || h.price_from > s.priceMax)) return false;
        if (s.priceMin != null && (h.price_from == null || h.price_from < s.priceMin)) return false;
        if (s.walk && (h.km_from_knust == null || h.km_from_knust > 2)) return false;
        if (s.roomType && !(h.rooms || []).some(rm => String(rm[0]).indexOf(s.roomType + '-') === 0)) return false;
        return true;
      });
      if (s.cheapest) r.sort((a, b) => (a.price_from || 1e9) - (b.price_from || 1e9));
      else if (s.near) r.sort((a, b) => (a.km_from_knust == null ? 9 : a.km_from_knust) - (b.km_from_knust == null ? 9 : b.km_from_knust));
      else r.sort((a, b) => (b._pop || 0) - (a._pop || 0));
      return r;
    }

    function describe(s, noP) {
      const p = [];
      if (s.type) p.push({ 'Hostel': 'hostels', 'Guest house & Hotel': 'guest houses / hotels', 'Apartment / Self-contained': 'apartments' }[s.type] || '');
      if (s.areas.length) p.push('in ' + s.areas.join(' or '));
      if (s.exAreas.length) p.push('outside ' + s.exAreas.join(' and '));
      if (s.college) p.push('handy for ' + s.college.replace(' (KSB)', '') + ' students');
      if (s.confirmed) p.push('with a confirmed contact');
      if (s.photos) p.push('with photos');
      if (s.amenities.length) p.push('with ' + s.amenities.join(' & '));
      if (s.roomType) p.push(s.roomType + '-in-a-room');
      if (!noP) { if (s.priceMin != null && s.priceMax != null) p.push('between GHS ' + s.priceMin.toLocaleString() + ' and ' + s.priceMax.toLocaleString()); else if (s.priceMax != null) p.push('under GHS ' + s.priceMax.toLocaleString()); else if (s.priceMin != null) p.push('above GHS ' + s.priceMin.toLocaleString()); }
      if (s.walk) p.push('within walking distance'); else if (s.near) p.push('close to campus');
      if (s.minRating) p.push('well rated');
      return p.join(', ');
    }

    function compose(s, res) {
      const d = describe(s);
      if (!res.length) {
        if (s.priceMax != null || s.priceMin != null) { const alt = search(Object.assign({}, s, { priceMin: null, priceMax: null })); if (alt.length) return { text: 'No hostels matched ' + (d || 'that') + ". Only <b>" + M.with_price + '</b> hostels list prices online, so here are ' + Math.min(alt.length, 5) + ' ' + (describe(s, true) || 'options') + ' without the price limit:', cards: alt.slice(0, 5) }; }
        return { text: "I couldn't find hostels " + (d || 'like that') + '. Try another area or a higher budget — or tap a suggestion below.' };
      }
      const n = res.length, show = Math.min(n, 5), ord = s.cheapest ? ' (cheapest first)' : s.near ? ' (closest first)' : s.best ? ' (top rated first)' : ' (most popular first)';
      return { text: 'Found <b>' + n + '</b> hostel' + (n > 1 ? 's' : '') + (d ? ' ' + d : '') + '. Showing ' + show + ord + ':', cards: res.slice(0, show) };
    }

    const coreName = s => nrm(s.toLowerCase().replace(GEN_WORDS, ' '));
    const qCore = t => nrm(t.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(NAME_STOP, ' ').split(/\s+/).filter(Boolean).join(''));

    function named(t) {
      t = t.replace(/['’`]/g, '');
      // tier pre: the whole query IS a hostel name, punctuation aside ("A&D Hostel",
      // "To Be Hotel", "N.A.A Hostel" — names that dissolve into stop-words otherwise)
      const whole = nrm(t);
      if (whole.length >= 2) { const ex = H.filter(h => nrm(h.name) === whole); if (ex.length) { const out = ex.slice(0, 8); out._strong = true; return out; } }
      // tier A: campus nicknames (hall 7, conti, katanga, SRC, brunei…) resolved
      // against the live data — the single most common student phrasing
      const aliasHits = [];
      for (const [re, phrase] of ALIASES) {
        if (!re.test(t)) continue;
        const key = nrm(phrase);
        H.forEach(h => { if (nrm(h.name).indexOf(key) >= 0 && !aliasHits.includes(h)) aliasHits.push(h); });
      }
      if (aliasHits.length) { aliasHits.sort((a, b) => (b._pop || 0) - (a._pop || 0)); const out = aliasHits.slice(0, 8); out._strong = true; return out; }
      // word-based, so even a question ("where is Adepa located?") still finds the hostel name
      const words = t.toLowerCase().replace(/[^a-z0-9 ]/g, ' ').replace(NAME_STOP, ' ').split(/\s+/).filter(w => w.length >= 2 || /^\d+$/.test(w)); // keep numbers ("hall 7") & 2-char names (BK, AG)
      let alljoined = qCore(t);
      if (alljoined.length < 2) alljoined = whole;   // short punctuated names ("A&D") lose everything to stop-words
      // tier 0: exact core-name match — handles short/acronym names (BK, J&J, R&B, AG) & exact names.
      // Sibling records whose core merely CONTAINS the query ("Evandy Hostel KNUST"
      // next to "Evandy Annex") are appended after the exact hits.
      if (alljoined.length >= 2 && alljoined.length <= 7) {
        const ex = H.filter(h => coreName(h.name) === alljoined);
        if (ex.length) {
          ex.sort((a, b) => nrm(a.name).length - nrm(b.name).length);
          if (alljoined.length >= 4) H.forEach(h => { if (!ex.includes(h) && coreName(h.name).indexOf(alljoined) >= 0) ex.push(h); });
          const out = ex.slice(0, 8); out._strong = true; return out;
        }
      }
      if (!words.length) return [];
      const joined = nrm(words.join(''));
      // tier 1: the whole phrase appears in the name (or a short name sits inside the query) —
      // checked on the full name AND on the core name (generic words stripped), so
      // "Fortune Royal Ltd" ⊂ "Fortune Royal Hostel Ltd" and "Sieyha Boadi" ⊂ "SIEYHA HOSTEL BOADI".
      // Rank closest/shortest name first.
      const qc = alljoined;
      let out = H.filter(h => {
        const k = nrm(h.name);
        if ((joined.length >= 3 && k.indexOf(joined) >= 0) || (k.length >= 5 && joined.indexOf(k) >= 0)) return true;
        const c = coreName(h.name);
        return (qc.length >= 3 && c.length >= 3 && (c.indexOf(qc) >= 0 || (c.length >= 5 && qc.indexOf(c) >= 0)));
      });
      if (out.length) { out.sort((a, b) => Math.abs(nrm(a.name).length - joined.length) - Math.abs(nrm(b.name).length - joined.length)); return out.slice(0, 8); }
      // tier 2: distinctive shared whole words (len>=4, or a number like "7"), skipping generic
      // building words (court/hall/tower…) so "adepa court" ranks ADEPA above every "… Court".
      // Prefix check runs BOTH ways so "chancellors" still matches "Chancellor's".
      let dwords = words.filter(w => (w.length >= 4 || /^\d+$/.test(w)) && !GENSET.has(w));
      if (!dwords.length) dwords = words.filter(w => w.length >= 4 || /^\d+$/.test(w));   // fall back if query was ALL generic words
      const sc = [];
      for (const h of H) {
        const nw = h.name.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
        let s = 0; for (const w of dwords) if (nw.some(x => x === w || (w.length >= 4 && x.startsWith(w)) || (x.length >= 4 && w.startsWith(x)))) s++;
        if (s) sc.push([s, h]);
      }                                                    // avoids "allow"->"Hallowed" (needs a whole distinctive word)
      sc.sort((a, b) => b[0] - a[0] || (b[1]._pop || 0) - (a[1]._pop || 0));
      if (sc.length) return sc.slice(0, 8).map(x => x[1]);
      // tier 3: fuzzy word match — catches typos ("adeppa court", "celya royale").
      // Only distinctive words ≥4 chars; edit distance 1 (or 2 for long words).
      const fzw = dwords.filter(w => w.length >= 4 && !GENSET.has(w));
      if (!fzw.length) return [];
      const fz = [];
      for (const h of H) {
        const nw = h.name.toLowerCase().split(/[^a-z0-9]+/).filter(x => x.length >= 4 && !GENSET.has(x));
        let s = 0; for (const w of fzw) if (nw.some(x => fuzzyEq(x, w))) s++;
        if (s) fz.push([s, h]);
      }
      fz.sort((a, b) => b[0] - a[0] || (b[1]._pop || 0) - (a[1]._pop || 0));
      const fout = fz.slice(0, 6).map(x => x[1]); fout._fuzzy = true;
      return fout;
    }

    // is the top named() hit a confident, specific match? (alias, exact core name, or the query phrase sits in the name)
    function nameStrong(t, list) {
      if (!list.length) return false;
      if (list._strong) return true;
      if (list._fuzzy) return false;
      const c = qCore(t), k = nrm(list[0].name);
      if (c.length >= 2 && coreName(list[0].name) === c) return true;                     // exact core name (BK, Adepa, Celia Royale)
      if (c.length >= 4 && (k.indexOf(c) >= 0 || (c.indexOf(k) >= 0 && k.length >= 5))) return true; // query phrase inside the name
      return false;
    }

    function welcome() { return "Hi, I'm <b>Ama</b> — your KNUST hostel finder. Tell me what you're after and I'll search all <b>" + M.total + "</b> hostels. e.g. “confirmed hostels in Ayeduase under 3000” or “cheapest near campus”."; }

    function answer(q) {
      const t = q.toLowerCase().trim();
      if (!t) return { text: 'Tell me what you need — e.g. “cheap hostels in Ayeduase with a confirmed contact”.' };
      if (/^(hi|hello|hey|yo|hiya|good (morning|afternoon|evening)|akwaaba|ete ?sen|maakye|maaha|maadwo)/.test(t) || /who are you|what can you do|how (do|does) (you|this|it) work|help me|^help$/.test(t)) return { text: welcome(), meta: true };
      if (/^(thanks|thank you|thx|medaase|meda wo ase|ok|okay|nice|cool|great|yoo)/.test(t) && t.length < 16) return { text: "Anytime! Ask me about any KNUST hostel — area, budget, confirmed contacts, photos or distance.", meta: true };
      const s = parse(t);
      const nm = named(t);
      const isCount = /\bhow many\b|\bnumber of\b|\bcount\b|how many are/.test(t);
      // a hostel-NAME match wins when there's no real filter (only type/amenities, which are often part of "does X have wifi?")
      const weakFilter = !s.areas.length && !s.exAreas.length && !s.college && s.priceMin == null && s.priceMax == null && !s.confirmed && !s.photos && !s.near && !s.walk && !s.best && !s.cheapest && !s.roomType && s.minRating == null;
      // "real search" signals (want many results) — NOT photos/confirmed/amenities, which are usually asked ABOUT a named place
      const searchFilter = s.areas.length || s.exAreas.length || s.college || s.priceMin != null || s.priceMax != null || s.near || s.walk || s.best || s.cheapest || s.roomType || s.minRating != null;
      const strong = nameStrong(t, nm);   // confident, specific name match ("photos of Celia Royale", "is X confirmed")
      // fuzzy (typo) matches are the least confident — only use them when the message
      // has NO usable filter, so "hostels with wifi" never becomes "did you mean Wini Hostel"
      if (nm.length && !isCount && (nm._fuzzy ? !has(s) : (strong ? !searchFilter : (weakFilter || !has(s))))) {
        if (nm._fuzzy) return { text: "I couldn't find that exact name — did you mean: " + nm.slice(0, 4).map(h => esc(h.name)).join(', ') + '? Tap one below for details.', cards: nm.slice(0, 4), fuzzy: true };
        if (nm.length === 1) { const h = nm[0]; return { text: "Here's <b>" + esc(h.name) + '</b> — ' + esc(h.area) + (h.price_from ? ', from GHS ' + h.price_from.toLocaleString() : '') + (h.rating ? ', ★' + h.rating.toFixed(1) : '') + (h.confirmed ? ', confirmed contact' : '') + '. Tap it for photos, room prices & contact.', cards: [h] }; }
        return { text: 'I found <b>' + nm.length + '</b> matching that — ' + nm.slice(0, 6).map(h => esc(h.name)).join(', ') + '. Tap any for details.', cards: nm.slice(0, 6) };
      }
      if (/\bregist/.test(t)) { const rg = H.filter(h => h.registered); return { text: '<b>' + rg.length + '</b> place' + (rg.length === 1 ? ' is' : 's are') + ' officially <b>KNUST-registered</b> on the KOSASS portal' + (s.areas.length ? ' — filtering to ' + esc(s.areas.join(', ')) : '') + '. Here are some:', cards: (s.areas.length ? rg.filter(h => s.areas.includes(h.area)) : rg).slice(0, 6), meta: true }; }
      if (has(s)) { const res = search(s); if (isCount) return { text: 'There are <b>' + res.length + '</b> hostel' + (res.length === 1 ? '' : 's') + ' ' + (describe(s, true) || 'matching that') + '.', cards: res.slice(0, 6), meta: true }; return compose(s, res); }
      if (isCount || /total hostels|all hostels/.test(t)) return { text: 'There are <b>' + M.total + '</b> hostels here across ' + (M.areas || []).length + ' areas — <b>' + M.confirmed + '</b> with confirmed contacts, <b>' + (M.registered_count || 0) + '</b> KNUST-registered and <b>' + M.with_phone + '</b> with a phone number.', meta: true };
      return { text: "I can search by <b>area</b>, <b>budget</b>, <b>college</b>, <b>confirmed contact</b>, photos, amenities or distance. Try a suggestion below ↓" };
    }

    return { answer, parse, named, search, has, welcome, describe, nameStrong, version: '2.0' };
  }

  return { create };
});
