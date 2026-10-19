(() => {
  "use strict";

  const STORE_KEY = "spellingbee:v1";
  const SHOW_MS = 1500;          // how long the word stays fully visible
  const REQUEUE_AFTER = 6;       // missed words come back after this many rounds
  const HISTORY_MAX = 30;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const coarsePointer = window.matchMedia("(pointer: coarse)").matches;

  const $ = (id) => document.getElementById(id);
  const stage = $("stage"), slot = $("slot"), card = $("card"), cardWord = $("cardWord");
  const input = $("answer"), form = $("answerForm"), goBtn = $("goBtn"), feedback = $("feedback");
  const bee1 = $("bee1"), bee2 = $("bee2"), trail = $("trail");

  const CHEERS = ["Buzz-tastic!", "Bee-autiful!", "Sweet as honey!", "Hive five!", "Un-bee-lievable!", "Wonderful!"];
  const OOPS = ["Not quite!", "Oh, bother!", "So close!", "Buzz-oops!"];

  let words = [];
  let state = null;
  let phase = "idle";            // idle | showing | typing | result
  let current = null;            // index into words
  let lastTyped = "";

  // ---------- Session state ----------

  function shuffled(n) {
    const a = Array.from({ length: n }, (_, i) => i);
    for (let i = n - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [a[i], a[j]] = [a[j], a[i]];
    }
    return a;
  }

  function freshState() {
    return {
      order: shuffled(words.length), pos: 0, round: 0, requeue: [],
      correct: 0, wrong: 0, streak: 0, best: 0, honey: 0,
      history: [], missed: {},
    };
  }

  function loadState() {
    try {
      const s = JSON.parse(sessionStorage.getItem(STORE_KEY));
      if (s && Array.isArray(s.order) && s.order.length === words.length) return s;
    } catch (_) { /* fall through to a fresh session */ }
    return freshState();
  }

  function save() {
    try { sessionStorage.setItem(STORE_KEY, JSON.stringify(state)); } catch (_) { /* storage full or disabled */ }
  }

  function pickNext() {
    state.round++;
    const due = state.requeue.findIndex((r) => r.due <= state.round);
    if (due !== -1) return state.requeue.splice(due, 1)[0].idx;
    if (state.pos >= state.order.length) {
      state.order = shuffled(words.length);
      state.pos = 0;
    }
    return state.order[state.pos++];
  }

  // ---------- Animation ----------

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const clamp01 = (v) => Math.min(1, Math.max(0, v));

  function geometry(bee) {
    const bw = bee.getBoundingClientRect().width || 120;
    const bh = bee.getBoundingClientRect().height || 90;
    const sw = stage.clientWidth;
    const cardLeft = slot.offsetLeft, cardW = slot.offsetWidth;
    const y = slot.offsetTop + slot.offsetHeight / 2 - bh / 2;
    const duration = Math.min(1700, Math.max(1100, sw * 1.6));
    return { bw, sw, cardLeft, cardW, y, duration, from: -bw, to: sw + 10 };
  }

  // Time (ms after launch) at which the bee's nose reaches the card's left edge.
  function leadTime(g) {
    const nose = g.bw * 0.9;
    return g.duration * clamp01((g.cardLeft - g.from - nose) / (g.to - g.from));
  }

  // Fly a bee across the stage; onProgress(p) gets how far its nose is across the card (0..1).
  function fly(bee, onProgress, { flip = false } = {}) {
    const g = geometry(bee);
    bee.style.visibility = "visible";
    return new Promise((resolve) => {
      const start = performance.now();
      const step = (now) => {
        const t = clamp01((now - start) / g.duration);
        const x = g.from + (g.to - g.from) * t;
        const bob = Math.sin(t * Math.PI * 5) * 10;
        const tilt = Math.cos(t * Math.PI * 5) * 6;
        bee.style.transform = `translate(${x}px, ${g.y + bob}px) rotate(${tilt}deg)${flip ? " scaleX(-1)" : ""}`;
        onProgress(clamp01((x + g.bw * 0.9 - g.cardLeft) / g.cardW), x, g.y + bob, g);
        if (t < 1) requestAnimationFrame(step);
        else { bee.style.visibility = "hidden"; resolve(); }
      };
      requestAnimationFrame(step);
    });
  }

  function sparkle(x, y) {
    const s = document.createElement("span");
    s.className = "sparkle";
    s.textContent = Math.random() < 0.5 ? "✨" : "🌼";
    s.style.left = `${x}px`;
    s.style.top = `${y}px`;
    trail.appendChild(s);
    setTimeout(() => s.remove(), 700);
  }

  async function showWord() {
    if (reducedMotion) {
      card.style.clipPath = "inset(0 0 0 0)";
      await sleep(SHOW_MS);
      card.style.clipPath = "inset(0 0 0 100%)";
      return;
    }
    let revealed;
    const fullyShown = new Promise((r) => { revealed = r; });
    const done1 = fly(bee1, (p) => {
      card.style.clipPath = `inset(0 ${(1 - p) * 100}% 0 0)`;
      if (p >= 1) revealed();
    });
    await Promise.race([fullyShown, done1]);
    card.style.clipPath = "inset(0 0 0 0)";

    // launch the wiper so it reaches the card exactly SHOW_MS after the reveal
    const lead = leadTime(geometry(bee2));
    await sleep(Math.max(0, SHOW_MS - lead));
    let lastSpark = 0;
    await Promise.all([done1, fly(bee2, (p, x, y, g) => {
      card.style.clipPath = `inset(0 0 0 ${p * 100}%)`;
      const now = performance.now();
      if (p > 0 && p < 1 && now - lastSpark > 60) {
        lastSpark = now;
        sparkle(x + g.bw * 0.2, y + g.bw * 0.45);
      }
    })]);
  }

  // ---------- Game flow ----------

  async function startRound() {
    current = pickNext();
    save();
    phase = "showing";
    lastTyped = "";
    input.value = "";
    input.className = "";
    input.placeholder = "";
    feedback.innerHTML = "";
    cardWord.textContent = words[current].w;
    card.style.clipPath = "inset(0 100% 0 0)";
    goBtn.disabled = true;
    goBtn.textContent = "Watch closely…";
    // Focus now (inside the tap) so the mobile keyboard is already up when the box appears.
    input.focus({ preventScroll: true });

    await showWord();

    phase = "typing";
    input.placeholder = "Type it here…";
    goBtn.disabled = false;
    goBtn.textContent = "Check ✔";
    input.focus({ preventScroll: true });
  }

  function submit() {
    const typed = input.value.trim().toLowerCase();
    if (!typed) { input.focus(); return; }
    const entry = words[current];
    const ok = typed === entry.w;
    lastTyped = input.value;
    phase = "result";

    if (ok) {
      state.correct++;
      state.streak++;
      state.best = Math.max(state.best, state.streak);
      const gained = 10 + Math.min(state.streak - 1, 10) * 2;
      state.honey += gained;
      $("sHoney").classList.remove("bump");
      void $("sHoney").offsetWidth;
      $("sHoney").classList.add("bump");
      input.className = "good";
      renderFeedback(true, entry, typed, gained);
    } else {
      state.wrong++;
      state.streak = 0;
      state.missed[entry.w] = (state.missed[entry.w] || 0) + 1;
      state.requeue.push({ idx: current, due: state.round + REQUEUE_AFTER });
      input.className = "bad";
      renderFeedback(false, entry, typed, 0);
    }
    state.history.unshift({ w: entry.w, ok, t: typed });
    state.history.length = Math.min(state.history.length, HISTORY_MAX);
    save();
    renderScore();

    goBtn.textContent = "Next word ▶";
    // On phones, drop the keyboard so the feedback is visible; Next re-opens it.
    if (coarsePointer) input.blur();
    else input.focus({ preventScroll: true });
  }

  // Mark the letters of `word` that the attempt didn't get (via longest common subsequence).
  function missedLetters(word, typed) {
    const n = word.length, m = typed.length;
    const dp = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
    for (let i = n - 1; i >= 0; i--)
      for (let j = m - 1; j >= 0; j--)
        dp[i][j] = word[i] === typed[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    const miss = new Array(n).fill(true);
    let i = 0, j = 0;
    while (i < n && j < m) {
      if (word[i] === typed[j]) { miss[i] = false; i++; j++; }
      else if (dp[i + 1][j] >= dp[i][j + 1]) i++;
      else j++;
    }
    return miss;
  }

  const esc = (s) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pick = (a) => a[Math.floor(Math.random() * a.length)];

  function renderFeedback(ok, entry, typed, gained) {
    let html;
    if (ok) {
      html = `<div class="bubble good">
        <div class="title">${pick(CHEERS)} +${gained} 🍯</div>
        <p class="reason"><b>Tip:</b> ${esc(entry.r)}</p>
      </div>`;
    } else {
      const miss = missedLetters(entry.w, typed);
      const letters = [...entry.w].map((c, i) => (miss[i] ? `<span class="miss">${c}</span>` : c)).join("");
      const alts = entry.m.length ? `<p class="alts">Often misspelled as: ${entry.m.map(esc).join(", ")}</p>` : "";
      html = `<div class="bubble bad">
        <div class="title">${pick(OOPS)}</div>
        <div class="word">${letters}</div>
        <div>You wrote: <span class="typed">${esc(typed)}</span></div>
        <p class="reason"><b>Why it's tricky:</b> ${esc(entry.r)}</p>
        ${alts}
      </div>`;
    }
    feedback.innerHTML = html;
  }

  function renderScore() {
    const s = state;
    $("sHoney").textContent = s.honey;
    $("sCorrect").textContent = s.correct;
    $("sWrong").textContent = s.wrong;
    $("sStreak").textContent = s.streak;
    $("sBest").textContent = s.best;
    const total = s.correct + s.wrong;
    $("sAcc").textContent = total ? `${Math.round((s.correct / total) * 100)}%` : "–";
    $("sSeen").textContent = s.pos;
    $("sTotal").textContent = words.length;
    $("sBar").style.width = `${(s.pos / words.length) * 100}%`;

    const hist = $("history");
    hist.innerHTML = s.history.length
      ? s.history.map((h) => `<li class="${h.ok ? "ok" : "no"}"><span>${esc(h.w)}</span><span class="mark">${h.ok ? "✔" : "✘ " + esc(h.t)}</span></li>`).join("")
      : '<li class="empty">Nothing yet — let\'s go!</li>';

    const tricky = Object.entries(s.missed).sort((a, b) => b[1] - a[1]).slice(0, 20);
    $("tricky").innerHTML = tricky.length
      ? tricky.map(([w, n]) => `<li>${esc(w)}${n > 1 ? ` <span class="n">×${n}</span>` : ""}</li>`).join("")
      : '<li class="empty">No misses yet 🌼</li>';
  }

  function goToIdle() {
    phase = "idle";
    feedback.innerHTML = "";
    input.value = "";
    input.className = "";
    card.style.clipPath = "inset(0 100% 0 0)";
    goBtn.disabled = false;
    goBtn.textContent = state.round ? "Keep buzzing!" : "Start buzzing!";
  }

  // ---------- Events ----------

  goBtn.addEventListener("click", () => {
    if (phase === "idle" || phase === "result") startRound();
    else if (phase === "typing") submit();
  });

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    if (phase === "typing") submit();
    else if (phase === "result" || phase === "idle") startRound();
  });

  // No peeking or typing ahead while the word is showing; keep the answer frozen after checking.
  input.addEventListener("input", () => {
    if (phase === "showing" || phase === "idle") input.value = "";
    else if (phase === "result") input.value = lastTyped;
  });
  input.addEventListener("paste", (e) => { if (phase !== "typing") e.preventDefault(); });

  $("resetBtn").addEventListener("click", () => {
    if (phase === "showing") return;
    if (!confirm("Start a new session? Your score and word history will be cleared.")) return;
    state = freshState();
    save();
    renderScore();
    goToIdle();
  });

  // ---------- Boot ----------

  goBtn.disabled = true;
  goBtn.textContent = "Loading words…";
  fetch("words.json")
    .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); })
    .then((data) => {
      words = data;
      state = loadState();
      save();
      renderScore();
      goToIdle();
    })
    .catch(() => {
      goBtn.textContent = "Couldn't load words 😢";
    });
})();
