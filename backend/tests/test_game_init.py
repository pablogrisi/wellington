"""
Testes para inicialização do jogo.
参照: GAME_RULES_SPEC.md - Initial Setup, Player Layout
"""
import pytest
from app.game_engine import WellingtonGame, Card


class TestNewGame:
    """Testes de criação de novo jogo."""

    def test_new_game_creates_four_players(self, game):
        """INIT-01: 4 jogadores criados."""
        game.new_game()
        assert len(game.players) == 4

    def test_first_player_is_human(self, game):
        """INIT-01: Primeiro jogador é humano."""
        game.new_game()
        assert game.players[0].is_bot is False
        assert game.players[0].name == "Voce"

    def test_other_players_are_bots(self, game):
        """INIT-01: Demais jogadores são bots."""
        game.new_game()
        assert game.players[1].is_bot is True
        assert game.players[2].is_bot is True
        assert game.players[3].is_bot is True
        assert game.players[1].name == "Bot 1"
        assert game.players[2].name == "Bot 2"
        assert game.players[3].name == "Bot 3"

    def test_each_player_receives_four_cards(self, game):
        """INIT-02: Cada jogador recebe 4 cartas."""
        game.new_game()
        for i, player in enumerate(game.players):
            assert len(player.cards) == 4, f"Jogador {i} tem {len(player.cards)} cartas"

    def test_players_know_two_cards_initially(self, game):
        """INIT-03: Jogador conhece 2 cartas inicialmente."""
        game.new_game()
        human = game.players[0]
        # Jogador conhece as cartas nos slots 2 e 3 (0-indexed: 2, 3)
        assert 2 in human.known_slots
        assert 3 in human.known_slots
        # Slots 0 e 1 são desconhecidos
        assert 0 not in human.known_slots
        assert 1 not in human.known_slots

    def test_bot_players_know_two_cards(self, game):
        """INIT-03: Bots também conhecem 2 cartas."""
        game.new_game()
        for i in range(1, 4):
            bot = game.players[i]
            assert len(bot.known_slots) == 2

    def test_draw_pile_has_correct_count(self, game):
        """INIT-04: Monte de compras tem quantidade correta."""
        game.new_game()
        # 54 cartas - 16 (4 para cada jogador) - 1 (descarte inicial) = 37
        expected = 54 - 16 - 1
        assert len(game.draw_pile) == expected

    def test_discard_pile_has_one_card(self, game):
        """INIT-05: Pilha de descarte tem 1 carta."""
        game.new_game()
        assert len(game.discard_pile) == 1

    def test_first_card_in_discard_is_face_up(self, game):
        """INIT-05: Carta no descarte é visível."""
        game.new_game()
        assert game.discard_pile[0] is not None

    def test_human_starts_first(self, game):
        """INIT-06: Jogador humano começa."""
        game.new_game()
        assert game.current_player == 0

    def test_drawn_card_initially_none(self, game):
        """INIT-06: Nenhuma carta została sacada inicialmente."""
        game.new_game()
        assert game.drawn_card is None

    def test_wellington_caller_initially_none(self, game):
        """INIT-06: Ninguém chamou Wellington ainda."""
        game.new_game()
        assert game.wellington_caller is None

    def test_game_not_over_initially(self, game):
        """INIT-06: Jogo não terminou."""
        game.new_game()
        assert game.game_over is False


class TestPlayerState:
    """Testes do estado do jogador."""

    def test_player_starts_not_locked(self, game):
        """Jogador começa sem lock."""
        game.new_game()
        for player in game.players:
            assert player.locked is False

    def test_player_cards_are_card_objects(self, game):
        """Cartas são objetos Card."""
        game.new_game()
        human = game.players[0]
        for card in human.cards:
            assert isinstance(card, Card)


class TestDeckWithSeed:
    """Testes de determinismo com seed."""

    def test_same_seed_same_deck(self):
        """Mesma seed gera mesmo baralho."""
        game1 = WellingtonGame(seed=123)
        game2 = WellingtonGame(seed=123)
        game1.new_game()
        game2.new_game()

        # Compara todas as cartas
        for p1, p2 in zip(game1.players, game2.players):
            for c1, c2 in zip(p1.cards, p2.cards):
                assert c1.rank == c2.rank
                assert c1.suit == c2.suit

    def test_different_seed_different_deck(self):
        """Seed diferente gera baralho diferente."""
        game1 = WellingtonGame(seed=100)
        game2 = WellingtonGame(seed=200)
        game1.new_game()
        game2.new_game()

        # Verifica que pelo menos uma carta é diferente
        different = False
        for p1, p2 in zip(game1.players, game2.players):
            for c1, c2 in zip(p1.cards, p2.cards):
                if c1.rank != c2.rank or c1.suit != c2.suit:
                    different = True
                    break

        assert different
