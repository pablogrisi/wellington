"""
Testes para o modelo de cartas (Card).
参照: GAME_RULES_SPEC.md - Deck
"""
import pytest
from app.game_engine import Card, RANKS, SUITS, POINTS


class TestCardPoints:
    """Testes de pontuação das cartas."""

    def test_ace_points_zero(self):
        """CARD-01: Ás = 0 pontos."""
        card = Card(rank="A", suit="H")
        assert card.points == 0

    def test_king_points_minus_one(self):
        """CARD-02: Rei = -1 pontos."""
        card = Card(rank="K", suit="S")
        assert card.points == -1

    def test_joker_points_minus_two(self):
        """CARD-03: Joker = -2 pontos."""
        card = Card(rank="JK", suit=None)
        assert card.points == -2

    def test_number_cards_points(self):
        """CARD-04: Cartas numéricas = valor facial."""
        assert Card(rank="2", suit="H").points == 2
        assert Card(rank="3", suit="D").points == 3
        assert Card(rank="4", suit="C").points == 4
        assert Card(rank="5", suit="S").points == 5
        assert Card(rank="6", suit="H").points == 6
        assert Card(rank="7", suit="D").points == 7
        assert Card(rank="8", suit="C").points == 8
        assert Card(rank="9", suit="S").points == 9
        assert Card(rank="10", suit="H").points == 10

    def test_jack_points_eleven(self):
        """CARD-05: Valete = 11 pontos."""
        card = Card(rank="J", suit="H")
        assert card.points == 11

    def test_queen_points_twelve(self):
        """CARD-06: Rainha = 12 pontos."""
        card = Card(rank="Q", suit="D")
        assert card.points == 12


class TestCardLabel:
    """Testes de rótulo da carta."""

    def test_regular_card_label(self):
        """CARD-08: Carta regular tem formato correto."""
        card = Card(rank="A", suit="H")
        assert card.label() == "AH"

        card = Card(rank="10", suit="S")
        assert card.label() == "10S"

        card = Card(rank="K", suit="C")
        assert card.label() == "KC"

    def test_joker_label(self):
        """CARD-08: Joker tem label específico."""
        card = Card(rank="JK", suit=None)
        assert card.label() == "JK"


class TestDeckConstruction:
    """Testes de construção do baralho."""

    def test_ranks_count(self):
        """Deve haver 13 ranks."""
        assert len(RANKS) == 13

    def test_suits_count(self):
        """Deve haver 4 naipes."""
        assert len(SUITS) == 4

    def test_standard_deck_count(self):
        """52 cartas padrão (13 ranks × 4 suits)."""
        assert len(RANKS) * len(SUITS) == 52

    def test_full_deck_with_jokers(self):
        """54 cartas incluindo 2 Jokers."""
        # 52 regulares + 2 Jokers
        assert len(RANKS) * len(SUITS) + 2 == 54

    def test_all_ranks_present(self):
        """Todos os ranks esperados estão presentes."""
        expected_ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "JK"]
        assert RANKS == expected_ranks[:13]  # 13 ranks without JK

    def test_all_suits_present(self):
        """Todos os naipes esperados estão presentes."""
        expected_suits = ["S", "H", "D", "C"]
        assert SUITS == expected_suits


class TestPointsConstant:
    """Testes do dicionário de pontos."""

    def test_all_ranks_have_points(self):
        """Todos os ranks têm pontuação definida."""
        all_ranks = RANKS + ["JK"]
        for rank in all_ranks:
            assert rank in POINTS, f"Rank {rank} não tem pontuação definida"

    def test_ace_zero_points(self):
        """A = 0."""
        assert POINTS["A"] == 0

    def test_king_negative_points(self):
        """K = -1."""
        assert POINTS["K"] == -1

    def test_joker_most_negative(self):
        """Joker = -2 (mais negativo)."""
        assert POINTS["JK"] == -2

    def test_number_cards_face_value(self):
        """Cartas numéricas têm valor facial."""
        for num in ["2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            assert POINTS[num] == int(num)

    def test_jack_eleven(self):
        """J = 11."""
        assert POINTS["J"] == 11

    def test_queen_twelve(self):
        """Q = 12."""
        assert POINTS["Q"] == 12
