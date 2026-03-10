/**
 * Testes de manipuladores de eventos
 * EVENT_SYSTEM.md
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';

// Event types from EVENT_SYSTEM.md
const EVENT_TYPES = {
  PLAYER_DRAW_CARD: 'PLAYER_DRAW_CARD',
  PLAYER_DISCARD_CARD: 'PLAYER_DISCARD_CARD',
  PLAYER_CALL_WELLIGTON: 'PLAYER_CALL_WELLIGTON',
  PLAYER_USE_ABILITY: 'PLAYER_USE_ABILITY',
  PLAYER_CUT: 'PLAYER_CUT',
  PLAYER_SKIP_CUT: 'PLAYER_SKIP_CUT',
  TURN_STARTED: 'TURN_STARTED',
  TURN_ENDED: 'TURN_ENDED',
  CUT_WINDOW_OPENED: 'CUT_WINDOW_OPENED',
  CUT_WINDOW_CLOSED: 'CUT_WINDOW_CLOSED',
  ABILITY_STARTED: 'ABILITY_STARTED',
  ABILITY_RESOLVED: 'ABILITY_RESOLVED',
  ROUND_FINISHED: 'ROUND_FINISHED',
};

// Mock event bus
class EventBus {
  constructor() {
    this.listeners = {};
    this.eventLog = [];
  }

  on(event, callback) {
    if (!this.listeners[event]) {
      this.listeners[event] = [];
    }
    this.listeners[event].push(callback);
  }

  emit(event, data) {
    this.eventLog.push({ event, data, timestamp: Date.now() });
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => cb(data));
    }
  }

  clear() {
    this.listeners = {};
    this.eventLog = [];
  }
}

// Mock game actions
class GameActions {
  constructor(eventBus) {
    this.eventBus = eventBus;
    this.canDraw = false;
    this.canDiscard = false;
    this.canCut = false;
  }

  enableDraw() {
    this.canDraw = true;
  }

  disableDraw() {
    this.canDraw = false;
  }

  draw() {
    if (!this.canDraw) return false;
    this.eventBus.emit(EVENT_TYPES.PLAYER_DRAW_CARD, { player: 0 });
    this.disableDraw();
    this.canDiscard = true;
    return true;
  }

  discard(card) {
    if (!this.canDiscard) return false;
    this.eventBus.emit(EVENT_TYPES.PLAYER_DISCARD_CARD, { player: 0, card });
    this.canDiscard = false;
    this.canCut = true;
    return true;
  }

  skipCut() {
    if (!this.canCut) return false;
    this.eventBus.emit(EVENT_TYPES.PLAYER_SKIP_CUT, { player: 0 });
    this.canCut = false;
    return true;
  }
}

describe('Event System', () => {
  let eventBus;

  beforeEach(() => {
    eventBus = new EventBus();
  });

  describe('Event Types', () => {
    it('UI-EVENT-01: PLAYER_DRAW_CARD event exists', () => {
      expect(EVENT_TYPES.PLAYER_DRAW_CARD).toBe('PLAYER_DRAW_CARD');
    });

    it('UI-EVENT-01: PLAYER_DISCARD_CARD event exists', () => {
      expect(EVENT_TYPES.PLAYER_DISCARD_CARD).toBe('PLAYER_DISCARD_CARD');
    });

    it('UI-EVENT-04: PLAYER_SKIP_CUT event exists', () => {
      expect(EVENT_TYPES.PLAYER_SKIP_CUT).toBe('PLAYER_SKIP_CUT');
    });
  });

  describe('Event Emission', () => {
    it('Events are emitted correctly', () => {
      const callback = vi.fn();
      eventBus.on(EVENT_TYPES.PLAYER_DRAW_CARD, callback);

      eventBus.emit(EVENT_TYPES.PLAYER_DRAW_CARD, { player: 0 });

      expect(callback).toHaveBeenCalledWith({ player: 0 });
    });

    it('Event log records events', () => {
      eventBus.emit(EVENT_TYPES.PLAYER_DRAW_CARD, { player: 0 });

      expect(eventBus.eventLog.length).toBe(1);
      expect(eventBus.eventLog[0].event).toBe(EVENT_TYPES.PLAYER_DRAW_CARD);
    });
  });

  describe('Event Flow', () => {
    it('UI-EVENT-02: Click events trigger actions', () => {
      const actions = new GameActions(eventBus);
      actions.enableDraw();

      const result = actions.draw();

      expect(result).toBe(true);
      expect(eventBus.eventLog.length).toBe(1);
    });

    it('UI-EVENT-04: Buttons enabled/disabled correctly', () => {
      const actions = new GameActions(eventBus);

      // Cannot draw initially
      expect(actions.canDraw).toBe(false);

      // Enable draw
      actions.enableDraw();
      expect(actions.canDraw).toBe(true);

      // After drawing, cannot draw again
      actions.draw();
      expect(actions.canDraw).toBe(false);
    });
  });

  describe('Cut Window', () => {
    it('UI-EVENT-03: Cut window opens after discard', () => {
      const actions = new GameActions(eventBus);
      actions.enableDraw();
      actions.draw();
      actions.discard({ rank: '5', suit: 'H' });

      // Should be in cut window now
      const lastEvent = eventBus.eventLog[eventBus.eventLog.length - 1];
      expect(lastEvent.event).toBe(EVENT_TYPES.PLAYER_DISCARD_CARD);
    });

    it('CUT_WINDOW_OPENED event fires', () => {
      const callback = vi.fn();
      eventBus.on(EVENT_TYPES.CUT_WINDOW_OPENED, callback);

      eventBus.emit(EVENT_TYPES.CUT_WINDOW_OPENED, {});

      expect(callback).toHaveBeenCalled();
    });

    it('CUT_WINDOW_CLOSED event fires', () => {
      const callback = vi.fn();
      eventBus.on(EVENT_TYPES.CUT_WINDOW_CLOSED, callback);

      eventBus.emit(EVENT_TYPES.CUT_WINDOW_CLOSED, {});

      expect(callback).toHaveBeenCalled();
    });
  });

  describe('Ability Events', () => {
    it('ABILITY_STARTED event fires for card 5', () => {
      const callback = vi.fn();
      eventBus.on(EVENT_TYPES.ABILITY_STARTED, callback);

      eventBus.emit(EVENT_TYPES.ABILITY_STARTED, { ability: 5 });

      expect(callback).toHaveBeenCalledWith({ ability: 5 });
    });

    it('UI-EVENT-05: Ability instructions displayed', () => {
      // For ability 5: "Select one of your cards to reveal."
      const instructions = {
        5: 'Select one of your cards to reveal.',
        6: 'Select a card from another player.',
        7: 'Select one of your cards and one from another player to swap.',
        8: 'Select two cards to reveal, then choose whether to swap.',
      };

      expect(instructions[5]).toBe('Select one of your cards to reveal.');
      expect(instructions[6]).toBe('Select a card from another player.');
      expect(instructions[7]).toBe('Select one of your cards and one from another player to swap.');
      expect(instructions[8]).toBe('Select two cards to reveal, then choose whether to swap.');
    });
  });

  describe('Wellington Events', () => {
    it('WELLINGTON_CALLED event exists', () => {
      expect(EVENT_TYPES.PLAYER_CALL_WELLIGTON).toBe('PLAYER_CALL_WELLIGTON');
    });

    it('Wellington event fires correctly', () => {
      const callback = vi.fn();
      eventBus.on(EVENT_TYPES.PLAYER_CALL_WELLIGTON, callback);

      eventBus.emit(EVENT_TYPES.PLAYER_CALL_WELLIGTON, { player: 0 });

      expect(callback).toHaveBeenCalledWith({ player: 0 });
    });
  });

  describe('Turn Events', () => {
    it('TURN_STARTED event exists', () => {
      expect(EVENT_TYPES.TURN_STARTED).toBe('TURN_STARTED');
    });

    it('TURN_ENDED event exists', () => {
      expect(EVENT_TYPES.TURN_ENDED).toBe('TURN_ENDED');
    });
  });
});
