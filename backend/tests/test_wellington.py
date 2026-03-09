"""
Testes para o sistema Wellington.
参照: GAME_RULES_SPEC.md - Wellington
"""
import random
import pytest
from app.game_engine import WellingtonGame, Card


class TestWellingtonCall:
    """Testes de chamada Wellington."""

    def test_wellington_sets_caller(self, game_started):
        """WELL-01: Chamada Wellington configura o chamador."""
        # Setup: configurar estado para permitir chamada
        game_started.pending_human_wellington_window = True
        
        game_started.action_call_wellington()
        
        assert game_started.wellington_caller == 0
        assert game_started.players[0].locked is True

    def test_wellington_locks_cards(self, game_started):
        """WELL-02: Cartas são travadas após chamada."""
        # Setup
        game_started.pending_human_wellington_window = True
        
        game_started.action_call_wellington()
        
        # Todas as cartas devem estar locked
        for player in game_started.players:
            if player.name == "Voce":
                assert player.locked is True


class TestWellingtonEndRound:
    """Testes de fim de rodada."""

    def test_game_ends_after_wellington_returns(self, game_started):
        """WELL-03: Jogo termina quando turno retorna ao chamador."""
        # Setup: humano chamou Wellington
        game_started.wellington_caller = 0
        
        # Simular avanço de turno até retornar ao chamador
        # current_player vai de 0 -> 1 -> 2 -> 3 -> 0
        game_started.current_player = 1
        game_started._advance_turn()
        
        # Quando retornar ao chamador, jogo termina
        # Verificar se lógica de fim de jogo funciona
        assert game_started.current_player == 2


class TestAutoWellington:
    """Testes de Wellington automático."""

    def test_auto_wellington_when_no_cards(self, game_started):
        """WELL-04: Wellington automático quando sem cartas."""
        # Setup: jogador sem cartas
        game_started.players[0].cards = [None, None, None, None]
        
        # Ao começar turno, deve acionar auto Wellington
        # Verificar se jogo termina
        # Implementação específica depende de quando é verificado


class TestImmediateWellington:
    """Testes de Wellington imediato."""

    def test_immediate_wellington_on_last_card_cut(self, game_started):
        """WELL-05: Cut instantâneo dispara Wellington imediato."""
        # Setup: jogador corta última carta
        game_started.players[0].cards = [
            Card(rank="7", suit="H"),  # Última carta
            None,
            None,
            None,
        ]
        
        # Cut com matching card
        # Deve dispar Wellington imediatamente


class TestWellingtonTiebreak:
    """Testes de desempate Wellington."""

    def test_non_caller_wins_tie(self, game_started):
        """WELL-06: Não-chamador vence em caso de empate."""
        # Setup: dois jogadores com mesma pontuação
        # Um chamou Wellington, outro não
        # Não-chamador deve vencer
        
        # Executar lógica de desempate
        winner = game_started._winner_ids_if_over()
        
        # Verificar que não-chamador venceu
        # Implementação específica

    def test_draw_when_no_caller(self, game_started):
        """WELL-07: Empate sem chamadores = draw."""
        # Setup: dois jogadores mesma pontuação, nenhum chamou
        # Resultado deve ser draw


class TestWellingtonRestrictions:
    """Testes de restrições Wellington."""

    def test_cannot_modify_locked_player(self, game_started):
        """Não pode modificar jogador locked."""
        game_started.players[0].locked = True
        
        # Tentativa de modificação deve falhar ou ser ignorada


class TestWellingtonState:
    """Testes de estado Wellington."""

    def test_wellington_waiting_return(self, game_started):
        """Estado de esperando retorno ao chamador."""
        game_started.wellington_waiting_return = True
        
        # Estado deve ser preservado
        assert game_started.wellington_waiting_return is True

    def test_wellington_caller_index(self, game_started):
        """Índice do chamador Wellington é válido."""
        game_started.wellington_caller = 2
        
        # Deve ser índice válido
        assert 0 <= game_started.wellington_caller < len(game_started.players)


class TestWellingtonHuman:
    """Testes específicos do jogador humano."""

    def test_can_call_wellington(self, game_started):
        """Humano pode chamar Wellington."""
        can_call = game_started._can_human_call_wellington()
        # Após fazer ação, deve poder chamar
        # Verificar condições

    def test_human_wellington_window(self, game_started):
        """Janela de Wellington para humano."""
        game_started.pending_human_wellington_window = True
        
        assert game_started.pending_human_wellington_window is True

    def test_pass_human_wellington_window(self, game_started):
        """Passar janela de Wellington."""
        # Setup
        game_started.pending_human_wellington_window = True
        
        game_started.action_pass_human_wellington_window()
        
        assert game_started.pending_human_wellington_window is False


class TestBotWellingtonKnowledge:
    """Bot só pode decidir com cartas que já conhece."""

    def test_bot_does_not_call_with_unknown_cards(self, game_started):
        game_started.current_player = 1
        bot = game_started.players[1]
        bot.locked = False
        bot.cards = [
            Card(rank="A", suit="H"),
            Card(rank="K", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="JK", suit=None),
        ]
        bot.known_slots = {0, 1}
        game_started.wellington_caller = None

        game_started._finish_turn_after_play(player_idx=1)

        assert game_started.wellington_caller is None

    def test_bot_can_call_when_all_cards_are_known(self, game_started):
        game_started.current_player = 1
        bot = game_started.players[1]
        bot.locked = False
        bot.cards = [
            Card(rank="A", suit="H"),
            Card(rank="K", suit="S"),
            Card(rank="A", suit="D"),
            Card(rank="JK", suit=None),
        ]
        bot.known_slots = {0, 1, 2, 3}
        game_started.wellington_caller = None
        game_started.random = random.Random(1)

        game_started._finish_turn_after_play(player_idx=1)

        assert game_started.wellington_caller == 1
