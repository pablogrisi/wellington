// ──────────────────────────────────────────────
//  WELLIGTON — UI Prototype
//  API integration points marked with: // [API]
// ──────────────────────────────────────────────

// ─── Suits & Ranks ───
const SUITS = { '♠': 'black', '♣': 'black', '♥': 'red', '♦': 'red' };

// ─── Mock State ───
const MOCK_STATE = {
  deckCount: 32,
  currentTurn: 'human',
  drawnCard: null,
  cutWindow: false,
  players: {
    human: {
      name: 'Você',
      score: null,
      welligton: false,
      cards: [
        { rank: '7', suit: '♥', faceUp: true  },
        { rank: 'K', suit: '♠', faceUp: false },
        { rank: '3', suit: '♦', faceUp: true  },
        { rank: 'J', suit: '♣', faceUp: false },
      ]
    },
    top: {
      name: 'Bot Alfa',
      score: null,
      welligton: false,
      cards: [
        { rank: 'A', suit: '♠', faceUp: false },
        { rank: '9', suit: '♥', faceUp: false },
        { rank: '6', suit: '♦', faceUp: true  },
        { rank: '2', suit: '♣', faceUp: false },
      ]
    },
    left: {
      name: 'Bot Beta',
      score: null,
      welligton: false,
      cards: [
        { rank: '5', suit: '♣', faceUp: false },
        { rank: 'Q', suit: '♦', faceUp: true  },
        { rank: '8', suit: '♠', faceUp: false },
        { rank: '4', suit: '♥', faceUp: false },
      ]
    },
    right: {
      name: 'Bot Gama',
      score: null,
      welligton: false,
      cards: [
        { rank: '10', suit: '♥', faceUp: false },
        { rank: 'J',  suit: '♦', faceUp: false },
        { rank: 'A',  suit: '♣', faceUp: true  },
        { rank: '3',  suit: '♠', faceUp: false },
      ]
    }
  },
  discardTop: { rank: 'Q', suit: '♥' }
};

let gameState = JSON.parse(JSON.stringify(MOCK_STATE));
let logVisible = false;
let cutTimer = null;
let cutSeconds = 3;

// ── Interaction phase ──────────────────────────
// null        = waiting for player action (can draw or declare Welligton)
// 'replace'   = drew a card, clicking own card substitutes it
// 'cut-self'  = cut window open, clicking own card cuts it
// 'cut-other' = cut window open, clicking opponent card cuts it
// 'ability-reveal' = ability panel open, clicking own card reveals it
let phase = null;

// ─── DOM References ───
const els = {
  deck:             document.getElementById('deck'),
  deckCount:        document.getElementById('deck-count'),
  drawnPreview:     document.getElementById('drawn-card-preview'),
  drawnHint:        document.getElementById('drawn-card-hint'),
  discardSlot:      document.getElementById('discard-top-slot'),
  btnWelligton:     document.getElementById('btn-welligton'),
  abilityPanel:     document.getElementById('ability-panel'),
  abilityTitle:     document.getElementById('ability-title'),
  abilityDesc:      document.getElementById('ability-desc'),
  abilityCard:      document.getElementById('ability-card-name'),
  btnAblCancel:     document.getElementById('btn-ability-cancel'),
  cutCountdown:     document.getElementById('cut-countdown'),
  cutTimerEl:       document.getElementById('cut-timer'),
  logPanel:         document.getElementById('game-log'),
  logEntries:       document.getElementById('log-entries'),
  logToggle:        document.getElementById('game-log-toggle'),
  toast:            document.getElementById('toast'),
  phaseBanner:      document.getElementById('phase-banner'),
  turnIndicator:    document.getElementById('turn-indicator'),
  actionHint:       document.getElementById('action-hint'),
};

// ─── Card HTML Builders ───
function buildCardFace(card) {
  if (!card) return '';
  if (card.rank === 'JOKER') {
    return `<div class="card-face joker">
      <div class="card-rank-suit"><span class="card-rank">&#9733;</span><span class="card-suit-top">JOKER</span></div>
      <div class="card-center-suit">&#127183;</div>
      <div class="card-rank-suit-bottom"><span class="card-rank">&#9733;</span><span class="card-suit-top">JOKER</span></div>
    </div>`;
  }
  const color = SUITS[card.suit] || 'black';
  return `<div class="card-face ${color}">
    <div class="card-rank-suit">
      <span class="card-rank">${card.rank}</span>
      <span class="card-suit-top">${card.suit}</span>
    </div>
    <div class="card-center-suit">${card.suit}</div>
    <div class="card-rank-suit-bottom">
      <span class="card-rank">${card.rank}</span>
      <span class="card-suit-top">${card.suit}</span>
    </div>
  </div>`;
}

function buildCardSlot(card, index, playerId, clickable) {
  const slot = document.createElement('div');
  slot.classList.add('card-slot');
  slot.dataset.index = index;
  slot.dataset.player = playerId;

  if (!card) {
    slot.classList.add('empty');
    slot.innerHTML = '<div class="card-inner"></div>';
    return slot;
  }

  if (!card.faceUp) slot.classList.add('face-down');

  slot.innerHTML = `
    <div class="card-inner">
      ${buildCardFace(card)}
      <div class="card-back"></div>
    </div>`;

  if (clickable) {
    slot.setAttribute('tabindex', '0');
    slot.setAttribute('role', 'button');
    slot.setAttribute('aria-label', card.faceUp
      ? `Carta ${card.rank}${card.suit}`
      : 'Carta virada para baixo');
    slot.addEventListener('click', () => onGridCardClick(playerId, index));
    slot.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onGridCardClick(playerId, index); }
    });
  }

  return slot;
}

// ─── Render ───
function renderGrid(gridId, cards, playerId, clickable = false) {
  const grid = document.getElementById(gridId);
  if (!grid) return;
  grid.innerHTML = '';
  cards.forEach((card, i) => grid.appendChild(buildCardSlot(card, i, playerId, clickable)));
}

function renderAll() {
  const isHuman = gameState.currentTurn === 'human';

  // Human cards — always clickable so we can intercept interactions
  renderGrid('grid-human', gameState.players.human.cards, 'human', true);
  renderGrid('grid-top',   gameState.players.top.cards,   'top',   isHuman && gameState.cutWindow);
  renderGrid('grid-left',  gameState.players.left.cards,  'left',  isHuman && gameState.cutWindow);
  renderGrid('grid-right', gameState.players.right.cards, 'right', isHuman && gameState.cutWindow);

  // Discard pile
  if (gameState.discardTop) {
    const inner = els.discardSlot.querySelector('.card-inner');
    if (inner) inner.innerHTML = buildCardFace(gameState.discardTop) + '<div class="card-back"></div>';
    els.discardSlot.classList.remove('face-down');
  }

  // Drawn card preview
  const inner = els.drawnPreview.querySelector('.card-inner');
  if (gameState.drawnCard) {
    if (inner) inner.innerHTML = buildCardFace(gameState.drawnCard) + '<div class="card-back"></div>';
    els.drawnPreview.classList.remove('face-down');
    els.drawnPreview.classList.add('visible');
  } else {
    if (inner) inner.innerHTML = '<div class="card-face"></div><div class="card-back"></div>';
    els.drawnPreview.classList.add('face-down');
    els.drawnPreview.classList.remove('visible');
  }

  // Deck count
  els.deckCount.textContent = gameState.deckCount;

  // Welligton status badges
  ['human','top','left','right'].forEach(pid => {
    const s = document.getElementById(`status-${pid}`);
    if (!s) return;
    if (gameState.players[pid].welligton) {
      s.textContent = 'WELLIGTON LOCKED';
      s.classList.add('locked');
    } else {
      s.classList.remove('locked');
    }
  });

  // Turn indicator
  const turnMap = { human: 'SUA VEZ', top: 'VEZ DO BOT ALFA', left: 'VEZ DO BOT BETA', right: 'VEZ DO BOT GAMA' };
  els.turnIndicator.textContent = turnMap[gameState.currentTurn] || '';

  // Active highlight
  document.querySelectorAll('.player-area').forEach(el => el.classList.remove('active-turn'));
  const activeEl = document.getElementById(`player-${gameState.currentTurn}`);
  if (activeEl) activeEl.classList.add('active-turn');

  // Welligton button
  const canWelligton = isHuman && !gameState.drawnCard && !gameState.players.human.welligton && !gameState.cutWindow;
  els.btnWelligton.disabled = !canWelligton;

  // Deck clickability
  const canDraw = isHuman && !gameState.drawnCard && !gameState.cutWindow;
  els.deck.classList.toggle('disabled', !canDraw);

  refreshHighlights();
  refreshHints();
}

// ─── Highlights (card glow) ───
function refreshHighlights() {
  // Clear all
  document.querySelectorAll('.card-slot').forEach(s => {
    s.classList.remove('selectable', 'selectable-danger');
    els.drawnPreview.classList.remove('discardable');
  });

  if (gameState.currentTurn !== 'human') return;

  if (phase === 'replace') {
    // Own cards are selectable (substitute), drawn card is discardable
    document.querySelectorAll('#grid-human .card-slot:not(.empty)').forEach(s => s.classList.add('selectable'));
    els.drawnPreview.classList.add('discardable');
  }

  if (phase === 'cut-self' || (gameState.cutWindow && !phase)) {
    document.querySelectorAll('#grid-human .card-slot:not(.empty)').forEach(s => s.classList.add('selectable'));
  }

  if (phase === 'cut-other' || (gameState.cutWindow && !phase)) {
    ['grid-top','grid-left','grid-right'].forEach(gid => {
      document.querySelectorAll(`#${gid} .card-slot:not(.empty)`).forEach(s => {
        s.classList.add('selectable', 'selectable-danger');
      });
    });
  }

  if (phase === 'ability-reveal') {
    document.querySelectorAll('#grid-human .card-slot:not(.empty)').forEach(s => s.classList.add('selectable'));
  }
}

// ─── Context hints ───
function refreshHints() {
  const isHuman = gameState.currentTurn === 'human';
  let hint = '';
  let drawnHint = '';

  if (!isHuman) {
    hint = '';
  } else if (gameState.cutWindow) {
    hint = 'Clique em uma carta para cortar — ou aguarde o tempo';
  } else if (phase === 'ability-reveal') {
    hint = 'Clique em uma de suas cartas para revelar';
  } else if (gameState.drawnCard) {
    hint = 'Clique em uma de suas cartas para substituir';
    drawnHint = 'Clique aqui para descartar';
  } else {
    hint = 'Clique no monte para comprar';
  }

  els.actionHint.textContent = hint;
  els.actionHint.classList.toggle('active', !!hint && isHuman);

  els.drawnHint.textContent = drawnHint;
  els.drawnHint.classList.toggle('active', !!drawnHint);
}

// ─── Card click on grid ───
function onGridCardClick(playerId, index) {
  if (gameState.currentTurn !== 'human') return;

  const card = gameState.players[playerId].cards[index];
  if (!card) return;

  // ── After drawing: click own card = substitute; drawn card click = discard (handled separately)
  if (phase === 'replace') {
    if (playerId !== 'human') return;
    // [API] POST /game/replace-card { card_index: index, drawn_card: gameState.drawnCard }
    const replaced = card;
    gameState.players.human.cards[index] = { ...gameState.drawnCard, faceUp: true };
    gameState.discardTop = replaced;
    gameState.drawnCard = null;
    phase = null;
    addLog(`Você substituiu ${replaced.rank}${replaced.suit} pela carta comprada.`);
    renderAll();
    flipCardAnimation('grid-human', index);
    startCutWindow();
    return;
  }

  // ── Cut window: click own card = cut self; click opponent = cut other
  if (gameState.cutWindow) {
    if (playerId === 'human') {
      // [API] POST /game/cut { target_player: 'human', card_index: index }
      addLog(`Você cortou sua própria carta ${card.rank}${card.suit}.`);
      gameState.players.human.cards[index] = null;
      hideCutCountdown();
      endHumanTurn();
    } else {
      // [API] POST /game/cut { target_player: playerId, card_index: index }
      addLog(`Você cortou ${card.rank}${card.suit} de ${gameState.players[playerId].name}.`, true);
      gameState.players[playerId].cards[index] = null;
      hideCutCountdown();
      endHumanTurn();
    }
    renderAll();
    return;
  }

  // ── Ability: click own card = reveal
  if (phase === 'ability-reveal') {
    if (playerId !== 'human') return;
    // [API] POST /game/ability { action: 'reveal', card_index: index }
    gameState.players.human.cards[index].faceUp = true;
    phase = null;
    hideAbilityPanel();
    addLog(`Você revelou ${card.rank}${card.suit}.`, true);
    renderAll();
    flipCardAnimation('grid-human', index);
    return;
  }
}

// ─── Drawn card click = discard ───
els.drawnPreview.addEventListener('click', () => {
  if (phase !== 'replace') return;
  if (!gameState.drawnCard) return;
  // [API] POST /game/discard { card: gameState.drawnCard }
  const card = gameState.drawnCard;
  gameState.discardTop = card;
  gameState.drawnCard = null;
  phase = null;
  addLog(`Você descartou ${card.rank}${card.suit}.`);
  renderAll();
  startCutWindow();
});

els.drawnPreview.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); els.drawnPreview.click(); }
});

// ─── Deck click = draw ───
els.deck.addEventListener('click', () => {
  if (gameState.currentTurn !== 'human') return;
  if (gameState.drawnCard) return;
  if (gameState.cutWindow) return;
  if (els.deck.classList.contains('disabled')) return;

  // [API] POST /game/draw-card
  const mockDraw = { rank: '8', suit: '♦', faceUp: true };
  gameState.drawnCard = mockDraw;
  gameState.deckCount = Math.max(0, gameState.deckCount - 1);
  phase = 'replace';
  addLog('Você comprou uma carta do monte.');
  renderAll();
});

els.deck.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); els.deck.click(); }
});

// ─── Welligton button ───
els.btnWelligton.addEventListener('click', () => {
  if (els.btnWelligton.disabled) return;
  // [API] POST /game/welligton
  gameState.players.human.welligton = true;
  phase = null;
  addLog('Você declarou WELLIGTON!', true);
  showPhaseBanner('WELLIGTON!');
  renderAll();
  endHumanTurn();
});

// ─── Ability Panel ───
els.btnAblCancel.addEventListener('click', () => {
  phase = null;
  hideAbilityPanel();
  addLog('Habilidade cancelada.');
  renderAll();
});

function showAbilityPanel(cardName, title, desc) {
  els.abilityCard.textContent = cardName;
  els.abilityTitle.textContent = title;
  els.abilityDesc.textContent = desc;
  els.abilityPanel.classList.add('visible');
  phase = 'ability-reveal';
  renderAll();
}

function hideAbilityPanel() {
  els.abilityPanel.classList.remove('visible');
}

// ─── Cut Countdown ───
function startCutWindow() {
  cutSeconds = 3;
  gameState.cutWindow = true;
  phase = null;
  els.cutTimerEl.textContent = cutSeconds;
  els.cutTimerEl.classList.remove('urgent');
  els.cutCountdown.classList.add('visible');
  addLog('Janela de corte aberta — 3 segundos!');
  renderAll();

  cutTimer = setInterval(() => {
    cutSeconds--;
    els.cutTimerEl.textContent = cutSeconds;
    if (cutSeconds <= 1) els.cutTimerEl.classList.add('urgent');
    if (cutSeconds <= 0) {
      clearInterval(cutTimer);
      hideCutCountdown();
      addLog('Janela de corte encerrada. Você não cortou.');
      endHumanTurn();
    }
  }, 1000);
}

function hideCutCountdown() {
  clearInterval(cutTimer);
  gameState.cutWindow = false;
  els.cutCountdown.classList.remove('visible');
  renderAll();
}

// ─── End Human Turn (mock bot turns) ───
function endHumanTurn() {
  phase = null;
  gameState.drawnCard = null;

  const botOrder = ['top', 'right', 'left'];
  let delay = 800;

  botOrder.forEach(bot => {
    setTimeout(() => {
      gameState.currentTurn = bot;
      renderAll();
      addLog(`${gameState.players[bot].name} está jogando...`);
    }, delay);

    setTimeout(() => {
      // [API] GET /game/bot-action?player=bot
      const actions = ['comprou e descartou uma carta', 'substituiu uma carta', 'passou a vez'];
      const action = actions[Math.floor(Math.random() * actions.length)];
      addLog(`${gameState.players[bot].name} ${action}.`);
      gameState.deckCount = Math.max(0, gameState.deckCount - 1);
    }, delay + 500);

    delay += 1200;
  });

  setTimeout(() => {
    gameState.currentTurn = 'human';
    renderAll();
    addLog('Sua vez!', true);
  }, delay + 200);
}

// ─── Flip Animation ───
function flipCardAnimation(gridId, index) {
  const slots = document.querySelectorAll(`#${gridId} .card-slot`);
  if (slots[index]) {
    slots[index].classList.remove('face-down');
    slots[index].classList.add('flipping');
    setTimeout(() => slots[index].classList.remove('flipping'), 700);
  }
}

// ─── Game Log ───
function addLog(msg, highlight = false) {
  const el = document.createElement('div');
  el.className = 'log-entry' + (highlight ? ' highlight' : '');
  el.textContent = msg;
  els.logEntries.prepend(el);
  while (els.logEntries.children.length > 40) els.logEntries.lastChild.remove();
}

els.logToggle.addEventListener('click', () => {
  logVisible = !logVisible;
  els.logPanel.classList.toggle('visible', logVisible);
  els.logToggle.title = logVisible ? 'Fechar log' : 'Log do jogo';
});

// ─── Toast ───
let toastTimer = null;
function showToast(msg) {
  els.toast.textContent = msg;
  els.toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => els.toast.classList.remove('show'), 2400);
}

// ─── Phase Banner ───
let bannerTimer = null;
function showPhaseBanner(text) {
  els.phaseBanner.textContent = text;
  els.phaseBanner.classList.add('show');
  clearTimeout(bannerTimer);
  bannerTimer = setTimeout(() => els.phaseBanner.classList.remove('show'), 2000);
}

// ─── Demo: Simulate ability trigger after 3s ───
setTimeout(() => {
  showAbilityPanel(
    'J♦',
    'Valete de Ouros',
    'Selecione uma de suas cartas para revelar seu valor.'
  );
  addLog('Habilidade ativada: Valete de Ouros.', true);
}, 3000);

// ─── Initial Render ───
renderAll();
addLog('Partida iniciada. Boa sorte!', true);
addLog('Você recebeu 4 cartas. 2 estão reveladas.');
addLog('Clique no monte para comprar uma carta.');

// ─── Touch support ───
document.addEventListener('touchstart', () => {}, { passive: true });
