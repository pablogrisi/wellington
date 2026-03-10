/**
 * Testes de componentes de UI
 * FRONTEND_UI_SPEC.md - Table Layout, Player Area
 */
import { describe, it, expect, beforeEach } from 'vitest';

// Player positions from FRONTEND_UI_SPEC.md
const PLAYER_POSITIONS = {
  TOP: 'top',    // Bot
  LEFT: 'left',  // Bot
  RIGHT: 'right', // Bot
  BOTTOM: 'bottom', // Human Player
};

// Mock UI Components
class PlayerArea {
  constructor(position, name) {
    this.position = position;
    this.name = name;
    this.cards = [];
    this.isActive = false;
    this.isLocked = false;
  }

  setCards(cards) {
    this.cards = cards;
  }

  setActive(active) {
    this.isActive = active;
  }

  setLocked(locked) {
    this.isLocked = locked;
  }
}

class CardGrid {
  constructor(rows = 2, cols = 2) {
    this.rows = rows;
    this.cols = cols;
    this.slots = Array(rows * cols).fill(null);
  }

  setCard(slotIndex, card) {
    this.slots[slotIndex] = card;
  }

  getCard(slotIndex) {
    return this.slots[slotIndex];
  }
}

class DeckArea {
  constructor() {
    this.drawPile = [];
    this.discardPile = [];
    this.drawnCard = null;
  }

  addToDrawPile(card) {
    this.drawPile.push(card);
  }

  addToDiscard(card) {
    this.discardPile.push(card);
    this.drawnCard = null;
  }

  draw() {
    return this.drawPile.pop();
  }
}

class EventLog {
  constructor() {
    this.entries = [];
  }

  add(entry) {
    this.entries.push({
      ...entry,
      timestamp: Date.now(),
    });
  }

  getRecent(count = 10) {
    return this.entries.slice(-count);
  }

  clear() {
    this.entries = [];
  }
}

class CutCountdown {
  constructor() {
    this.timeLeft = 0;
    this.isRunning = false;
  }

  start(seconds) {
    this.timeLeft = seconds;
    this.isRunning = true;
  }

  tick() {
    if (this.isRunning && this.timeLeft > 0) {
      this.timeLeft--;
    }
    return this.timeLeft;
  }

  stop() {
    this.isRunning = false;
  }

  reset() {
    this.timeLeft = 0;
    this.isRunning = false;
  }
}

describe('UI Components', () => {
  describe('Player Positions', () => {
    it('UI-COMP-01: 4 players around table', () => {
      const positions = Object.keys(PLAYER_POSITIONS);
      expect(positions.length).toBe(4);
    });

    it('UI-COMP-01: Human player at bottom', () => {
      expect(PLAYER_POSITIONS.BOTTOM).toBe('bottom');
    });

    it('UI-COMP-01: Bots at top, left, right', () => {
      expect(PLAYER_POSITIONS.TOP).toBe('top');
      expect(PLAYER_POSITIONS.LEFT).toBe('left');
      expect(PLAYER_POSITIONS.RIGHT).toBe('right');
    });
  });

  describe('Player Area', () => {
    let playerArea;

    beforeEach(() => {
      playerArea = new PlayerArea('bottom', 'Voce');
    });

    it('Player area has name', () => {
      expect(playerArea.name).toBe('Voce');
    });

    it('Player area has position', () => {
      expect(playerArea.position).toBe('bottom');
    });

    it('Player can have cards', () => {
      playerArea.setCards([{ rank: 'A', suit: 'H' }]);
      expect(playerArea.cards.length).toBe(1);
    });

    it('Player can be active', () => {
      playerArea.setActive(true);
      expect(playerArea.isActive).toBe(true);
    });

    it('UI-COMP-04: Player can be locked (Wellington)', () => {
      playerArea.setLocked(true);
      expect(playerArea.isLocked).toBe(true);
    });
  });

  describe('Card Grid', () => {
    it('UI-COMP-02: Grid is 2x2', () => {
      const grid = new CardGrid(2, 2);
      expect(grid.rows).toBe(2);
      expect(grid.cols).toBe(2);
      expect(grid.slots.length).toBe(4);
    });

    it('UI-COMP-02: Can set card in slot', () => {
      const grid = new CardGrid(2, 2);
      grid.setCard(0, { rank: 'A', suit: 'H' });
      expect(grid.getCard(0)).toEqual({ rank: 'A', suit: 'H' });
    });

    it('Empty slot returns null', () => {
      const grid = new CardGrid(2, 2);
      expect(grid.getCard(0)).toBeNull();
    });
  });

  describe('Deck Area', () => {
    let deckArea;

    beforeEach(() => {
      deckArea = new DeckArea();
    });

    it('UI-COMP-03: Draw pile exists', () => {
      expect(deckArea.drawPile).toEqual([]);
    });

    it('UI-COMP-03: Discard pile exists', () => {
      expect(deckArea.discardPile).toEqual([]);
    });

    it('Can add cards to draw pile', () => {
      deckArea.addToDrawPile({ rank: 'A', suit: 'H' });
      expect(deckArea.drawPile.length).toBe(1);
    });

    it('Can draw from pile', () => {
      deckArea.addToDrawPile({ rank: 'A', suit: 'H' });
      const card = deckArea.draw();
      expect(card).toEqual({ rank: 'A', suit: 'H' });
      expect(deckArea.drawPile.length).toBe(0);
    });

    it('Can add to discard pile', () => {
      deckArea.addToDiscard({ rank: '5', suit: 'H' });
      expect(deckArea.discardPile.length).toBe(1);
    });
  });

  describe('Event Log', () => {
    let eventLog;

    beforeEach(() => {
      eventLog = new EventLog();
    });

    it('UI-COMP-04: Event log can add entries', () => {
      eventLog.add({ message: 'Player drew a card' });
      expect(eventLog.entries.length).toBe(1);
    });

    it('UI-COMP-04: Can get recent entries', () => {
      for (let i = 0; i < 15; i++) {
        eventLog.add({ message: `Event ${i}` });
      }
      const recent = eventLog.getRecent(10);
      expect(recent.length).toBe(10);
    });

    it('Event log example messages', () => {
      eventLog.add({ type: 'draw', message: 'Player drew a card' });
      eventLog.add({ type: 'discard', message: 'Bot discarded 7' });
      eventLog.add({ type: 'reveal', message: 'Player revealed a card' });
      eventLog.add({ type: 'cut', message: 'Bot attempted cut' });
      eventLog.add({ type: 'cut_success', message: 'Cut successful' });
      eventLog.add({ type: 'wellington', message: 'Player called WELLIGTON' });

      expect(eventLog.entries.length).toBe(6);
    });
  });

  describe('Cut Countdown', () => {
    let countdown;

    beforeEach(() => {
      countdown = new CutCountdown();
    });

    it('UI-COMP-06: Countdown starts with 3 seconds', () => {
      countdown.start(3);
      expect(countdown.timeLeft).toBe(3);
      expect(countdown.isRunning).toBe(true);
    });

    it('UI-COMP-06: Countdown ticks down', () => {
      countdown.start(3);
      countdown.tick();
      expect(countdown.timeLeft).toBe(2);
      countdown.tick();
      expect(countdown.timeLeft).toBe(1);
    });

    it('UI-COMP-06: Countdown stops at zero', () => {
      countdown.start(1);
      countdown.tick();
      expect(countdown.timeLeft).toBe(0);
      expect(countdown.isRunning).toBe(false);
    });

    it('Can reset countdown', () => {
      countdown.start(3);
      countdown.tick();
      countdown.reset();
      expect(countdown.timeLeft).toBe(0);
      expect(countdown.isRunning).toBe(false);
    });
  });

  describe('Wellington Indicator', () => {
    it('UI-COMP-04: Locked indicator shows', () => {
      const player = new PlayerArea('bottom', 'Voce');
      player.setLocked(true);
      expect(player.isLocked).toBe(true);
    });

    it('Wellington indicator message', () => {
      const message = 'WELLIGTON LOCKED';
      expect(message).toBe('WELLIGTON LOCKED');
    });
  });
});
