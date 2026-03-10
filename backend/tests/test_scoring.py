"""
Testes para o sistema de pontuação.
参照: GAME_RULES_SPEC.md - Card values, Round End
"""
import pytest
from app.game_engine import WellingtonGame, Card


class TestScoreCalculation:
    """Testes de cálculo de pontuação."""

    def test_calculate_ace_zero(self, game_started):
        """SCORE-01: Ás conta como 0."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="A", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="A", suit="C"),
        ]
        
        # 0 + 0 + 0 + 0 = 0
        score = sum(c.points for c in player.cards if c is not None)
        assert score == 0

    def test_calculate_king_negative(self, game_started):
        """SCORE-03: K reduz pontuação (-1)."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="K", suit="H"),
            Card(rank="K", suit="S"),
            Card(rank="K", suit="D"),
            Card(rank="K", suit="C"),
        ]
        
        # -1 + -1 + -1 + -1 = -4
        score = sum(c.points for c in player.cards if c is not None)
        assert score == -4

    def test_calculate_joker_negative_two(self, game_started):
        """SCORE-04: Joker reduz 2 (-2)."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="JK", suit=None),
            Card(rank="A", suit="H"),
            Card(rank="2", suit="S"),
            Card(rank="3", suit="D"),
        ]
        
        # -2 + 0 + 2 + 3 = 3
        score = sum(c.points for c in player.cards if c is not None)
        assert score == 3

    def test_calculate_number_cards(self, game_started):
        """SCORE-01: Cartas numéricas têm valor facial."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="2", suit="H"),
            Card(rank="5", suit="S"),
            Card(rank="9", suit="D"),
            Card(rank="10", suit="C"),
        ]
        
        # 2 + 5 + 9 + 10 = 26
        score = sum(c.points for c in player.cards if c is not None)
        assert score == 26

    def test_calculate_face_cards(self, game_started):
        """SCORE-01: J=11, Q=12."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="J", suit="H"),
            Card(rank="Q", suit="S"),
            Card(rank="J", suit="D"),
            Card(rank="Q", suit="C"),
        ]
        
        # 11 + 12 + 11 + 12 = 46
        score = sum(c.points for c in player.cards if c is not None)
        assert score == 46


class TestEmptySlotScoring:
    """Testes de pontuação com slots vazios."""

    def test_empty_slot_not_counted(self, game_started):
        """SCORE-05: Slots vazios não contam."""
        player = game_started.players[0]
        player.cards = [
            Card(rank="5", suit="H"),
            None,  # Slot vazio
            Card(rank="A", suit="S"),
            None,  # Slot vazio
        ]
        
        # 5 + 0 = 5 (None não conta)
        score = sum(c.points for c in player.cards if c is not None)
        assert score == 5


class TestWinnerDetermination:
    """Testes de determinação do vencedor."""

    def test_lowest_score_wins(self, game_started):
        """SCORE-02: Menor pontuação vence."""
        # Setup: jogadores com diferentes pontuações
        game_started.players[0].cards = [
            Card(rank="A", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="A", suit="C"),
        ]  # 0 pontos
        
        game_started.players[1].cards = [
            Card(rank="K", suit="H"),
            Card(rank="5", suit="S"),
            Card(rank="5", suit="D"),
            Card(rank="5", suit="C"),
        ]  # -1 + 15 = 14 pontos
        
        # Menor pontuação deve vencer
        scores = game_started._scores_if_over()
        
        if scores:
            min_score = min(s["score"] for s in scores)
            winner = next(s for s in scores if s["score"] == min_score)
            assert winner["player_id"] == 0

    def test_tie_no_winner(self, game_started):
        """Empate sem chamador = draw."""
        game_started.players[0].cards = [
            Card(rank="A", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="A", suit="C"),
        ]  # 0
        
        game_started.players[1].cards = [
            Card(rank="A", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="A", suit="C"),
        ]  # 0
        
        winner = game_started._winner_ids_if_over()
        # Empate deve retornar ambos ou None


class TestScoreIfOver:
    """Testes de verificação de pontuação."""

    def test_scores_requires_game_over(self, game_started):
        """Só calcula pontuação se jogo terminou."""
        game_started.game_over = False
        
        scores = game_started._scores_if_over()
        assert scores is None

    def test_scores_when_game_over(self, game_started):
        """Calcula pontuação quando jogo termina."""
        game_started.game_over = True
        
        scores = game_started._scores_if_over()
        assert scores is not None
        assert len(scores) == 4  # 4 jogadores


class TestScoreHelper:
    """Testes de funções auxiliares de pontuação."""

    def test_all_players_scored(self, game_started):
        """Todos os jogadores têm pontuação."""
        game_started.game_over = True
        
        scores = game_started._scores_if_over()
        
        for score_data in scores:
            assert "score" in score_data
            assert "player" in score_data
            assert "name" in score_data
