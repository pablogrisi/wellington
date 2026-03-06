const API = "";
let state = null;
let botStepTimer = null;
let cutAutoPassTimer = null;
let wellingtonWindowTimer = null;
let lastRenderedLogLine = null;
let recentActorId = null;
let wellingtonFlashTimer = null;
let showWellingtonFlash = false;
const uiState = {
  ability7Selection: {
    ownSlot: null,
    targetPlayer: null,
    targetSlot: null,
  },
  ability8Selection: {
    ownSlot: null,
    targetPlayer: null,
    targetSlot: null,
  },
};

const statusEl = document.getElementById("status");
const tableEl = document.getElementById("table");
const controlsEl = document.getElementById("controls");
const logListEl = document.getElementById("log-list");
const pauseBtn = document.getElementById("pause-btn");
const resumeBtn = document.getElementById("resume-btn");
const newGameBtn = document.getElementById("new-game-btn");

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });

  if (!response.ok) {
    let msg = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body?.detail) msg = body.detail;
    } catch (_) {}
    throw new Error(msg);
  }

  return response.json();
}

async function loadState() {
  state = await request("/api/state");
  render();
}

function toastError(err) {
  alert(err.message || String(err));
}

async function action(path, payload = null, options = {}) {
  try {
    state = await request(path, {
      method: "POST",
      body: payload ? JSON.stringify(payload) : undefined,
    });
    render();
  } catch (err) {
    if (options?.suppressError?.(err)) return;
    toastError(err);
  }
}

function render() {
  if (!state) return;
  syncUiStateWithGame();
  renderStatus();
  renderTable();
  renderControls();
  renderLog();
  scheduleCutAutoPass();
  scheduleWellingtonWindowAutoPass();
  scheduleBotStep();
}

function syncUiStateWithGame() {
  const pending = state.pending_ability;
  if (!pending || pending.rank !== "7") {
    uiState.ability7Selection = { ownSlot: null, targetPlayer: null, targetSlot: null };
  }
  if (!pending || pending.rank !== "8") {
    uiState.ability8Selection = { ownSlot: null, targetPlayer: null, targetSlot: null };
  }
}

function scheduleBotStep() {
  if (botStepTimer) {
    clearTimeout(botStepTimer);
    botStepTimer = null;
  }
  if (!state || state.paused || !state.can_bot_step) return;
  // Quando entra a vez do bot, ele compra imediatamente.
  // A espera de 3s fica apenas entre compra e resolucao da jogada.
  const delay = state.pending_bot_turn ? Number(state.bot_delay_ms || 3000) : 0;
  botStepTimer = setTimeout(() => {
    action("/api/bot-step");
  }, delay);
}

function scheduleCutAutoPass() {
  if (cutAutoPassTimer) {
    clearTimeout(cutAutoPassTimer);
    cutAutoPassTimer = null;
  }
  if (!state || state.paused || !state.pending_human_cut) return;
  if (state.current_player === 0 && state.human_cut_available_until_draw) return;
  const delay = Number(state.bot_delay_ms || 3000);
  cutAutoPassTimer = setTimeout(() => {
    action("/api/action/skip-cut", null, {
      suppressError: (err) => String(err?.message || "").includes("Nao ha corte pendente."),
    });
  }, delay);
}

function scheduleWellingtonWindowAutoPass() {
  if (wellingtonWindowTimer) {
    clearTimeout(wellingtonWindowTimer);
    wellingtonWindowTimer = null;
  }
  if (!state || state.paused || !state.pending_human_wellington_window) return;
  if (state.actions?.can_send_cut_other_card) return;
  const delay = Number(state.bot_delay_ms || 3000);
  wellingtonWindowTimer = setTimeout(() => {
    action("/api/action/pass-wellington-window", null, {
      suppressError: (err) =>
        String(err?.message || "").includes("Nao ha janela de Wellington pendente.") ||
        String(err?.message || "").includes("Escolha a carta para enviar"),
    });
  }, delay);
}

function renderStatus() {
  const turnName = state.players[state.current_player]?.name || "-";
  const caller = state.wellington_caller;
  const callerText = caller === null ? "Nao" : state.players[caller].name;
  const drawn = state.drawn_card || "-";
  const pausedText = state.paused ? "Sim" : "Nao";
  const wellingtonAlert =
    caller === null
      ? ""
      : `<div class="wellington-alert"><strong>Wellington ATIVO:</strong> ${state.players[caller].name} pediu Wellington. Ninguem mais pode pedir.</div>`;

  let scoreHtml = "";
  if (state.game_over && Array.isArray(state.scores)) {
    scoreHtml = `<div><strong>Placar final:</strong> ${state.scores
      .map((s) => `${s.name}: ${s.score}`)
      .join(" | ")}</div>`;
  }

  statusEl.innerHTML = `
    <div><strong>Vez:</strong> ${turnName}</div>
    <div><strong>Topo do descarte:</strong> ${state.top_discard || "-"}</div>
    <div><strong>Monte:</strong> ${state.draw_pile_count} cartas</div>
    <div><strong>Carta comprada por voce:</strong> ${drawn}</div>
    <div><strong>Wellington chamado:</strong> ${callerText}</div>
    <div><strong>Pausado:</strong> ${pausedText}</div>
    ${wellingtonAlert}
    ${scoreHtml}
  `;

  if (pauseBtn) pauseBtn.disabled = Boolean(state.paused);
  if (resumeBtn) resumeBtn.disabled = !state.paused;
}

function parseCardText(text) {
  if (!text || text === "--" || text === "??") {
    return { kind: "none" };
  }

  if (text === "JK") {
    return { kind: "joker", rank: "JK", suit: null, red: false, symbolHtml: "JK" };
  }

  const knownRankOnly = text.match(/^(A|K|Q|J|10|[2-9])\?$/);
  if (knownRankOnly) {
    return {
      kind: "rank_only",
      rank: knownRankOnly[1],
      suit: null,
      red: false,
      symbolHtml: "?",
    };
  }

  const full = text.match(/^(A|K|Q|J|10|[2-9])([SHDC])$/);
  if (!full) {
    return { kind: "raw", raw: text };
  }

  const rank = full[1];
  const suit = full[2];
  const suitMap = {
    S: { symbolHtml: "&spades;", red: false },
    H: { symbolHtml: "&hearts;", red: true },
    D: { symbolHtml: "&diams;", red: true },
    C: { symbolHtml: "&clubs;", red: false },
  };

  return {
    kind: "full",
    rank,
    suit,
    symbolHtml: suitMap[suit].symbolHtml,
    red: suitMap[suit].red,
  };
}

function renderCardFace(parsed) {
  if (parsed.kind === "joker") {
    return `
      <div class="card-face joker">
        <div class="card-corner top">JK</div>
        <div class="card-center">JOKER</div>
        <div class="card-corner bottom">JK</div>
      </div>
    `;
  }

  if (parsed.kind === "rank_only") {
    return `
      <div class="card-face rank-only">
        <div class="card-corner top">${parsed.rank}<span class="suit">?</span></div>
        <div class="card-center">${parsed.rank}<span class="suit">?</span></div>
        <div class="card-corner bottom">${parsed.rank}<span class="suit">?</span></div>
      </div>
    `;
  }

  if (parsed.kind === "full") {
    const redClass = parsed.red ? " red" : "";
    return `
      <div class="card-face${redClass}">
        <div class="card-corner top">${parsed.rank}<span class="suit">${parsed.symbolHtml}</span></div>
        <div class="card-center">${parsed.symbolHtml}</div>
        <div class="card-corner bottom">${parsed.rank}<span class="suit">${parsed.symbolHtml}</span></div>
      </div>
    `;
  }

  return `<div class="card-raw">${parsed.raw || "?"}</div>`;
}

function renderTable() {
  tableEl.innerHTML = "";
  updateRecentActorFromLog();

  if (state.game_over && Array.isArray(state.scores) && state.scores.length > 0) {
    const winnerIds = new Set(state.winner_ids || []);
    const winners = state.scores.filter((s) => winnerIds.has(s.player));
    const winnersText = winners.map((w) => w.name).join(", ");
    const winnerScore = winners.length > 0 ? winners[0].score : state.scores[0].score;

    const banner = document.createElement("div");
    banner.className = "winner-banner";
    banner.textContent = `Vencedor${winners.length > 1 ? "es" : ""}: ${winnersText} (${winnerScore} ponto${winnerScore === 1 ? "" : "s"})`;
    tableEl.appendChild(banner);
  }

  const board = document.createElement("div");
  board.className = "table-board";

  const slots = {
    top: [2],
    left: [1],
    right: [3],
    bottom: [0],
  };

  const topSlot = document.createElement("div");
  topSlot.className = "board-slot top";
  slots.top.forEach((id) => topSlot.appendChild(buildPlayerElement(state.players[id], recentActorId === id)));

  const leftSlot = document.createElement("div");
  leftSlot.className = "board-slot left";
  slots.left.forEach((id) => leftSlot.appendChild(buildPlayerElement(state.players[id], recentActorId === id)));

  const rightSlot = document.createElement("div");
  rightSlot.className = "board-slot right";
  slots.right.forEach((id) => rightSlot.appendChild(buildPlayerElement(state.players[id], recentActorId === id)));

  const bottomSlot = document.createElement("div");
  bottomSlot.className = "board-slot bottom";
  slots.bottom.forEach((id) => bottomSlot.appendChild(buildPlayerElement(state.players[id], recentActorId === id)));

  const centerSlot = document.createElement("div");
  centerSlot.className = "board-slot center";
  centerSlot.appendChild(buildCenterPileElement());

  board.appendChild(topSlot);
  board.appendChild(leftSlot);
  board.appendChild(centerSlot);
  board.appendChild(rightSlot);
  board.appendChild(bottomSlot);

  tableEl.appendChild(board);

  if (showWellingtonFlash) {
    const flash = document.createElement("div");
    flash.className = "wellington-call-flash";
    flash.textContent = "Wellington";
    tableEl.appendChild(flash);
  }
}

function buildPlayerElement(p, isRecentActor) {
  const playerEl = document.createElement("article");
  playerEl.className = `player ${p.id === 0 ? "me" : ""} ${state.current_player === p.id ? "active-turn" : ""}`;
  if (isRecentActor) playerEl.classList.add("recent-actor");

  const scoreMap = new Map((state.scores || []).map((item) => [item.player, item.score]));
  const playerScore = scoreMap.has(p.id) ? scoreMap.get(p.id) : null;
  const winnerIds = new Set(state.winner_ids || []);
  const isWinner = state.game_over && winnerIds.has(p.id);

  const badges = [];
  if (state.current_player === p.id) badges.push('<span class="badge active">Vez</span>');
  if (p.locked) badges.push('<span class="badge locked">Travado</span>');
  if (state.wellington_caller === p.id) badges.push('<span class="badge wellington">Wellington</span>');
  if (state.game_over && playerScore !== null) badges.push(`<span class="badge score">Pontos: ${playerScore}</span>`);
  if (isWinner) badges.push('<span class="badge winner">Vencedor</span>');

  playerEl.innerHTML = `
    <div class="player-head">
      <div><strong>${p.name}</strong> ${p.is_bot ? "(bot)" : "(voce)"}</div>
      <div>${badges.join(" ")} <span class="badge">${p.card_count} cartas</span></div>
    </div>
    <div class="player-body">
      <div class="cards"></div>
      <div class="bot-draw-zone" data-player="${p.id}"></div>
    </div>
  `;

  const cardsEl = playerEl.querySelector(".cards");
  const botVisual = p.bot_visual || { side: null, slot_discarded: null };
  p.cards.forEach((c) => {
    const card = document.createElement("div");
    let cls = "card";
    if (c.is_empty) cls += " empty";
    else if (!c.known) cls += " unknown";
    card.className = cls;
    const slotDiscarded = p.is_bot && Number.isInteger(botVisual.slot_discarded) && botVisual.slot_discarded === c.slot;

    if (slotDiscarded) {
      card.classList.add("slot-discarded");
      card.innerHTML = `<div class="slot">slot ${c.slot}</div><div class="discarded-mark">DESCARTOU</div>`;
    } else if (c.is_empty) {
      card.innerHTML = `<div class="slot">slot ${c.slot}</div><div class="empty-mark">vazio</div>`;
    } else if (!c.known) {
      card.innerHTML = `<div class="slot">slot ${c.slot}</div><div class="back-mark" aria-hidden="true"></div>`;
    } else {
      const parsed = parseCardText(c.text);
      card.innerHTML = `<div class="slot">slot ${c.slot}</div>${renderCardFace(parsed)}`;
    }

    const interactionBlocked = c.is_empty || slotDiscarded;
    applyAbilityCardInteraction(card, p.id, c.slot, interactionBlocked);
    applyCutCardInteraction(card, p.id, c.slot, interactionBlocked);
    applyReplaceCardInteraction(card, p.id, c.slot, interactionBlocked);
    cardsEl.appendChild(card);
  });

  const drawZoneEl = playerEl.querySelector(".bot-draw-zone");
  if (p.is_bot) {
    renderBotDrawZone(drawZoneEl, botVisual);
  } else {
    drawZoneEl.remove();
  }

  return playerEl;
}

function renderBotDrawZone(container, botVisual) {
  if (!container) return;
  const side = botVisual?.side || null;
  if (!side) {
    container.innerHTML = "";
    return;
  }
  if (side === "drawn") {
    container.innerHTML = `<div class="bot-side-card"><div class="back-mark" aria-hidden="true"></div></div>`;
    return;
  }
  if (side === "discarded") {
    container.innerHTML = `<div class="bot-side-card discarded"><div class="discarded-mark">DESCARTOU</div></div>`;
    return;
  }
  container.innerHTML = "";
}

function applyAbilityCardInteraction(cardEl, playerId, slot, isEmpty) {
  if (state.paused) return;
  const pending = state.pending_ability;
  if (!pending || isEmpty) return;

  if (pending.rank === "5") {
    if (playerId !== 0) return;
    cardEl.classList.add("clickable-card");
    cardEl.addEventListener("click", async () => {
      await action("/api/action/ability", { data: { slot } });
    });
    return;
  }

  if (pending.rank === "6") {
    cardEl.classList.add("clickable-card");
    cardEl.addEventListener("click", async () => {
      await action("/api/action/ability", { data: { target_player: playerId, slot } });
    });
    return;
  }

  if (pending.rank === "7") {
    applyAbility7CardInteraction(cardEl, playerId, slot);
    return;
  }

  if (pending.rank === "8") {
    applyAbility8CardInteraction(cardEl, playerId, slot);
  }
}

function applyAbility7CardInteraction(cardEl, playerId, slot) {
  const selected = uiState.ability7Selection;
  const isOwn = playerId === 0;
  const isLockedTarget = !isOwn && Boolean(state.players[playerId]?.locked);
  const isSelectedOwn = isOwn && selected.ownSlot === slot;
  const isSelectedTarget = !isOwn && selected.targetPlayer === playerId && selected.targetSlot === slot;

  if (isLockedTarget) {
    cardEl.classList.add("disabled-card");
    cardEl.title = "Jogador travado por Wellington";
    cardEl.addEventListener("click", () => {
      toastError(new Error("Esse jogador ja chamou Wellington e esta travado. Escolha outro alvo."));
    });
    return;
  }

  cardEl.classList.add("clickable-card");
  if (isSelectedOwn || isSelectedTarget) {
    cardEl.classList.add("selected-card");
  }

  cardEl.addEventListener("click", () => {
    if (isOwn) {
      selected.ownSlot = selected.ownSlot === slot ? null : slot;
      if (selected.ownSlot === null) {
        selected.targetPlayer = null;
        selected.targetSlot = null;
      }
      render();
      return;
    }

    selected.targetPlayer =
      selected.targetPlayer === playerId && selected.targetSlot === slot ? null : playerId;
    selected.targetSlot = selected.targetPlayer === null ? null : slot;
    render();
  });
}

function applyAbility8CardInteraction(cardEl, playerId, slot) {
  const pending = state.pending_ability;
  if (!pending || pending.rank !== "8") return;

  const selected = uiState.ability8Selection;
  const isOwn = playerId === 0;
  const isLockedTarget = !isOwn && Boolean(state.players[playerId]?.locked);
  const isSelectedOwn = isOwn && selected.ownSlot === slot;
  const isSelectedTarget = !isOwn && selected.targetPlayer === playerId && selected.targetSlot === slot;

  if (isLockedTarget) {
    cardEl.classList.add("disabled-card");
    cardEl.title = "Jogador travado por Wellington";
    cardEl.addEventListener("click", () => {
      toastError(new Error("Esse jogador ja chamou Wellington e esta travado. Escolha outro alvo."));
    });
    return;
  }

  cardEl.classList.add("clickable-card");
  if (isSelectedOwn || isSelectedTarget) {
    cardEl.classList.add("selected-card");
  }

  cardEl.addEventListener("click", async () => {
    if (isOwn) {
      selected.ownSlot = selected.ownSlot === slot ? null : slot;
      if (selected.ownSlot === null) {
        selected.targetPlayer = null;
        selected.targetSlot = null;
      }
      render();
      return;
    }

    selected.targetPlayer =
      selected.targetPlayer === playerId && selected.targetSlot === slot ? null : playerId;
    selected.targetSlot =
      selected.targetPlayer === null ? null : slot;

    render();

    if (selected.ownSlot === null || selected.targetPlayer === null || selected.targetSlot === null) {
      return;
    }

    await action("/api/action/ability", {
      data: {
        preview: true,
        own_slot: selected.ownSlot,
        target_player: selected.targetPlayer,
        target_slot: selected.targetSlot,
      },
    });
  });
}

function applyCutCardInteraction(cardEl, playerId, slot, isEmpty) {
  if (state.paused) return;
  if (isEmpty) return;

  // Fase 2 do corte com carta de outro: clique em carta sua para enviar.
  if (state.actions?.can_send_cut_other_card) {
    if (playerId !== 0) return;
    cardEl.classList.add("clickable-card");
    cardEl.addEventListener("click", async () => {
      await action("/api/action/cut-other", {
        target_player: -1,
        target_slot: -1,
        give_slot: slot,
      });
    });
    return;
  }

  if (!state.actions?.can_cut) return;

  // Corte normal: clique (ou arraste) em carta sua.
  if (playerId === 0) {
    cardEl.classList.add("clickable-card");
    cardEl.draggable = true;
    cardEl.addEventListener("click", async () => {
      await action("/api/action/cut-self", { slot });
    });
    cardEl.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("cut_slot", String(slot));
      event.dataTransfer.effectAllowed = "move";
    });
    return;
  }

  // Corte com carta de outro: clique direto na carta alvo.
  cardEl.classList.add("clickable-card");
  cardEl.addEventListener("click", async () => {
    await action("/api/action/cut-other", {
      target_player: playerId,
      target_slot: slot,
    });
  });
}

function applyReplaceCardInteraction(cardEl, playerId, slot, isEmpty) {
  if (state.paused) return;
  if (!state.actions?.can_discard_drawn || state.current_player !== 0 || playerId !== 0 || isEmpty) return;

  cardEl.classList.add("clickable-card");
  cardEl.draggable = true;
  cardEl.addEventListener("click", async () => {
    await action("/api/action/replace", { slot });
  });
  cardEl.addEventListener("dragstart", (event) => {
    event.dataTransfer.setData("replace_slot", String(slot));
    event.dataTransfer.effectAllowed = "move";
  });
}

function buildCenterPileElement() {
  const center = document.createElement("div");
  center.className = "table-center";

  const drawEl = document.createElement("div");
  drawEl.className = "pile";
  if (!state.paused && state.actions?.can_draw) {
    drawEl.classList.add("clickable");
    drawEl.title = "Clique para comprar";
    drawEl.addEventListener("click", () => action("/api/action/draw"));
  }
  drawEl.innerHTML = `
    <div class="pile-label">Monte (${state.draw_pile_count})</div>
    <div class="pile-card draw"><div class="back-mark" aria-hidden="true"></div></div>
  `;

  const discardEl = document.createElement("div");
  discardEl.className = "pile";
  const top = state.top_discard ? renderCardFace(parseCardText(state.top_discard)) : '<div class="card-raw">-</div>';
  discardEl.innerHTML = `
    <div class="pile-label">Descarte</div>
    <div class="pile-card discard ${state.actions?.can_cut ? "cut-drop-target" : ""} ${recentActorId !== null ? "recent-play" : ""}">${top}</div>
  `;
  if (!state.paused && (state.actions?.can_cut || state.actions?.can_discard_drawn)) {
    const dropTarget = discardEl.querySelector(".pile-card.discard");
    if (state.actions?.can_discard_drawn && !state.actions?.can_cut) {
      dropTarget.classList.add("cut-drop-target");
    }
    dropTarget.addEventListener("dragover", (event) => {
      event.preventDefault();
      dropTarget.classList.add("drag-over");
    });
    dropTarget.addEventListener("dragleave", () => {
      dropTarget.classList.remove("drag-over");
    });
    dropTarget.addEventListener("drop", async (event) => {
      event.preventDefault();
      dropTarget.classList.remove("drag-over");
      if (state.actions?.can_cut) {
        const cutSlot = Number(event.dataTransfer.getData("cut_slot"));
        if (!Number.isNaN(cutSlot)) {
          await action("/api/action/cut-self", { slot: cutSlot });
          return;
        }
      }
      if (state.actions?.can_discard_drawn) {
        const replaceSlot = Number(event.dataTransfer.getData("replace_slot"));
        if (!Number.isNaN(replaceSlot)) {
          await action("/api/action/replace", { slot: replaceSlot });
        }
      }
    });
  }

  const drawnEl = document.createElement("div");
  drawnEl.className = "pile";
  const drawnFace = state.drawn_card
    ? renderCardFace(parseCardText(state.drawn_card))
    : '<div class="card-raw">-</div>';
  drawnEl.innerHTML = `
    <div class="pile-label">Sua compra</div>
    <div class="pile-card drawn ${state.drawn_card ? "filled" : ""}">${drawnFace}</div>
  `;
  if (!state.paused && state.actions?.can_discard_drawn) {
    drawnEl.classList.add("clickable");
    drawnEl.title = "Clique para descartar a carta comprada";
    drawnEl.addEventListener("click", () => action("/api/action/discard-drawn"));
  }

  center.appendChild(drawEl);
  center.appendChild(discardEl);
  center.appendChild(drawnEl);
  return center;
}

function renderControls() {
  controlsEl.innerHTML = "";

  const base = document.createElement("div");
  base.className = "control-row";

  base.appendChild(makeBtn("Comprar carta", () => action("/api/action/draw"), !state.actions.can_draw));
  base.appendChild(makeBtn("Descartar comprada", () => action("/api/action/discard-drawn"), !state.actions.can_discard_drawn));
  base.appendChild(makeBtn("Chamar Wellington", () => action("/api/action/call-wellington"), !state.actions.can_call_wellington, "danger"));
  controlsEl.appendChild(base);

  if (state.paused) {
    const pausedRow = document.createElement("div");
    pausedRow.className = "control-row";
    pausedRow.appendChild(makeText("Jogo pausado: todas as jogadas estao bloqueadas ate clicar em Retomar."));
    controlsEl.appendChild(pausedRow);
    return;
  }

  if (state.pending_human_wellington_window) {
    const row = document.createElement("div");
    row.className = "control-row";
    row.appendChild(makeText("Janela de Wellington: voce tem 3s para chamar Wellington; depois a vez passa automaticamente."));
    controlsEl.appendChild(row);
  }

  if (state.wellington_caller !== null) {
    const row = document.createElement("div");
    row.className = "control-row";
    row.appendChild(
      makeText(
        `Wellington ja foi chamado por ${state.players[state.wellington_caller].name}. Os outros jogadores nao podem chamar.`
      )
    );
    controlsEl.appendChild(row);
  }

  if (state.actions.can_discard_drawn) {
    const row = document.createElement("div");
    row.className = "control-row";
    row.appendChild(makeText("Com carta comprada: clique numa carta sua ou arraste para o descarte para substituir."));
    controlsEl.appendChild(row);
  }

  if (state.actions?.can_cut) {
    const cutBox = document.createElement("div");
    cutBox.className = "control-row";
    if (state.current_player === 0) {
      if (state.human_cut_available_until_draw) {
        cutBox.appendChild(makeText("Corte disponivel ate voce comprar. Clique na carta (sua ou de outro jogador) ou arraste sua carta para o descarte."));
      } else {
        cutBox.appendChild(makeText("Corte pendente: voce tem 3s para agir (depois passa automaticamente)."));
      }
    } else {
      cutBox.appendChild(makeText("Corte pendente: voce tem 3s para agir (depois passa automaticamente)."));
    }

    const selfSlots = state.cut_options?.self_slots || [];
    selfSlots.forEach((slot) => {
      cutBox.appendChild(makeBtn(`Cortar com meu slot ${slot}`, () => action("/api/action/cut-self", { slot }), false, "primary"));
    });
    controlsEl.appendChild(cutBox);

    const otherTargets = state.cut_options?.other_targets || [];
    otherTargets.slice(0, 8).forEach((opt) => {
      const row = document.createElement("div");
      row.className = "control-row";
      row.appendChild(makeText(`Corte com carta de ${state.players[opt.target_player].name} slot ${opt.target_slot}:`));
      row.appendChild(
        makeBtn(
          "Tentar corte",
          () =>
            action("/api/action/cut-other", {
              target_player: opt.target_player,
              target_slot: opt.target_slot,
            })
        )
      );
      controlsEl.appendChild(row);
    });
  }

  if (state.actions?.can_send_cut_other_card) {
    const row = document.createElement("div");
    row.className = "control-row";
    row.appendChild(makeText("Corte confirmado. Clique em uma carta sua para enviar ao jogador alvo:"));
    const sendSlots = state.actions?.send_cut_other_slots || [];
    sendSlots.forEach((slot) => {
      row.appendChild(
        makeBtn(
          `Enviar meu slot ${slot}`,
          () =>
            action("/api/action/cut-other", {
              target_player: -1,
              target_slot: -1,
              give_slot: slot,
            }),
          false,
          "primary"
        )
      );
    });
    controlsEl.appendChild(row);
  }

  if (state.pending_ability) {
    const ab = state.pending_ability;
    const row = document.createElement("div");
    row.className = "control-row";
    row.appendChild(makeText(`Habilidade ${ab.rank} pendente.`));

    if (ab.rank === "5") {
      row.appendChild(makeText("Habilidade 5: clique em uma carta sua para revelar."));
    }

    if (ab.rank === "6") {
      row.appendChild(makeText("Habilidade 6: clique em qualquer carta para revelar."));
    }

    if (ab.rank === "7") {
      const sel = uiState.ability7Selection;
      const own = sel.ownSlot === null ? "-" : `slot ${sel.ownSlot}`;
      const target =
        sel.targetPlayer === null ? "-" : `${state.players[sel.targetPlayer].name} slot ${sel.targetSlot}`;
      row.appendChild(makeText(`Habilidade 7: clique em 1 carta sua e 1 de outro jogador (nao travado). Selecionado: sua ${own} / alvo ${target}.`));
      const ready = sel.ownSlot !== null && sel.targetPlayer !== null && sel.targetSlot !== null;
      row.appendChild(
        makeBtn(
          "Trocar cartas selecionadas",
          () => action("/api/action/ability", {
            data: {
              own_slot: sel.ownSlot,
              target_player: sel.targetPlayer,
              target_slot: sel.targetSlot,
            },
          }),
          !ready,
          "primary"
        )
      );
    }

    if (ab.rank === "8") {
      const helper = document.createElement("small");
      const sel = uiState.ability8Selection;
      const own = sel.ownSlot === null ? "-" : `slot ${sel.ownSlot}`;
      const target =
        sel.targetPlayer === null ? "-" : `${state.players[sel.targetPlayer].name} slot ${sel.targetSlot}`;
      helper.textContent = `Clique em 1 carta sua e 1 carta de outro jogador (nao travado) para revelar. Selecionado: sua ${own} / alvo ${target}.`;
      row.appendChild(helper);

      if (state.pending_ability8_preview) {
        row.appendChild(
          makeBtn(
            "Trocar cartas reveladas",
            () => action("/api/action/ability", { data: { do_swap: true } }),
            false,
            "primary"
          )
        );
        row.appendChild(
          makeBtn(
            "Nao trocar",
            () => action("/api/action/ability", { data: { do_swap: false } })
          )
        );
      }
    }

    controlsEl.appendChild(row);
  }

  if (state.game_over) {
    const finalRow = document.createElement("div");
    finalRow.className = "control-row";
    finalRow.appendChild(makeText("Partida finalizada."));
    controlsEl.appendChild(finalRow);
  }
}

function renderLog() {
  logListEl.innerHTML = "";
  (state.log || []).slice().reverse().forEach((line) => {
    const el = document.createElement("div");
    el.className = "log-item";
    el.textContent = line;
    logListEl.appendChild(el);
  });
}

function updateRecentActorFromLog() {
  const lines = state.log || [];
  const latest = lines.slice(-1)[0] || null;
  if (!latest) {
    recentActorId = null;
    lastRenderedLogLine = null;
    return;
  }
  if (latest === lastRenderedLogLine) return;
  lastRenderedLogLine = latest;

  recentActorId = null;
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (line.startsWith("Voce ")) {
      recentActorId = 0;
      break;
    }
    if (line.startsWith("Bot 1 ")) {
      recentActorId = 1;
      break;
    }
    if (line.startsWith("Bot 2 ")) {
      recentActorId = 2;
      break;
    }
    if (line.startsWith("Bot 3 ")) {
      recentActorId = 3;
      break;
    }
  }

  if (latest.includes("chamou Wellington")) {
    triggerWellingtonFlash();
  }
}

function triggerWellingtonFlash() {
  showWellingtonFlash = true;
  if (wellingtonFlashTimer) {
    clearTimeout(wellingtonFlashTimer);
    wellingtonFlashTimer = null;
  }
  wellingtonFlashTimer = setTimeout(() => {
    showWellingtonFlash = false;
    render();
  }, 1400);
}

function makeBtn(label, onClick, disabled = false, cls = "") {
  const btn = document.createElement("button");
  btn.textContent = label;
  if (cls) btn.classList.add(cls);
  btn.disabled = disabled;
  btn.addEventListener("click", onClick);
  return btn;
}

function makeText(txt) {
  const span = document.createElement("small");
  span.textContent = txt;
  return span;
}

newGameBtn.addEventListener("click", () => action("/api/new-game"));
pauseBtn.addEventListener("click", () => action("/api/pause"));
resumeBtn.addEventListener("click", () => action("/api/resume"));

loadState().catch(toastError);


