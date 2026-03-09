/**
 * WELLIGTON - Game Client
 * Connects to FastAPI backend
 */

// ─── API Configuration ───
const API = "";

// ─── State ───
let state = null;
let botStepTimer = null;
let cutAutoPassTimer = null;
let wellingtonWindowTimer = null;
let logVisible = false;
let phase = null;
let wellingtonBannerTimer = null;
let lastWellingtonCaller = null;
let lastWinnerKey = null;
const botVisualAnimations = {};

// Cut countdown timer
let cutCountdown = 3;

// Ability state tracking
let abilitySelection = { own_slot: null, target_player: null, target_slot: null };

// ─── DOM Elements ───
const els = {
  // Player gate
  playerGate: document.getElementById('player-gate'),
  playerGateForm: document.getElementById('player-gate-form'),
  playerNameInput: document.getElementById('player-name-input'),
  playerGateError: document.getElementById('player-gate-error'),
  
  // Game areas
  deck: document.getElementById('deck'),
  deckCount: document.getElementById('deck-count'),
  discardSlot: document.getElementById('discard-top-slot'),
  discardFace: document.getElementById('discard-face'),
  drawnPreview: document.getElementById('drawn-card-preview'),
  drawnFace: document.getElementById('drawn-face'),
  drawnHint: document.getElementById('drawn-card-hint'),
  
  // Players
  players: {
    top: { grid: document.getElementById('grid-top'), name: document.getElementById('name-top'), score: document.getElementById('score-top'), status: document.getElementById('status-top') },
    left: { grid: document.getElementById('grid-left'), name: document.getElementById('name-left'), score: document.getElementById('score-left'), status: document.getElementById('status-left') },
    right: { grid: document.getElementById('grid-right'), name: document.getElementById('name-right'), score: document.getElementById('score-right'), status: document.getElementById('status-right') },
    human: { grid: document.getElementById('grid-human'), name: document.getElementById('name-human'), score: document.getElementById('score-human'), status: document.getElementById('status-human') }
  },
  
  // UI
  turnIndicator: document.getElementById('turn-indicator'),
  phaseBanner: document.getElementById('phase-banner'),
  actionPanel: document.getElementById('action-panel'),
  actionHint: document.getElementById('action-hint'),
  btnWelligton: document.getElementById('btn-welligton'),
  
  // Cut countdown
  cutCountdown: document.getElementById('cut-countdown'),
  cutTimer: document.getElementById('cut-timer'),
  
  // Ability panel
  abilityPanel: document.getElementById('ability-panel'),
  abilityTitle: document.getElementById('ability-title'),
  abilityDesc: document.getElementById('ability-desc'),
  abilityCard: document.getElementById('ability-card-name'),
    // Ability 8 modal
    ability8Modal: document.getElementById('ability8-modal'),
    ability8OwnSlot: document.getElementById('ability8-own-slot'),
    ability8OwnCard: document.getElementById('ability8-own-card'),
    ability8TargetSlot: document.getElementById('ability8-target-slot'),
    ability8TargetCard: document.getElementById('ability8-target-card'),
    btnAbility8Swap: document.getElementById('btn-ability8-swap'),
    btnAbility8NoSwap: document.getElementById('btn-ability8-no-swap'),
  
  
  // Log
  logToggle: document.getElementById('game-log-toggle'),
  logPanel: document.getElementById('game-log'),
  logEntries: document.getElementById('log-entries'),
  
  // Toast
  toast: document.getElementById('toast'),
  
  // Controls
  undoBtn: document.getElementById('undo-btn'),
  pauseBtn: document.getElementById('pause-btn'),
  resumeBtn: document.getElementById('resume-btn'),
  newGameBtn: document.getElementById('new-game-btn'),
};

// ─── Card Image Mapping ───
// Map rank to sprite number
const RANK_MAP = {
  'A': '1',
  '2': '2', '3': '3', '4': '4', '5': '5', '6': '6', '7': '7', '8': '8', '9': '9', '10': '10',
  'J': '11',
  'Q': '12',
  'K': '13'
};

const SUIT_MAP = {
  'S': 'Spades',
  'H': 'Hearts',
  'D': 'Diamonds',
  'C': 'Clubs'
};

// Parse card label to {rank, suit}
function parseCard(label) {
  if (!label) return null;
  if (label === 'JK') return { rank: 'JK', suit: null };
  const rank = label.slice(0, -1);
  const suit = label.slice(-1);
  return { rank, suit };
}

// Get card image URL
function getCardImageUrl(rank, suit) {
  if (!rank) return null;
  
  if (rank === 'JK') {
    // Jokers - use black joker
    return '/assets/cards/Joker_Black.png';
  }
  
  if (!suit) {
    // Face down
    return '/assets/cards/Card_Back.png';
  }
  
  const suitName = SUIT_MAP[suit];
  const rankNum = RANK_MAP[rank];
  
  if (suitName && rankNum) {
    return `/assets/cards/${suitName}_${rankNum}.png`;
  }
  
  return null;
}

// ─── API Functions ───
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

async function action(path, payload = null) {
  try {
    state = await request(path, {
      method: "POST",
      body: payload ? JSON.stringify(payload) : undefined,
    });
    render();
  } catch (err) {
    showToast(err.message);
  }
}

// ─── Rendering Functions ───
function render() {
  if (!state) return;
  
  syncUiStateWithGame();
  renderPlayerGate();
  renderPlayers();
  renderDeck();
  renderDiscard();
  renderDrawnCard();
  renderControls();
  renderTurnIndicator();
  renderWellingtonButton();
  renderWellingtonAnnouncement();
  renderWinnerAnnouncement();
  renderCutCountdown();
  renderAbilityPanel();
    renderAbility8Modal();
  renderLog();
  
  // Schedule automation
  scheduleCutAutoPass();
  scheduleWellingtonWindowAutoPass();
  scheduleBotStep();
}

function syncUiStateWithGame() {
  // Determine interaction phase
  if (state.pending_human_cut) {
    phase = 'cut-self';
  } else if (state.pending_human_cut_other_transfer) {
    phase = 'cut-other-transfer';
  } else if (state.drawn_card) {
    phase = 'replace';
  } else if (state.pending_ability) {
    phase = 'ability';
  } else if (state.pending_human_wellington_window) {
    phase = 'wellington';
  } else {
    phase = null;
  }
}

function renderPlayerGate() {
  if (!els.playerGate) return;
  
  if (state.player_ready) {
    els.playerGate.style.display = 'none';
  } else {
    els.playerGate.style.display = 'flex';
  }
}

// Card is {rank, suit} or null
function cardToText(card) {
  if (!card) return null;
  return card.rank + (card.suit || '');
}

// Render card image
function renderCardImage(card) {
  if (!card) {
    // Empty slot
    return '<div class="card-empty-slot"></div>';
  }
  
  const imgUrl = getCardImageUrl(card.rank, card.suit);
  
  if (imgUrl) {
    return `<img src="${imgUrl}" class="card-image" alt="${card.rank}${card.suit || ''}" />`;
  }
  
  // Fallback for unknown
  return '<div class="card-empty-slot"></div>';
}

// Render a card slot - card can be {rank, suit} or null
function renderCardSlot(card, index, isSelectable = false, isSelectableDanger = false) {
  let classes = 'card-slot';
  
  if (!card) classes += ' empty';
  if (isSelectable) classes += ' selectable';
  if (isSelectableDanger) classes += ' selectable-danger';
  
  return `<div class="${classes}" data-slot="${index}">
    ${renderCardImage(card)}
  </div>`;
}

function renderDiscardMarkerSlot(index = -1, extraClass = '') {
  const dataSlot = index >= 0 ? `data-slot="${index}"` : '';
  return `<div class="card-slot discard-marker ${extraClass}" ${dataSlot}>
    <div class="discard-marker-label">DESCARTE</div>
  </div>`;
}

function renderCutMarkerSlot(index = -1) {
  const dataSlot = index >= 0 ? `data-slot="${index}"` : '';
  return `<div class="card-slot cut-marker" ${dataSlot}>
    <div class="cut-marker-label">CORTOU</div>
  </div>`;
}

function renderBotDrawnSlot(discarded = false) {
  if (discarded) {
    return renderDiscardMarkerSlot(-1, 'bot-drawn-extra');
  }
  return `<div class="card-slot bot-drawn-extra">
    ${renderCardImage({ rank: '?', suit: null })}
  </div>`;
}

function getBotVisualAnimation(playerId, visual) {
  if (!visual) {
    delete botVisualAnimations[playerId];
    return null;
  }

  // Handle cut mode
  if (visual.mode === 'cut') {
    const visualKey = `cut:${visual.slot}:${visual.player_name}`;
    const current = botVisualAnimations[playerId];
    if (current && current.visualKey === visualKey) {
      if (current.until && Date.now() >= current.until) {
        delete botVisualAnimations[playerId];
        return null;
      }
      return current;
    }

    const anim = {
      mode: 'cut',
      slot: visual.slot,
      player_name: visual.player_name,
      visualKey,
      until: Date.now() + 1500,
    };
    botVisualAnimations[playerId] = anim;
    
    // Show toast message
    showToast(`${visual.player_name} cortou!`);
    
    setTimeout(() => {
      if (botVisualAnimations[playerId]?.visualKey === visualKey) {
        delete botVisualAnimations[playerId];
        render();
        // Call bot-step after animation to execute the cut
        if (currentState?.phase === 'cut') {
          fetch('/api/bot-step/', { method: 'POST', credentials: 'include' })
            .then(r => r.json())
            .then(data => {
              currentState = data;
              render();
            });
        }
      }
    }, 1510);
    return anim;
  }

  // Original side-based logic
  if (!visual.side) {
    delete botVisualAnimations[playerId];
    return null;
  }

  const visualKey = `${visual.side}:${visual.slot_discarded ?? 'none'}`;
  const current = botVisualAnimations[playerId];
  if (current && current.visualKey === visualKey) {
    if (current.until && Date.now() >= current.until) {
      delete botVisualAnimations[playerId];
      return null;
    }
    return current;
  }

  if (visual.side === 'drawn' && Number.isInteger(visual.slot_discarded)) {
    const anim = {
      mode: 'replace-discard',
      slot: visual.slot_discarded,
      visualKey,
      until: Date.now() + 1000,
    };
    botVisualAnimations[playerId] = anim;
    setTimeout(() => {
      if (botVisualAnimations[playerId]?.visualKey === visualKey) {
        delete botVisualAnimations[playerId];
        render();
      }
    }, 1010);
    return anim;
  }

  if (visual.side === 'discarded') {
    const anim = {
      mode: 'drawn-discard',
      visualKey,
      until: Date.now() + 1000,
    };
    botVisualAnimations[playerId] = anim;
    setTimeout(() => {
      if (botVisualAnimations[playerId]?.visualKey === visualKey) {
        delete botVisualAnimations[playerId];
        render();
      }
    }, 1010);
    return anim;
  }

  if (visual.side === 'drawn') {
    const anim = { mode: 'drawn', visualKey };
    botVisualAnimations[playerId] = anim;
    return anim;
  }

  delete botVisualAnimations[playerId];
  return null;
}

function renderPlayers() {
  const playerIds = { top: 2, left: 1, right: 3, human: 0 };
  
  for (const [pos, playerId] of Object.entries(playerIds)) {
    const player = state.players[playerId];
    const playerEl = els.players[pos];
    
    if (!player || !playerEl.grid) continue;
    
    // Update name
    if (playerEl.name) playerEl.name.textContent = player.name;
    
    // Update active-turn class
    const playerArea = document.getElementById(`player-${pos}`);
    if (playerArea) {
      if (state.current_player === playerId) {
        playerArea.classList.add('active-turn');
      } else {
        playerArea.classList.remove('active-turn');
      }
    }
    
    // Update score - only show when game over
    if (playerEl.score) {
      if (state.game_over && state.scores) {
        const playerScore = state.scores.find(s => s.player === playerId);
        playerEl.score.textContent = playerScore ? `${playerScore.score} pontos` : '?';
      } else {
        playerEl.score.textContent = '?';
      }
    }
    
    // Update status
    if (playerEl.status) {
      const isWinner = state.game_over && Array.isArray(state.winner_ids) && state.winner_ids.includes(playerId);
      if (isWinner) {
        playerEl.status.textContent = 'VENCEDOR';
        playerEl.status.classList.add('winner');
        playerEl.status.classList.remove('locked');
      } else if (player.locked) {
        playerEl.status.textContent = 'WELLIGTON LOCKED';
        playerEl.status.classList.add('locked');
        playerEl.status.classList.remove('winner');
      } else {
        playerEl.status.textContent = '';
        playerEl.status.classList.remove('locked');
        playerEl.status.classList.remove('winner');
      }
    }

    const botAnim = player.is_bot ? getBotVisualAnimation(playerId, player.bot_visual) : null;
    const botAnimActive = !!botAnim && (!botAnim.until || Date.now() < botAnim.until);
    
    // Render cards
    let cardsHtml = '';
    player.cards.forEach((cardObj, idx) => {
      let cardToRender = null;
      
      if (!cardObj.is_empty) {
        if (cardObj.known) {
          const label = cardObj.text;
          if (label === 'JK') {
            cardToRender = { rank: 'JK', suit: null };
          } else if (label === '??') {
            cardToRender = { rank: '?', suit: null };
          } else {
            const rank = label.slice(0, -1);
            const suit = label.slice(-1);
            cardToRender = { rank, suit };
          }
        } else {
          cardToRender = { rank: '?', suit: null };
        }
      }
      
      if (player.is_bot && botAnimActive && botAnim.mode === 'replace-discard' && idx === botAnim.slot) {
        cardsHtml += renderDiscardMarkerSlot(idx);
        return;
      }

      if (player.is_bot && botAnimActive && botAnim.mode === 'cut' && idx === botAnim.slot) {
        cardsHtml += renderCutMarkerSlot(idx);
        return;
      }

      // Determine if selectable
      let selectable = false;
      let selectableDanger = false;
      
      if (phase === 'replace' && pos === 'human' && cardObj.known) {
        selectable = true;
      } else if (phase === 'cut-self' && pos === 'human' && cardObj.known) {
        selectable = true;
      } else if (phase === 'cut-other-transfer' && pos === 'human' && cardObj.known) {
        selectableDanger = true;
      }
      
      cardsHtml += renderCardSlot(cardToRender, idx, selectable, selectableDanger);
    });

    let extraBotHtml = '';
    if (player.is_bot && botAnimActive) {
      if (botAnim.mode === 'drawn' || botAnim.mode === 'replace-discard') {
        extraBotHtml = renderBotDrawnSlot(false);
      } else if (botAnim.mode === 'drawn-discard') {
        extraBotHtml = renderBotDrawnSlot(true);
      }
    }

    playerEl.grid.classList.toggle('has-bot-extra', !!extraBotHtml);
    playerEl.grid.innerHTML = extraBotHtml + cardsHtml;
  }
}

function showPhaseBanner(message, durationMs = 2300) {
  if (!els.phaseBanner) return;

  if (wellingtonBannerTimer) {
    clearTimeout(wellingtonBannerTimer);
    wellingtonBannerTimer = null;
  }

  els.phaseBanner.textContent = message;
  els.phaseBanner.classList.add('show');

  if (durationMs > 0) {
    wellingtonBannerTimer = setTimeout(() => {
      els.phaseBanner.classList.remove('show');
      wellingtonBannerTimer = null;
    }, durationMs);
  }
}

function renderWellingtonAnnouncement() {
  if (!state || !state.players) return;
  if (state.game_over) return;

  const caller = state.wellington_caller;
  if (caller === null || caller === undefined) {
    lastWellingtonCaller = null;
    return;
  }

  if (lastWellingtonCaller === caller) return;

  const callerPlayer = state.players[caller];
  const callerName = callerPlayer?.name || `Jogador ${caller}`;
  showPhaseBanner(`${callerName} pediu WELLIGTON!`);
  lastWellingtonCaller = caller;
}

function renderWinnerAnnouncement() {
  if (!state || !state.players || !state.game_over) {
    lastWinnerKey = null;
    return;
  }

  const winnerIds = Array.isArray(state.winner_ids) ? state.winner_ids : [];
  if (winnerIds.length === 0) return;

  const winnerKey = winnerIds.join(',');
  if (winnerKey === lastWinnerKey) return;

  const winnerNames = winnerIds
    .map(id => state.players[id]?.name || `Jogador ${id}`)
    .join(' / ');
  showPhaseBanner(`Vencedor: ${winnerNames}`, 4200);
  lastWinnerKey = winnerKey;
}

function renderDeck() {
  if (els.deckCount) {
    els.deckCount.textContent = state.draw_pile_count || 0;
  }
  
  if (els.deck) {
    const canDraw = state.actions?.can_draw && phase === null;
    els.deck.classList.toggle('disabled', !canDraw);
    if (state.draw_pile_count > 0) {
      els.deck.classList.add('face-down');
    } else {
      els.deck.classList.remove('face-down');
    }
  }
}

function renderDiscard() {
  if (els.discardFace && state.top_discard) {
    const topCard = parseCard(state.top_discard);
    els.discardFace.innerHTML = renderCardImage(topCard);
  } else if (els.discardFace) {
    els.discardFace.innerHTML = '';
  }
}

function renderDrawnCard() {
  if (!state.drawn_card) {
    if (els.drawnPreview) els.drawnPreview.classList.remove('visible');
    if (els.drawnFace) els.drawnFace.innerHTML = '';
    if (els.drawnHint) els.drawnHint.textContent = '';
    return;
  }
  
  if (els.drawnPreview) {
    els.drawnPreview.classList.add('visible');
    if (els.drawnFace) {
      const drawnCard = parseCard(state.drawn_card);
      els.drawnFace.innerHTML = renderCardImage(drawnCard);
    }
  }
  
  if (els.drawnHint) {
    if (phase === 'replace') {
      els.drawnHint.textContent = 'Clique para descartar';
      els.drawnHint.classList.add('active');
    } else {
      els.drawnHint.textContent = '';
      els.drawnHint.classList.remove('active');
    }
  }
}

function renderControls() {
  if (els.undoBtn) els.undoBtn.disabled = !state.can_undo;
  if (els.pauseBtn) els.pauseBtn.disabled = state.paused;
  if (els.resumeBtn) els.resumeBtn.disabled = !state.paused;
}

function renderTurnIndicator() {
  if (!els.turnIndicator) return;

  if (state.game_over && Array.isArray(state.winner_ids) && state.winner_ids.length > 0) {
    const winnerNames = state.winner_ids
      .map(id => state.players[id]?.name || `Jogador ${id}`)
      .join(' / ');
    els.turnIndicator.textContent = `VENCEDOR: ${winnerNames.toUpperCase()}`;
    els.turnIndicator.style.display = 'block';
    return;
  }
  
  const currentPlayer = state.players[state.current_player];
  
  if (currentPlayer) {
    if (state.current_player === 0) {
      els.turnIndicator.textContent = 'SUA VEZ';
    } else {
      els.turnIndicator.textContent = `VEZ DE ${currentPlayer.name.toUpperCase()}`;
    }
    els.turnIndicator.style.display = 'block';
  } else {
    els.turnIndicator.style.display = 'none';
  }
}

function renderWellingtonButton() {
  if (!els.btnWelligton) return;
  
  const canCall = state.actions?.can_call_wellington && phase === 'wellington';
  els.btnWelligton.disabled = !canCall;
}

let cutTimerInterval = null;

function renderCutCountdown() {
  if (!els.cutCountdown) return;
  
  if (state.pending_human_cut) {
    // Start countdown if not running
    if (!cutTimerInterval) {
      cutCountdown = 3;
      cutTimerInterval = setInterval(async () => {
        cutCountdown--;
        if (cutCountdown <= 0) {
          clearInterval(cutTimerInterval);
          cutTimerInterval = null;
          // Auto-skip cut when timer expires
          try {
            await action("/api/action/skip-cut");
          } catch (err) {
            console.error("Failed to skip cut:", err);
          }
        }
        if (els.cutTimer) {
          els.cutTimer.textContent = cutCountdown;
          if (cutCountdown <= 1) {
            els.cutTimer.classList.add('urgent');
          } else {
            els.cutTimer.classList.remove('urgent');
          }
        }
      }, 1000);
    }
    
    els.cutCountdown.classList.add('visible');
    if (els.cutTimer) els.cutTimer.textContent = cutCountdown;
  } else {
    // Clear countdown
    if (cutTimerInterval) {
      clearInterval(cutTimerInterval);
      cutTimerInterval = null;
    }
    els.cutCountdown.classList.remove('visible');
  }
}

function renderAbilityPanel() {
  if (!els.abilityPanel) return;

  if (state.pending_ability) {
    els.abilityPanel.classList.add('visible');
    
    const rank = state.pending_ability.rank || '';
    if (els.abilityCard) els.abilityCard.textContent = rank;
    
    const abilityNum = parseInt(rank);
    let title = 'Habilidade Ativada';
    let desc = '';
    
    switch (abilityNum) {
      case 5:
        title = 'Habilidade 5';
        desc = 'Selecione uma de suas cartas para revelar.';
        break;
      case 6:
        title = 'Habilidade 6';
        desc = 'Selecione uma carta de outro jogador para revelar.';
        break;
      case 7:
        title = 'Habilidade 7';
        desc = 'Selecione uma de suas cartas e uma de outro jogador para trocar.';
        break;
      case 8:
        title = 'Habilidade 8';
        desc = 'Selecione duas cartas para revelar, depois escolha se quer trocar.';
        break;
    }
    
    if (els.abilityTitle) els.abilityTitle.textContent = title;
    if (els.abilityDesc) els.abilityDesc.textContent = desc;
  } else {
    els.abilityPanel.classList.remove('visible');
  }
}

function renderLog() {
  function renderAbility8Modal() {
    if (!els.ability8Modal) return;

    if (state.pending_ability8_preview) {
      els.ability8Modal.classList.add('visible');
    
      const preview = state.pending_ability8_preview;
    
      if (els.ability8OwnSlot) els.ability8OwnSlot.textContent = preview.own_slot;
      if (els.ability8OwnCard) els.ability8OwnCard.textContent = preview.own_label;
      if (els.ability8TargetSlot) els.ability8TargetSlot.textContent = preview.target_slot;
      if (els.ability8TargetCard) els.ability8TargetCard.textContent = preview.target_label;
    } else {
      els.ability8Modal.classList.remove('visible');
    }
  }

  function renderLog() {
  if (!els.logEntries || !state.log) return;
  
  els.logEntries.innerHTML = state.log.slice(-20).map(entry => 
    `<div class="log-entry">${entry}</div>`
  ).join('');
}

function showToast(message) {
  if (!els.toast) return;
  
  els.toast.textContent = message;
  els.toast.classList.add('show');
  
  setTimeout(() => {
    els.toast.classList.remove('show');
  }, 3000);
}

// ─── Event Handlers ───

// Deck click
if (els.deck) {
  els.deck.addEventListener('click', () => {
    if (state.actions?.can_draw && phase === null) {
      action('/api/action/draw');
    }
  });
}

// Drawn card click
if (els.drawnPreview) {
  els.drawnPreview.addEventListener('click', () => {
    if (phase === 'replace') {
      action('/api/action/discard-drawn');
    }
  });
}

// Card slot clicks (delegation)
document.addEventListener('click', (e) => {
  const slot = e.target.closest('.card-slot');
  if (!slot) return;
  
  const slotIndex = parseInt(slot.dataset.slot);
  const isHumanCard = slot.closest('#grid-human');
  
  if (phase === 'replace' && isHumanCard) {
    action('/api/action/replace', { slot: slotIndex });
  } else if (phase === 'cut-self' && isHumanCard) {
    action('/api/action/cut-self', { slot: slotIndex });
  } else if (phase === 'cut-other-transfer' && isHumanCard) {
    // Player needs to give a card when cutting another player's card
    if (!state.pending_human_cut_other_transfer) {
      showToast('Transferencia de corte nao encontrada. Tente novamente.');
      return;
    }
    action('/api/action/cut-other', {
      target_player: state.pending_human_cut_other_transfer.target_player,
      target_slot: state.pending_human_cut_other_transfer.target_slot,
      give_slot: slotIndex,
    });
  } else if (phase === 'ability' && isHumanCard && state.pending_ability) {
    // Handle ability 5 (view own card)
    const rank = state.pending_ability.rank;
    if (rank === '5') {
      action('/api/action/ability', { data: { slot: slotIndex } });
    } else if (rank === '7') {
      // Ability 7: first click own card
      if (abilitySelection.own_slot === null) {
        abilitySelection.own_slot = slotIndex;
        showToast('Agora selecione uma carta de outro jogador');
      }
    } else if (rank === '8') {
      // Ability 8: first click own card
      if (abilitySelection.own_slot === null) {
        abilitySelection.own_slot = slotIndex;
        showToast('Agora selecione uma carta de outro jogador');
      }
    }
  }
});

// Also handle clicking on other players' cards for cuts and abilities
document.addEventListener('click', (e) => {
  const playerArea = e.target.closest('[id^="player-"]');
  if (!playerArea) return;
  
  const slot = e.target.closest('.card-slot');
  if (!slot) return;
  
  const slotIndex = parseInt(slot.dataset.slot);
  const pos = playerArea.id.replace('player-', '');
  
  // Map position to player ID
  const posToPlayerId = { top: 2, left: 1, right: 3 };
  const targetPlayer = posToPlayerId[pos];
  
  if (targetPlayer !== undefined && phase === 'cut-self') {
    // Cut another player's card
    action('/api/action/cut-other', { 
      target_player: targetPlayer, 
      target_slot: slotIndex 
    });
  } else if (targetPlayer !== undefined && phase === 'ability' && state.pending_ability) {
    const rank = state.pending_ability.rank;
    
    if (rank === '6') {
      // Ability 6: view opponent's card
      action('/api/action/ability', { 
        data: {
          target_player: targetPlayer, 
          slot: slotIndex
        }
      });
    } else if (rank === '7') {
      // Ability 7: swap without seeing
      if (abilitySelection.own_slot !== null) {
        action('/api/action/ability', { 
          data: {
            own_slot: abilitySelection.own_slot,
            target_player: targetPlayer, 
            target_slot: slotIndex
          }
        });
        abilitySelection = { own_slot: null, target_player: null, target_slot: null };
      } else {
        showToast('Primeiro selecione uma de suas cartas');
      }
    } else if (rank === '8') {
      // Ability 8: preview both cards
      if (abilitySelection.own_slot !== null) {
        action('/api/action/ability', { 
          data: {
            preview: true,
            own_slot: abilitySelection.own_slot,
            target_player: targetPlayer, 
            target_slot: slotIndex
          }
        });
        abilitySelection = { own_slot: null, target_player: null, target_slot: null };
      } else {
        showToast('Primeiro selecione uma de suas cartas');
      }
    }
  }
});

// Wellington button
if (els.btnWelligton) {
  els.btnWelligton.addEventListener('click', () => {
    action('/api/action/call-wellington');
  });
}

// Ability 8 swap decision
if (els.btnAbility8Swap) {
  els.btnAbility8Swap.addEventListener('click', () => {
    action('/api/action/ability', { 
      data: { do_swap: true }
    });
  });
}

if (els.btnAbility8NoSwap) {
  els.btnAbility8NoSwap.addEventListener('click', () => {
    action('/api/action/ability', { 
      data: { do_swap: false }
    });
  });
}

// Log toggle
if (els.logToggle && els.logPanel) {
  els.logToggle.addEventListener('click', () => {
    logVisible = !logVisible;
    els.logPanel.classList.toggle('visible', logVisible);
  });
}

// Player name submit
if (els.playerGateForm) {
  els.playerGateForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = els.playerNameInput.value.trim();
    if (!name) return;
    
    try {
      await action('/api/player/start', { name });
    } catch (err) {
      if (els.playerGateError) {
        els.playerGateError.textContent = err.message;
      }
    }
  });
}

// Controls
if (els.undoBtn) {
  els.undoBtn.addEventListener('click', () => action('/api/action/undo'));
}

if (els.pauseBtn) {
  els.pauseBtn.addEventListener('click', () => action('/api/pause'));
}

if (els.resumeBtn) {
  els.resumeBtn.addEventListener('click', () => action('/api/resume'));
}

if (els.newGameBtn) {
  els.newGameBtn.addEventListener('click', () => action('/api/new-game'));
}

// ─── Automation ───

function scheduleBotStep() {
  clearTimeout(botStepTimer);

  if (!state.player_ready || state.game_over || state.paused) return;
  if (!state.actions?.can_bot_step) return;

  const delay = state.pending_bot_turn ? 1000 : 500;
  botStepTimer = setTimeout(() => {
    action('/api/bot-step');
  }, delay);
}

function scheduleCutAutoPass() {
  clearTimeout(cutAutoPassTimer);
  
  if (!state.pending_human_cut) return;
  if (!state.actions?.can_cut) return;
  
  // Auto pass after 2.5 seconds
  cutAutoPassTimer = setTimeout(() => {
    // There's no skip cut action, so we just wait for the timer
    // The cut window will close automatically
  }, 2500);
}

function scheduleWellingtonWindowAutoPass() {
  clearTimeout(wellingtonWindowTimer);
  
  if (!state.pending_human_wellington_window) return;
  
  wellingtonWindowTimer = setTimeout(() => {
    action('/api/action/pass-wellington-window');
  }, 3000);
}

function clearAutomationTimers() {
  clearTimeout(botStepTimer);
  clearTimeout(cutAutoPassTimer);
  clearTimeout(wellingtonWindowTimer);
  if (cutTimerInterval) {
    clearInterval(cutTimerInterval);
    cutTimerInterval = null;
  }
}

// ─── Initialization ───
loadState();
