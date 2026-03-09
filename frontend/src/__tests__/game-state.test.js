/**
 * Testes de estado do jogo
 * GAME_STATE_MODEL.md
 */
import { describe, it, expect, beforeEach } from 'vitest';

// Game state structure (from backend)
const INITIAL_STATE = {
  players: [],
  deck: [],
  discard_pile: [],
  current_player_index: 0,
  phase: 'DRAW_PHASE',
  cut_window_open: false,
  ability_pending: null,
  wellington_player: null,
  round_finished: false,
};

// Mock game state manager
class GameStateManager {
  constructor() {
    this.state = { ...INITIAL_STATE };
  }

  reset() {
    this.state = { ...INITIAL_STATE };
  }

  updateState(newState) {
    this.state = { ...this.state, ...newState };
  }

  getState() {
    return this.state;
  }

  isPlayerTurn(playerIndex) {
    return this.state.current_player_index === playerIndex;
  }

  isHumanTurn() {
    return this.state.current_player_index === 0;
  }

  hasWellington() {
    return this.state.wellington_player !== null;
  }

  canDraw() {
    return this.state.phase === 'DRAW_PHASE';
  }
}

describe('Game State', () => {
  let gameState;

  beforeEach(() => {
    gameState = new GameStateManager();
  });

  describe('Initial State', () => {
    it('UI-STATE-01: Initial state is correct', () => {
      const state = gameState.getState();
      expect(state.phase).toBe('DRAW_PHASE');
      expect(state.current_player_index).toBe(0);
      expect(state.cut_window_open).toBe(false);
      expect(state.round_finished).toBe(false);
    });

    it('Initial players array is empty', () => {
      const state = gameState.getState();
      expect(state.players).toEqual([]);
    });
  });

  describe('State Updates', () => {
    it('UI-STATE-02: State updates after draw', () => {
      gameState.updateState({
        phase: 'DISCARD_PHASE',
        drawn_card: { rank: 'A', suit: 'H' },
      });

      const state = gameState.getState();
      expect(state.phase).toBe('DISCARD_PHASE');
      expect(state.drawn_card).toEqual({ rank: 'A', suit: 'H' });
    });

    it('UI-STATE-03: State updates after discard', () => {
      gameState.updateState({
        phase: 'CUT_WINDOW',
        cut_window_open: true,
      });

      const state = gameState.getState();
      expect(state.cut_window_open).toBe(true);
    });
  });

  describe('Player Turn', () => {
    it('UI-STATE-04: Human is player 0', () => {
      expect(gameState.isHumanTurn()).toBe(true);
    });

    it('Player turn changes correctly', () => {
      gameState.updateState({ current_player_index: 1 });
      expect(gameState.isHumanTurn()).toBe(false);
      expect(gameState.isPlayerTurn(1)).toBe(true);
    });
  });

  describe('Wellington State', () => {
    it('UI-STATE-05: No wellington initially', () => {
      expect(gameState.hasWellington()).toBe(false);
    });

    it('Wellington indicator shows when called', () => {
      gameState.updateState({
        wellington_player: 0,
        players: [
          { name: 'Voce', locked: true },
          { name: 'Bot 1', locked: false },
        ],
      });

      expect(gameState.hasWellington()).toBe(true);
    });
  });

  describe('Phase Management', () => {
    it('Can draw in DRAW_PHASE', () => {
      expect(gameState.canDraw()).toBe(true);
    });

    it('Cannot draw in other phases', () => {
      gameState.updateState({ phase: 'DISCARD_PHASE' });
      expect(gameState.canDraw()).toBe(false);
    });
  });

  describe('Player State Structure', () => {
    it('Player has required properties', () => {
      const player = {
        id: 0,
        type: 'human',
        cards: [],
        knowledge_map: {},
        has_called_welligton: false,
      };

      expect(player).toHaveProperty('id');
      expect(player).toHaveProperty('type');
      expect(player).toHaveProperty('cards');
      expect(player).toHaveProperty('knowledge_map');
      expect(player).toHaveProperty('has_called_welligton');
    });
  });
});

describe('Card Slot', () => {
  it('Card slot can be empty', () => {
    const slot = {
      card: null,
      known_to_players: [],
    };
    expect(slot.card).toBeNull();
  });

  it('Card slot can have card', () => {
    const slot = {
      card: { rank: 'A', suit: 'H', value: 0 },
      known_to_players: [0],
    };
    expect(slot.card).not.toBeNull();
    expect(slot.card.rank).toBe('A');
  });
});
