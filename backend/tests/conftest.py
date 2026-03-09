"""
Fixtures compartilhadas para os testes do jogo Welligton.
"""
import pytest
import sys
from pathlib import Path

# Adicionar o diretório app ao path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.game_engine import WellingtonGame, Card, PlayerState, RANKS, SUITS


@pytest.fixture
def game():
    """Cria um novo jogo com seed fixa para testes determinísticos."""
    return WellingtonGame(seed=42)


@pytest.fixture
def game_started(game):
    """Cria um jogo já iniciado."""
    game.new_game()
    return game


@pytest.fixture
def empty_game():
    """Cria um jogo vazio."""
    return WellingtonGame(seed=1)


@pytest.fixture
def card_ace_hearts():
    """Cria um Ás de Copas."""
    return Card(rank="A", suit="H")


@pytest.fixture
def card_king_spades():
    """Cria um Rei de Espadas."""
    return Card(rank="K", suit="S")


@pytest.fixture
def card_joker():
    """Cria um Coringa."""
    return Card(rank="JK", suit=None)


@pytest.fixture
def card_five():
    """Cria um 5 (ativa habilidade 5)."""
    return Card(rank="5", suit="H")


@pytest.fixture
def card_six():
    """Cria um 6 (ativa habilidade 6)."""
    return Card(rank="6", suit="D")


@pytest.fixture
def card_seven():
    """Cria um 7 (ativa habilidade 7)."""
    return Card(rank="7", suit="C")


@pytest.fixture
def card_eight():
    """Cria um 8 (ativa habilidade 8)."""
    return Card(rank="8", suit="S")


@pytest.fixture
def player_with_cards():
    """Cria um jogador com cartas específicas."""
    player = PlayerState(name="Test Player", is_bot=False)
    player.cards = [
        Card(rank="A", suit="H"),
        Card(rank="K", suit="S"),
        Card(rank="5", suit="D"),
        Card(rank="J", suit="C"),
    ]
    player.known_slots = {2, 3}  # Conhece as últimas duas
    return player


@pytest.fixture
def four_players():
    """Cria 4 jogadores para testes."""
    return [
        PlayerState(name="Voce", is_bot=False),
        PlayerState(name="Bot 1", is_bot=True),
        PlayerState(name="Bot 2", is_bot=True),
        PlayerState(name="Bot 3", is_bot=True),
    ]
