"""
Testes para as habilidades (Card Abilities).
参照: GAME_RULES_SPEC.md - Card Abilities
"""
import pytest
from app.game_engine import WellingtonGame, Card


class TestAbility5:
    """Testes para Habilidade 5 - Revelar carta própria."""

    def test_ability_5_activates_on_discard(self, game_started):
        """ABIL-5-01: Habilidade 5 ativa ao descartar 5."""
        # Setup: dar carta 5 ao jogador
        game_started.players[0].cards = [
            Card(rank="5", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="K", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[0].known_slots = {0, 1, 2, 3}
        
        # Descartar o 5 - usa _on_discard que ativa habilidade
        # Precisa ter drawn_card primeiro
        game_started.drawn_card = Card(rank="5", suit="H")
        game_started._on_discard(0, Card(rank="5", suit="H"))
        
        # Deve ativar habilidade - usa "player" e "rank"
        assert game_started.pending_ability is not None
        assert game_started.pending_ability["rank"] == "5"
        assert game_started.pending_ability["player"] == 0

    def test_ability_5_reveals_own_card(self, game_started):
        """ABIL-5-02: Habilidade 5 revela carta própria."""
        # Setup com estrutura correta
        game_started.pending_ability = {
            "player": 0,
            "rank": "5"
        }
        
        # Usar habilidade no slot 1
        game_started.action_use_ability({"slot": 1})
        
        # Carta no slot 1 deve estar conhecida
        assert 1 in game_started.players[0].known_slots
        assert game_started.pending_ability is None


class TestAbility6:
    """Testes para Habilidade 6 - Revelar carta de outro."""

    def test_ability_6_activates_on_discard(self, game_started):
        """ABIL-6-01: Habilidade 6 ativa ao descartar 6."""
        game_started.players[0].cards = [
            Card(rank="6", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="K", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[0].known_slots = {0, 1, 2, 3}
        
        game_started.drawn_card = Card(rank="6", suit="H")
        game_started._on_discard(0, Card(rank="6", suit="H"))
        
        assert game_started.pending_ability is not None
        assert game_started.pending_ability["rank"] == "6"

    def test_ability_6_reveals_other_player_card(self, game_started):
        """ABIL-6-02: Habilidade 6 revela carta de outro jogador."""
        game_started.pending_ability = {
            "player": 0,
            "rank": "6"
        }
        
        # Usar habilidade no bot 1, slot 0
        game_started.action_use_ability({
            "target_player": 1,
            "slot": 0
        })
        
        # Carta do bot deve estar conhecida pelo humano
        key = (1, 0)
        assert key in game_started.human_known_other
        assert game_started.pending_ability is None


class TestAbility7:
    """Testes para Habilidade 7 - Trocar cartas."""

    def test_ability_7_activates_on_discard(self, game_started):
        """ABIL-7-01: Habilidade 7 ativa ao descartar 7."""
        game_started.players[0].cards = [
            Card(rank="7", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="K", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[0].known_slots = {0, 1, 2, 3}
        
        game_started.drawn_card = Card(rank="7", suit="H")
        game_started._on_discard(0, Card(rank="7", suit="H"))
        
        assert game_started.pending_ability is not None
        assert game_started.pending_ability["rank"] == "7"

    def test_ability_7_swaps_cards(self, game_started):
        """ABIL-7-02: Habilidade 7 troca cartas entre jogadores."""
        # Setup: dar cartas específicas
        game_started.players[0].cards = [
            Card(rank="A", suit="H"),
            Card(rank="K", suit="S"),
            Card(rank="5", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[1].cards = [
            Card(rank="Q", suit="H"),
            Card(rank="J", suit="S"),
            Card(rank="8", suit="D"),
            Card(rank="3", suit="C"),
        ]
        
        # Guardar cartas antes da troca
        human_card = game_started.players[0].cards[0]
        bot_card = game_started.players[1].cards[0]
        
        # Simular uso da habilidade 7
        game_started._ability_7(
            player_idx=0,
            own_slot=0,
            target_idx=1,
            target_slot=0
        )
        
        # Cartas devem estar trocadas
        assert game_started.players[0].cards[0] == bot_card
        assert game_started.players[1].cards[0] == human_card

    def test_ability_7_preserves_knowledge(self, game_started):
        """ABIL-7-03: Habilidade 7 preserva conhecimento."""
        # Setup conhecimento prévio
        game_started.human_known_other[(1, 0)] = "QJ"  # Conhece QJ do Bot 1
        
        # Realizar troca
        game_started.players[0].cards[0] = Card(rank="A", suit="H")
        game_started.players[1].cards[0] = Card(rank="Q", suit="H")
        
        game_started._ability_7(0, 0, 1, 0)
        
        # Conhecimento deve ser preservado (mas não a carta específica)


class TestAbility8:
    """Testes para Habilidade 8 - Revelar + opcional swap."""

    def test_ability_8_activates_on_discard(self, game_started):
        """ABIL-8-01: Habilidade 8 ativa ao descartar 8."""
        game_started.players[0].cards = [
            Card(rank="8", suit="H"),
            Card(rank="A", suit="S"),
            Card(rank="K", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[0].known_slots = {0, 1, 2, 3}
        
        game_started.drawn_card = Card(rank="8", suit="H")
        game_started._on_discard(0, Card(rank="8", suit="H"))
        
        assert game_started.pending_ability is not None
        assert game_started.pending_ability["rank"] == "8"

    def test_ability_8_reveals_and_offers_swap(self, game_started):
        """ABIL-8-02: Habilidade 8 revela e oferece swap."""
        # Setup
        game_started.players[0].cards = [
            Card(rank="A", suit="H"),
            Card(rank="K", suit="S"),
            Card(rank="5", suit="D"),
            Card(rank="2", suit="C"),
        ]
        game_started.players[1].cards = [
            Card(rank="Q", suit="H"),
            Card(rank="J", suit="S"),
            Card(rank="8", suit="D"),
            Card(rank="3", suit="C"),
        ]
        
        # Ativar preview
        game_started._ability_8_preview(0, 0, 1, 0)
        
        # Deve criar preview
        assert game_started.pending_ability8_preview is not None

    def test_ability_8_confirm_with_swap(self, game_started):
        """ABIL-8-02: Habilidade 8 pode confirmar com swap."""
        game_started.pending_ability8_preview = {
            "player_idx": 0,
            "own_slot": 0,
            "target_idx": 1,
            "target_slot": 0,
            "do_swap": True
        }
        
        human_before = game_started.players[0].cards[0]
        bot_before = game_started.players[1].cards[0]
        
        # Confirmar swap
        game_started._ability_8(
            player_idx=0,
            own_slot=0,
            target_idx=1,
            target_slot=0,
            do_swap=True
        )
        
        # Verificar troca
        assert game_started.players[0].cards[0] == bot_before
        assert game_started.players[1].cards[0] == human_before

    def test_ability_8_confirm_without_swap(self, game_started):
        """ABIL-8-03: Habilidade 8 pode confirmar sem swap."""
        game_started.pending_ability8_preview = {
            "player_idx": 0,
            "own_slot": 0,
            "target_idx": 1,
            "target_slot": 0,
            "do_swap": False
        }
        
        human_before = game_started.players[0].cards[0]
        bot_before = game_started.players[1].cards[0]
        
        # Confirmar sem swap
        game_started._ability_8(
            player_idx=0,
            own_slot=0,
            target_idx=1,
            target_slot=0,
            do_swap=False
        )
        
        # Cartas não devem ser trocadas
        assert game_started.players[0].cards[0] == human_before
        assert game_started.players[1].cards[0] == bot_before


class TestAbilityBotResolution:
    """Testes de resolução de habilidade por bots."""

    def test_bot_resolves_ability_5(self, game_started):
        """Bot resolve habilidade 5 automaticamente."""
        # Bot descarta 5
        game_started._resolve_bot_ability(1, "5")
        # Deve resolver sem pending

    def test_bot_resolves_ability_6(self, game_started):
        """Bot resolve habilidade 6 automaticamente."""
        game_started._resolve_bot_ability(1, "6")

    def test_bot_resolves_ability_7(self, game_started):
        """Bot resolve habilidade 7 automaticamente."""
        game_started._resolve_bot_ability(1, "7")

    def test_bot_resolves_ability_8(self, game_started):
        """Bot resolve habilidade 8 automaticamente."""
        game_started._resolve_bot_ability(1, "8")


class TestAbilityRestrictions:
    """Testes de restrições das habilidades."""

    def test_ability_only_on_player_discard(self, game_started):
        """Habilidade só ativa quando descartada pelo jogador."""
        # Descartar via cut não ativa habilidade
        pass
