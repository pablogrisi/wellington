import random
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("wellington")

RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
SUITS = ["S", "H", "D", "C"]

POINTS = {
    "A": 0,
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "10": 10,
    "J": 11,
    "Q": 12,
    "K": -1,
    "JK": -2,
}


@dataclass
class Card:
    rank: str
    suit: Optional[str]

    @property
    def points(self) -> int:
        return POINTS[self.rank]

    def label(self) -> str:
        if self.rank == "JK":
            return "JK"
        return f"{self.rank}{self.suit}"


@dataclass
class PlayerState:
    name: str
    is_bot: bool
    cards: List[Optional[Card]] = field(default_factory=list)
    known_slots: set[int] = field(default_factory=set)
    locked: bool = False


class WellingtonGame:
    def __init__(self, seed: Optional[int] = None):
        self.random = random.Random(seed)
        self.players: List[PlayerState] = []
        self.draw_pile: List[Card] = []
        self.discard_pile: List[Card] = []
        self.current_player: int = 0
        self.drawn_card: Optional[Card] = None
        self.wellington_caller: Optional[int] = None
        self.game_over: bool = False
        self.pending_ability: Optional[Dict[str, Any]] = None
        self.pending_ability8_preview: Optional[Dict[str, Any]] = None
        self.pending_human_cut: bool = False
        self.pending_human_cut_other_transfer: Optional[Dict[str, Any]] = None
        self.pending_discard_resolution: Optional[Dict[str, Any]] = None
        self.pending_bot_cut: bool = False
        self.pending_bot_cut_action: Optional[Dict[str, Any]] = None
        self.human_cut_available_until_draw: bool = False
        self.pending_human_wellington_window: bool = False
        self.paused: bool = False
        self.wellington_waiting_return: bool = False
        self.pending_bot_turn: Optional[Dict[str, Any]] = None
        self.bot_visual: Dict[int, Dict[str, Any]] = {}
        self.human_known_other: Dict[tuple[int, int], str] = {}
        self.log: List[str] = []
        self.last_bot_action: Optional[str] = None
        self.cut_window_opened_at: Optional[float] = None

    def new_game(self) -> None:
        deck = self._build_deck()
        self.random.shuffle(deck)

        self.players = [
            PlayerState("Voce", is_bot=False),
            PlayerState("Bot 1", is_bot=True),
            PlayerState("Bot 2", is_bot=True),
            PlayerState("Bot 3", is_bot=True),
        ]

        for player in self.players:
            player.cards = [deck.pop(), deck.pop(), deck.pop(), deck.pop()]
            player.known_slots = {2, 3}
            player.locked = False

        self.draw_pile = deck
        self.discard_pile = [self.draw_pile.pop()]
        self.current_player = 0
        self.drawn_card = None
        self.wellington_caller = None
        self.game_over = False
        self.pending_ability = None
        self.pending_ability8_preview = None
        self.pending_human_cut = False
        self.pending_human_cut_other_transfer = None
        self.pending_discard_resolution = None
        self.pending_bot_cut = False
        self.human_cut_available_until_draw = False
        self.pending_human_wellington_window = False
        self.paused = False
        self.wellington_waiting_return = False
        self.pending_bot_turn = None
        self.bot_visual = {}
        self.human_known_other = {}
        self.log = ["Nova partida iniciada."]
        self.last_bot_action = None

    def to_state_dict(self) -> Dict[str, Any]:
        return {
            "players": [
                {
                    "name": p.name,
                    "is_bot": p.is_bot,
                    "cards": [self._card_to_dict(c) for c in p.cards],
                    "known_slots": sorted(p.known_slots),
                    "locked": p.locked,
                }
                for p in self.players
            ],
            "draw_pile": [self._card_to_dict(c) for c in self.draw_pile],
            "discard_pile": [self._card_to_dict(c) for c in self.discard_pile],
            "current_player": self.current_player,
            "drawn_card": self._card_to_dict(self.drawn_card),
            "wellington_caller": self.wellington_caller,
            "game_over": self.game_over,
            "pending_ability": self.pending_ability,
            "pending_ability8_preview": self.pending_ability8_preview,
            "pending_human_cut": self.pending_human_cut,
            "pending_human_cut_other_transfer": self.pending_human_cut_other_transfer,
            "pending_discard_resolution": self.pending_discard_resolution,
            "pending_bot_cut": self.pending_bot_cut,
            "human_cut_available_until_draw": self.human_cut_available_until_draw,
            "pending_human_wellington_window": self.pending_human_wellington_window,
            "paused": self.paused,
            "wellington_waiting_return": self.wellington_waiting_return,
            "pending_bot_turn": self.pending_bot_turn,
            "bot_visual": self.bot_visual,
            "human_known_other": [
                {"player": p, "slot": s, "label": label}
                for (p, s), label in self.human_known_other.items()
            ],
            "log": self.log,
        }

    def load_state_dict(self, data: Dict[str, Any]) -> None:
        self.players = []
        for p_data in data.get("players", []):
            player = PlayerState(
                name=p_data["name"],
                is_bot=bool(p_data["is_bot"]),
            )
            player.cards = [self._card_from_dict(c) for c in p_data.get("cards", [])]
            player.known_slots = set(int(v) for v in p_data.get("known_slots", []))
            player.locked = bool(p_data.get("locked", False))
            self.players.append(player)

        self.draw_pile = [self._card_from_dict(c) for c in data.get("draw_pile", []) if c is not None]
        self.discard_pile = [self._card_from_dict(c) for c in data.get("discard_pile", []) if c is not None]
        self.current_player = int(data.get("current_player", 0))
        self.drawn_card = self._card_from_dict(data.get("drawn_card"))
        self.wellington_caller = data.get("wellington_caller")
        self.game_over = bool(data.get("game_over", False))
        self.pending_ability = data.get("pending_ability")
        self.pending_ability8_preview = data.get("pending_ability8_preview")
        self.pending_human_cut = bool(data.get("pending_human_cut", False))
        self.pending_human_cut_other_transfer = data.get("pending_human_cut_other_transfer")
        self.pending_discard_resolution = data.get("pending_discard_resolution")
        self.pending_bot_cut = bool(data.get("pending_bot_cut", False))
        self.human_cut_available_until_draw = bool(data.get("human_cut_available_until_draw", False))
        self.pending_human_wellington_window = bool(data.get("pending_human_wellington_window", False))
        self.paused = bool(data.get("paused", False))
        self.wellington_waiting_return = bool(
            data.get(
                "wellington_waiting_return",
                self.wellington_caller is not None and not self.game_over,
            )
        )
        raw_pending_bot_turn = data.get("pending_bot_turn")
        self.pending_bot_turn = raw_pending_bot_turn if isinstance(raw_pending_bot_turn, dict) else None
        raw_bot_visual = data.get("bot_visual", {})
        if isinstance(raw_bot_visual, dict):
            self.bot_visual = {int(k): v for k, v in raw_bot_visual.items()}
        else:
            self.bot_visual = {}
        self.human_known_other = {
            (int(item["player"]), int(item["slot"])): str(item.get("label", item.get("rank", "")))
            for item in data.get("human_known_other", [])
        }
        self.log = [str(line) for line in data.get("log", [])]

    @staticmethod
    def _card_to_dict(card: Optional["Card"]) -> Optional[Dict[str, Any]]:
        if card is None:
            return None
        return {"rank": card.rank, "suit": card.suit}

    @staticmethod
    def _card_from_dict(payload: Optional[Dict[str, Any]]) -> Optional["Card"]:
        if payload is None:
            return None
        return Card(rank=str(payload["rank"]), suit=payload.get("suit"))

    # ---------- Public API ----------

    def run_bots_until_human(self) -> None:
        self._sanitize_human_cut_state()
        while not self.game_over:
            if self.paused:
                return
            if self.pending_ability is not None:
                return
            if self.pending_human_cut_other_transfer is not None:
                return
            if self.pending_bot_cut:
                if self.pending_discard_resolution is not None:
                    self._resolve_bot_cuts(int(self.pending_discard_resolution["player"]))
                self.pending_bot_cut = False
                self.cut_window_opened_at = None
                self._process_pending_discard_flow()
                continue
            if (
                self.pending_human_cut
                or self.pending_human_cut_other_transfer is not None
                or self.pending_ability is not None
            ):
                return
            if self.current_player == 0:
                return
            self._bot_turn(self.current_player)

    def can_bot_step(self) -> bool:
        self._sanitize_human_cut_state()
        if self.pending_ability is not None:
            return False
        if self.pending_human_cut_other_transfer is not None:
            return False
        if self.pending_bot_cut:
            # Check if cut window delay (2.5 seconds) has passed
            if self.cut_window_opened_at is not None:
                elapsed = time.time() - self.cut_window_opened_at
                if elapsed < 2.5:
                    return False
            result = not self.game_over and not self.paused
            return result
        result = (
            not self.game_over
            and not self.paused
            and self.current_player != 0
            and not self.pending_human_cut
            and self.pending_human_cut_other_transfer is None
            and self.pending_ability is None
        )
        return result

    def bot_step(self) -> bool:
        if not self.can_bot_step():
            return False
        if self.pending_bot_cut:
            if self.pending_discard_resolution is not None:
                self._resolve_bot_cuts(int(self.pending_discard_resolution["player"]))
            # Só limpa pending_bot_cut se não há mais cortes agendados
            if not self.pending_bot_cut_action:
                self.pending_bot_cut = False
                self.cut_window_opened_at = None
                self._process_pending_discard_flow()
            return True
        self._bot_turn(self.current_player)
        return True

    def action_pause(self) -> None:
        if not self.paused:
            self.paused = True
            self._log("Jogo pausado.")

    def action_resume(self) -> None:
        if self.paused:
            self.paused = False
            self._log("Jogo retomado.")

    def action_draw(self) -> None:
        self._ensure_not_over()
        self._ensure_human_turn()
        if self.pending_ability is not None:
            raise ValueError("Resolva a habilidade pendente.")
        if self.pending_human_wellington_window:
            raise ValueError("Aguarde a janela de Wellington encerrar.")
        if self.drawn_card is not None:
            raise ValueError("Voce ja comprou uma carta nesta rodada.")
        self._clear_bot_visual_next_draw()
        self.drawn_card = self._draw_card()
        self.pending_human_cut = False
        self.human_cut_available_until_draw = False
        self._log(f"Voce comprou {self.drawn_card.label()}.")

    def action_discard_drawn(self) -> None:
        self._ensure_not_over()
        self._ensure_human_turn()
        self._ensure_no_pending()
        if self.drawn_card is None:
            raise ValueError("Compre uma carta antes de descartar.")

        discarded = self.drawn_card
        self.drawn_card = None
        self.discard_pile.append(discarded)
        self._log(f"Voce descartou {discarded.label()}.")

        self._on_discard(player_idx=0, card=discarded)

    def action_replace(self, slot: int) -> None:
        self._ensure_not_over()
        self._ensure_human_turn()
        self._ensure_no_pending()
        if self.drawn_card is None:
            raise ValueError("Compre uma carta antes de trocar.")

        player = self.players[0]
        self._validate_slot(player, slot)
        old = player.cards[slot]
        if old is None:
            raise ValueError("Nao da para trocar em slot vazio.")

        new_card = self.drawn_card
        self.drawn_card = None
        player.cards[slot] = new_card
        player.known_slots.add(slot)

        self.discard_pile.append(old)
        
        self._log(f"Voce trocou slot {slot} por {new_card.label()} e descartou {old.label()}.")

        self._on_discard(player_idx=0, card=old)

    def action_call_wellington(self) -> None:
        self._ensure_not_over()
        self._ensure_human_turn()
        if self.pending_human_cut_other_transfer is not None:
            raise ValueError("Escolha a carta para enviar ao outro jogador antes de chamar Wellington.")
        if not self.pending_human_wellington_window:
            raise ValueError("Voce so pode chamar Wellington apos finalizar sua jogada.")
        if self.wellington_caller is not None:
            raise ValueError("Wellington ja foi chamado.")

        self.wellington_caller = 0
        self.wellington_waiting_return = True
        self.players[0].locked = True
        self.pending_human_cut = False
        self.human_cut_available_until_draw = False
        self.pending_human_wellington_window = False
        self._log("Voce chamou Wellington e travou suas cartas.")
        self._advance_turn()

    def action_pass_human_wellington_window(self) -> None:
        self._ensure_not_over()
        if not self.pending_human_wellington_window:
            raise ValueError("Nao ha janela de Wellington pendente.")
        if self.pending_human_cut_other_transfer is not None:
            raise ValueError("Escolha a carta para enviar ao outro jogador antes de passar.")
        self.pending_human_cut = False
        self.human_cut_available_until_draw = False
        self.pending_human_wellington_window = False
        self._advance_turn()

    def action_skip_cut(self) -> None:
        self._ensure_not_over()
        if not self._can_human_cut_now():
            raise ValueError("Nao ha corte pendente.")
        if self.current_player == 0 and self.drawn_card is None:
            if self.human_cut_available_until_draw:
                self.pending_human_cut = False
                self._log("Voce passou no corte por enquanto.")
                return
            self.pending_human_cut = False
            self._log("Voce passou no corte.")
            if self.pending_discard_resolution is not None:
                self._process_pending_discard_flow()
                return
            if self.pending_ability is not None:
                return
            if self.pending_human_wellington_window:
                return
            self._advance_turn()
            return
        self.pending_human_cut = False
        self._log("Voce passou no corte.")
        if self.pending_discard_resolution is not None:
            self._process_pending_discard_flow()
            return
        self._finish_turn_after_play(player_idx=self.current_player)

    def action_cut_self(self, slot: int) -> None:
        self._ensure_not_over()
        if not self._can_human_cut_now():
            raise ValueError("Nao ha corte pendente.")

        top = self._top_discard()
        player = self.players[0]
        self._validate_slot(player, slot)
        card = player.cards[slot]
        if card is None:
            raise ValueError("Slot vazio para corte.")

        if card.rank == top.rank:
            player.cards[slot] = None
            player.known_slots.discard(slot)
            self.discard_pile.append(card)
            self._log(f"Voce cortou com sucesso usando {card.label()} (slot {slot}).")
            # Apos corte, abrimos nova janela de 3s para cortes em sequencia.
            self.pending_human_cut = True
            self.human_cut_available_until_draw = False
            return
        else:
            self._penalty_blind_draw(0, 2)
            self._log(
                f"Corte errado! Voce tentou {card.label()} em cima de {top.label()} e comprou 2 cegas."
            )

        self.pending_human_cut = False
        if self.current_player == 0 and self.drawn_card is None:
            if self.pending_discard_resolution is not None:
                self._process_pending_discard_flow()
                return
            if self.pending_ability is not None:
                return
            if self.pending_human_wellington_window:
                return
            self._advance_turn()
            return
        if self.pending_discard_resolution is not None:
            self._process_pending_discard_flow()
            return
        self._finish_turn_after_play(player_idx=self.current_player)

    def action_cut_other(self, target_player: int, target_slot: int, give_slot: Optional[int]) -> None:
        self._ensure_not_over()
        human = self.players[0]

        # Fase 2: corte ja confirmado, aguardando o humano escolher qual carta enviar.
        if self.pending_human_cut_other_transfer is not None:
            transfer = self.pending_human_cut_other_transfer
            transfer_target_player = int(transfer["target_player"])
            transfer_target_slot = int(transfer["target_slot"])
            target = self.players[transfer_target_player]

            if give_slot is None:
                raise ValueError("Escolha qual carta sua sera enviada.")
            self._validate_slot(human, give_slot)
            give_card = human.cards[give_slot]
            if give_card is None:
                raise ValueError("Seu slot escolhido esta vazio.")

            target.cards[transfer_target_slot] = give_card
            human.cards[give_slot] = None
            human.known_slots.discard(give_slot)
            # O humano ja conhecia a carta enviada, entao o conhecimento acompanha a carta no novo slot.
            self.human_known_other[(transfer_target_player, transfer_target_slot)] = give_card.label()
            self.pending_human_cut_other_transfer = None
            self._log(
                f"Voce enviou sua carta do slot {give_slot} para {target.name}, slot {transfer_target_slot}."
            )
            # Apos concluir corte com carta de outro, abre nova janela de 3s para cortes em sequencia.
            self.pending_human_cut = True
            self.human_cut_available_until_draw = False
            return

        # Fase 1: tentativa de corte com carta de outro jogador.
        if not self._can_human_cut_now():
            raise ValueError("Nao ha corte pendente.")
        if target_player == 0:
            raise ValueError("Use corte normal para suas cartas.")
        if target_player < 0 or target_player >= len(self.players):
            raise ValueError("Jogador alvo invalido.")

        top = self._top_discard()
        target = self.players[target_player]
        self._validate_slot(target, target_slot)
        target_card = target.cards[target_slot]
        if target_card is None:
            raise ValueError("Slot alvo vazio.")

        # A carta alvo sempre sai da mesa (acertando ou errando), conforme regra.
        target.cards[target_slot] = None
        self._forget_human_knowledge(target_player, target_slot)
        self.discard_pile.append(target_card)

        if target_card.rank == top.rank:
            self.pending_human_cut = False
            self.pending_human_cut_other_transfer = {
                "target_player": target_player,
                "target_slot": target_slot,
            }
            self._log(
                f"Corte certo com carta de {target.name} ({target_card.label()}). Escolha sua carta para enviar."
            )
            return

        self._penalty_blind_draw(0, 1)
        self._log(
            f"Corte errado com carta de outro jogador! Era {target_card.label()}, topo era {top.label()}. "
            "Voce comprou 1 cega e o jogador alvo perdeu a carta."
        )
        self.pending_human_cut = True
        self.human_cut_available_until_draw = False
        return

    def action_use_ability(self, payload: Dict[str, Any]) -> None:
        self._ensure_not_over()
        if not self.pending_ability:
            raise ValueError("Nao ha habilidade pendente.")
        if self.pending_ability["player"] != 0:
            raise ValueError("Nao e sua habilidade pendente.")

        rank = self.pending_ability["rank"]
        if rank == "5":
            slot = int(payload.get("slot", -1))
            self._ability_5(0, slot)
        elif rank == "6":
            target = int(payload.get("target_player", -1))
            slot = int(payload.get("slot", -1))
            self._ability_6(0, target, slot)
        elif rank == "7":
            own_slot = int(payload.get("own_slot", -1))
            target = int(payload.get("target_player", -1))
            target_slot = int(payload.get("target_slot", -1))
            self._ability_7(0, own_slot, target, target_slot)
        elif rank == "8":
            if bool(payload.get("preview", False)):
                own_slot = int(payload.get("own_slot", -1))
                target = int(payload.get("target_player", -1))
                target_slot = int(payload.get("target_slot", -1))
                self._ability_8_preview(0, own_slot, target, target_slot)
                return

            if self.pending_ability8_preview:
                own_slot = int(self.pending_ability8_preview["own_slot"])
                target = int(self.pending_ability8_preview["target_player"])
                target_slot = int(self.pending_ability8_preview["target_slot"])
            else:
                own_slot = int(payload.get("own_slot", -1))
                target = int(payload.get("target_player", -1))
                target_slot = int(payload.get("target_slot", -1))
            do_swap = bool(payload.get("do_swap", False))
            self._ability_8(0, own_slot, target, target_slot, do_swap)
        else:
            raise ValueError("Habilidade invalida.")

        self.pending_ability8_preview = None
        self.pending_ability = None
        if self.pending_discard_resolution is not None:
            self.pending_discard_resolution["ability_resolved"] = True

        # Apos resolver a habilidade, o humano pode cortar imediatamente em sequencia.
        if self.pending_discard_resolution is not None and self._check_human_cut_opportunity(0):
            self.pending_human_cut = True
            self.human_cut_available_until_draw = False
            return

        self._process_pending_discard_flow()

    def public_state(self) -> Dict[str, Any]:
        self._sanitize_human_cut_state()
        top = self._top_discard()
        players_payload = []
        for p_idx, player in enumerate(self.players):
            cards_payload = []
            for slot, card in enumerate(player.cards):
                known, text = self._human_view_card(p_idx, slot, card)
                cards_payload.append(
                    {
                        "slot": slot,
                        "known": known,
                        "text": text,
                        "is_empty": card is None,
                    }
                )

            players_payload.append(
                {
                    "id": p_idx,
                    "name": player.name,
                    "is_bot": player.is_bot,
                    "locked": player.locked,
                    "cards": cards_payload,
                    "card_count": sum(1 for c in player.cards if c is not None),
                    "bot_visual": self.bot_visual.get(p_idx, {"side": None, "slot_discarded": None}),
                }
            )

        ability = None
        if self.pending_ability and self.pending_ability["player"] == 0:
            ability = self.pending_ability

        human_drawn_label = None
        if self.current_player == 0 and self.drawn_card is not None:
            human_drawn_label = self.drawn_card.label()

        return {
            "game_over": self.game_over,
            "current_player": self.current_player,
            "wellington_caller": self.wellington_caller,
            "top_discard": top.label() if top else None,
            "draw_pile_count": len(self.draw_pile),
            "drawn_card": human_drawn_label,
            "pending_human_cut": self.pending_human_cut,
            "pending_human_cut_other_transfer": self.pending_human_cut_other_transfer,
            "pending_bot_cut": self.pending_bot_cut,
            "human_cut_available_until_draw": self.human_cut_available_until_draw,
            "pending_human_wellington_window": self.pending_human_wellington_window,
            "paused": self.paused,
            "cut_options": self._human_cut_options(),
            "pending_ability": ability,
            "pending_ability8_preview": self.pending_ability8_preview,
            "pending_bot_turn": self.pending_bot_turn,
            "last_bot_action": self.last_bot_action,
            "bot_delay_ms": 3000,
            "bot_cut_delay_ms": 2500,
            "players": players_payload,
            "scores": self._scores_if_over(),
            "winner_ids": self._winner_ids_if_over(),
            "log": self.log[-20:],
            "actions": {
                "can_draw": self._can_human_draw(),
                "can_discard_drawn": self._can_human_discard_drawn(),
                "replace_slots": self._human_replace_slots(),
                "can_call_wellington": self._can_human_call_wellington(),
                "can_cut": self._can_human_cut_now(),
                "can_send_cut_other_card": self.pending_human_cut_other_transfer is not None,
                "send_cut_other_slots": self._human_send_cut_other_slots(),
                "can_bot_step": self.can_bot_step(),
            },
        }

    # ---------- Core ----------

    def _build_deck(self) -> List[Card]:
        deck = [Card(rank=r, suit=s) for r in RANKS for s in SUITS]
        deck.append(Card(rank="JK", suit=None))
        deck.append(Card(rank="JK", suit=None))
        return deck

    def _ensure_not_over(self) -> None:
        if self.game_over:
            raise ValueError("A partida acabou.")
        if self.paused:
            raise ValueError("A partida esta pausada.")

    def _ensure_human_turn(self) -> None:
        if self.current_player != 0:
            raise ValueError("Nao e sua vez.")
        if self.players[0].locked:
            raise ValueError("Voce esta travado apos chamar Wellington.")

    def _ensure_no_pending(self) -> None:
        if self.pending_human_cut:
            raise ValueError("Resolva o corte pendente.")
        if self.pending_human_cut_other_transfer is not None:
            raise ValueError("Escolha a carta para enviar ao outro jogador.")
        if self.pending_ability is not None:
            raise ValueError("Resolva a habilidade pendente.")
        if self.pending_human_wellington_window:
            raise ValueError("Aguarde a janela de Wellington encerrar.")

    def _draw_card(self) -> Card:
        if not self.draw_pile:
            self._rebuild_draw_from_discard()
        if not self.draw_pile:
            raise ValueError("Sem cartas para comprar.")
        return self.draw_pile.pop()

    def _rebuild_draw_from_discard(self) -> None:
        if len(self.discard_pile) <= 1:
            return
        top = self.discard_pile[-1]
        recyclable = self.discard_pile[:-1]
        self.random.shuffle(recyclable)
        self.draw_pile.extend(recyclable)
        self.discard_pile = [top]

    def _has_bot_cut_candidates(self, discarder_idx: int) -> bool:
        top = self._top_discard()
        if top is None:
            return False
        order = [discarder_idx] + [
            (discarder_idx + offset) % len(self.players)
            for offset in range(1, len(self.players))
        ]
        for idx in order:
            if idx == 0:
                continue
            p = self.players[idx]
            if p.locked:
                continue
            matching_known = [
                s for s, c in enumerate(p.cards)
                if c is not None and c.rank == top.rank and s in p.known_slots
            ]
            if matching_known:
                return True
        return False

    def _process_pending_discard_flow(self) -> None:
        if self.pending_discard_resolution is None:
            return
        if self.pending_bot_cut:
            return
        if self.pending_human_cut or self.pending_human_cut_other_transfer is not None:
            return
        if self.pending_ability is not None:
            return

        ctx = self.pending_discard_resolution
        self.pending_discard_resolution = None
        player_idx = int(ctx["player"])
        discarded_rank = str(ctx["rank"])

        if (
            discarded_rank in {"5", "6", "7", "8"}
            and not self.players[player_idx].locked
            and not bool(ctx.get("ability_resolved", False))
        ):
            if player_idx == 0:
                self.pending_ability = {"player": 0, "rank": discarded_rank}
                self._log(f"Habilidade da carta {discarded_rank} pendente para voce.")
                return
            self._resolve_bot_ability(player_idx, discarded_rank)

        self._finish_turn_after_play(player_idx=player_idx)

    def _on_discard(self, player_idx: int, card: Card) -> None:
        self.pending_discard_resolution = {
            "player": player_idx,
            "rank": card.rank,
            "ability_resolved": False,
        }

        is_human_special_discard = (
            player_idx == 0
            and card.rank in {"5", "6", "7", "8"}
            and not self.players[0].locked
        )
        if is_human_special_discard:
            # Habilidade especial do humano abre imediatamente apos descartar.
            self.pending_human_cut = False
            self.human_cut_available_until_draw = False
            self.pending_ability8_preview = None
            self.pending_ability = {"player": 0, "rank": card.rank}
            self._log(f"Habilidade da carta {card.rank} pendente para voce.")
        else:
            has_human_cut_opportunity = self._check_human_cut_opportunity(player_idx)
            if has_human_cut_opportunity:
                self.pending_human_cut = True
                # Se outro jogador descartou, o humano pode cortar ate comprar.
                # Se foi o proprio descarte do humano, resolve corte e segue o fluxo da vez.
                self.human_cut_available_until_draw = player_idx != 0
            else:
                self.pending_human_cut = False

        self.pending_bot_cut = self._has_bot_cut_candidates(player_idx)
        if self.pending_bot_cut:
            # Record when the cut window opened for the 2.5 second delay
            self.cut_window_opened_at = time.time()
            return

        self._process_pending_discard_flow()

    def _advance_turn(self) -> None:
        next_idx = (self.current_player + 1) % len(self.players)
        if (
            self.wellington_caller is not None
            and self.wellington_waiting_return
            and next_idx == self.wellington_caller
        ):
            self._finish_game()
            return

        self._clear_bot_visual_next_turn()
        self.current_player = next_idx
        self.drawn_card = None
        self.pending_human_wellington_window = False
        self.last_bot_action = None

        current = self.players[self.current_player]
        current_has_cards = any(c is not None for c in current.cards)
        if self.wellington_caller is None and not current.locked and not current_has_cards:
            self.wellington_caller = self.current_player
            self.wellington_waiting_return = True
            current.locked = True
            self._log(f"{current.name} chamou Wellington automaticamente (sem cartas na vez).")
            self._advance_turn()
            return

        if self.players[self.current_player].is_bot:
            return

    def _finish_game(self) -> None:
        self.game_over = True
        self.drawn_card = None
        self.pending_human_cut = False
        self.pending_human_cut_other_transfer = None
        self.pending_discard_resolution = None
        self.pending_bot_cut = False
        self.cut_window_opened_at = None
        self.human_cut_available_until_draw = False
        self.pending_ability = None
        self.pending_ability8_preview = None
        self.pending_human_wellington_window = False
        self.pending_bot_turn = None
        self.bot_visual = {}
        self.wellington_waiting_return = False
        self._log("Partida encerrada por Wellington. Cartas reveladas.")

    def _finish_turn_after_play(self, player_idx: int) -> None:
        player = self.players[player_idx]

        if (
            player_idx == 0
            and not self.game_over
            and self.wellington_caller is None
            and not player.locked
        ):
            self.pending_human_wellington_window = True
            self._log("Janela de Wellington aberta por 3s.")
            return

        if (
            player.is_bot
            and self.wellington_caller is None
            and not player.locked
        ):
            non_empty_slots = [i for i, c in enumerate(player.cards) if c is not None]
            all_cards_known = all(slot in player.known_slots for slot in non_empty_slots)
            if all_cards_known:
                total = sum(player.cards[slot].points for slot in non_empty_slots if player.cards[slot] is not None)
            else:
                total = None

            if total is not None and total <= 3 and self.random.random() < 0.45:
                self.wellington_caller = player_idx
                self.wellington_waiting_return = True
                player.locked = True
                self._log(f"{player.name} chamou Wellington.")

        self._advance_turn()

    # ---------- Abilities ----------

    def _ability_5(self, player_idx: int, slot: int) -> None:
        player = self.players[player_idx]
        self._validate_slot(player, slot)
        card = player.cards[slot]
        if card is None:
            raise ValueError("Slot vazio.")
        player.known_slots.add(slot)
        if player_idx == 0:
            self._log(f"Habilidade 5: voce viu seu slot {slot} ({card.label()}).")

    def _ability_6(self, player_idx: int, target_idx: int, slot: int) -> None:
        if target_idx < 0 or target_idx >= len(self.players):
            raise ValueError("Jogador alvo invalido.")
        if target_idx == player_idx:
            raise ValueError("Habilidade 6 so permite ver carta de outro jogador.")
        target = self.players[target_idx]
        self._validate_slot(target, slot)
        card = target.cards[slot]
        if card is None:
            raise ValueError("Slot vazio.")

        if player_idx == 0:
            if target_idx == 0:
                self.players[0].known_slots.add(slot)
            else:
                self.human_known_other[(target_idx, slot)] = card.label()
            self._log(f"Habilidade 6: voce viu {card.label()} do jogador {target_idx}, slot {slot}.")
        else:
            if target_idx == player_idx:
                self.players[player_idx].known_slots.add(slot)

    def _ability_7(self, player_idx: int, own_slot: int, target_idx: int, target_slot: int) -> None:
        if target_idx == player_idx:
            raise ValueError("Escolha outro jogador para habilidade 7.")
        own = self.players[player_idx]
        target = self.players[target_idx]
        if target.locked:
            raise ValueError("Esse jogador ja chamou Wellington e esta travado. Escolha outro alvo.")
        self._validate_slot(own, own_slot)
        self._validate_slot(target, target_slot)
        c1 = own.cards[own_slot]
        c2 = target.cards[target_slot]
        if c1 is None or c2 is None:
            raise ValueError("Nao pode trocar com slot vazio.")

        # Se o humano ja conhecia a carta que vai enviar, esse conhecimento acompanha a carta.
        human_knows_sent_card = player_idx == 0 and own_slot in self.players[0].known_slots

        own.cards[own_slot], target.cards[target_slot] = c2, c1

        if player_idx == 0:
            self.players[0].known_slots.discard(own_slot)
            if human_knows_sent_card:
                self.human_known_other[(target_idx, target_slot)] = c1.label()
            else:
                self._forget_human_knowledge(target_idx, target_slot)
        else:
            own.known_slots.discard(own_slot)
            self._forget_human_knowledge(player_idx, own_slot)
            if target_idx != 0:
                target.known_slots.discard(target_slot)
            self._forget_human_knowledge(target_idx, target_slot)
        self._log(f"Habilidade 7: troca cega realizada entre slot {own_slot} e jogador {target_idx} slot {target_slot}.")

    def _ability_8(self, player_idx: int, own_slot: int, target_idx: int, target_slot: int, do_swap: bool) -> None:
        if target_idx == player_idx:
            raise ValueError("Escolha outro jogador para habilidade 8.")
        own = self.players[player_idx]
        target = self.players[target_idx]
        if target.locked:
            raise ValueError("Esse jogador ja chamou Wellington e esta travado. Escolha outro alvo.")
        self._validate_slot(own, own_slot)
        self._validate_slot(target, target_slot)

        c1 = own.cards[own_slot]
        c2 = target.cards[target_slot]
        if c1 is None or c2 is None:
            raise ValueError("Nao pode usar habilidade 8 com slot vazio.")

        if player_idx == 0:
            self.players[0].known_slots.add(own_slot)
            self.human_known_other[(target_idx, target_slot)] = c2.label()
            self._log(
                f"Habilidade 8: voce viu {c1.label()} (seu slot {own_slot}) e {c2.label()} do jogador {target_idx} slot {target_slot}."
            )
        else:
            own.known_slots.add(own_slot)

        if do_swap:
            own.cards[own_slot], target.cards[target_slot] = c2, c1
            if player_idx == 0:
                # Continua conhecido: apos a troca, o jogador tambem viu c2.
                self.players[0].known_slots.add(own_slot)
                # Continua conhecido no alvo: apos a troca, o slot alvo passa a conter c1, que foi visto.
                self.human_known_other[(target_idx, target_slot)] = c1.label()
            else:
                own.known_slots.add(own_slot)
                if target_idx != 0:
                    target.known_slots.discard(target_slot)
                self._forget_human_knowledge(player_idx, own_slot)
            self._log("Habilidade 8: troca aplicada.")
        else:
            self._log("Habilidade 8: troca nao aplicada.")

    def _ability_8_preview(self, player_idx: int, own_slot: int, target_idx: int, target_slot: int) -> None:
        if target_idx == player_idx:
            raise ValueError("Escolha outro jogador para habilidade 8.")
        own = self.players[player_idx]
        target = self.players[target_idx]
        if target.locked:
            raise ValueError("Esse jogador ja chamou Wellington e esta travado. Escolha outro alvo.")
        self._validate_slot(own, own_slot)
        self._validate_slot(target, target_slot)
        c1 = own.cards[own_slot]
        c2 = target.cards[target_slot]
        if c1 is None or c2 is None:
            raise ValueError("Nao pode usar habilidade 8 com slot vazio.")

        self.pending_ability8_preview = {
            "own_slot": own_slot,
            "target_player": target_idx,
            "target_slot": target_slot,
            "own_label": c1.label(),
            "target_label": c2.label(),
        }
        # Uma vez vistas, mantemos visiveis ate a carta sair do slot.
        if player_idx == 0:
            self.players[0].known_slots.add(own_slot)
            self.human_known_other[(target_idx, target_slot)] = c2.label()
        self._log(
            f"Habilidade 8: cartas reveladas para decisao (seu slot {own_slot} e jogador {target_idx} slot {target_slot})."
        )

    def _resolve_bot_ability(self, player_idx: int, rank: str) -> None:
        player = self.players[player_idx]
        own_slots = [i for i, c in enumerate(player.cards) if c is not None]
        if not own_slots:
            return

        if rank == "5":
            unknown_own = [s for s in own_slots if s not in player.known_slots]
            slot = self.random.choice(unknown_own if unknown_own else own_slots)
            self._ability_5(player_idx, slot)
            self.last_bot_action = f"{player.name} jogou um 5 e revelou uma de suas cartas."
            return
        if rank == "6":
            candidates = [i for i in range(len(self.players)) if i != player_idx and not self.players[i].locked]
            if not candidates:
                return
            t = self.random.choice(candidates)
            t_slots = [i for i, c in enumerate(self.players[t].cards) if c is not None]
            if not t_slots:
                return
            slot = self.random.choice(t_slots)
            self._ability_6(player_idx, t, slot)
            target_name = "você" if t == 0 else self.players[t].name
            self.last_bot_action = f"{player.name} jogou um 6 e viu uma carta de {target_name}."
            self._log(f"{player.name} usou habilidade 6.")
            return
        if rank == "7":
            candidates = [i for i in range(len(self.players)) if i != player_idx and not self.players[i].locked]
            if not candidates:
                return
            t = self.random.choice(candidates)
            t_slots = [i for i, c in enumerate(self.players[t].cards) if c is not None]
            if not t_slots:
                return
            own_slot = self.random.choice(own_slots)
            target_slot = self.random.choice(t_slots)
            self._ability_7(player_idx, own_slot, t, target_slot)
            target_name = "você" if t == 0 else self.players[t].name
            self.last_bot_action = f"{player.name} jogou um 7 e trocou cartas com {target_name}."
            return
        if rank == "8":
            candidates = [i for i in range(len(self.players)) if i != player_idx and not self.players[i].locked]
            if not candidates:
                return
            t = self.random.choice(candidates)
            t_slots = [i for i, c in enumerate(self.players[t].cards) if c is not None]
            if not t_slots:
                return
            own_slot = self.random.choice(own_slots)
            target_slot = self.random.choice(t_slots)
            own_card = self.players[player_idx].cards[own_slot]
            target_card = self.players[t].cards[target_slot]
            do_swap = own_card is not None and target_card is not None and target_card.points < own_card.points
            self._ability_8(player_idx, own_slot, t, target_slot, do_swap)
            target_name = "você" if t == 0 else self.players[t].name
            action_text = "trocou cartas com" if do_swap else "comparou cartas com"
            self.last_bot_action = f"{player.name} jogou um 8 e {action_text} {target_name}."
            return

    # ---------- Cuts ----------

    def _top_discard(self) -> Optional[Card]:
        return self.discard_pile[-1] if self.discard_pile else None

    def _resolve_bot_cuts(self, discarder_idx: int) -> None:
        """Processa UM corte de bot por vez com visual state."""
        top = self._top_discard()
        if top is None:
            return

        # Se já tem uma ação de corte pendente, executar ela agora
        if self.pending_bot_cut_action:
            action = self.pending_bot_cut_action
            idx = action["player_idx"]
            slot = action["slot"]
            p = self.players[idx]
            card = p.cards[slot]
            
            # Executar o corte
            p.cards[slot] = None
            p.known_slots.discard(slot)
            self._forget_human_knowledge(idx, slot)
            self.discard_pile.append(card)
            self._log(f"{p.name} cortou com {card.label()} (slot {slot}).")
            
            # Limpar a ação pendente
            self.pending_bot_cut_action = None
            
            # Limpar o visual state
            if idx in self.bot_visual:
                self.bot_visual[idx] = {"clear_on": "next_bot_step"}
            
            # Verificar se há mais cortes possíveis
            self._check_and_queue_next_cut(discarder_idx)
            return
        
        # Verificar se há algum bot que pode cortar
        self._check_and_queue_next_cut(discarder_idx)

    def _check_and_queue_next_cut(self, discarder_idx: int) -> None:
        """Verifica se há bots que podem cortar e agenda o próximo."""
        top = self._top_discard()
        if top is None:
            return

        order = [discarder_idx] + [
            (discarder_idx + offset) % len(self.players)
            for offset in range(1, len(self.players))
        ]
        
        for idx in order:
            if idx == 0:
                continue
            p = self.players[idx]
            if p.locked:
                continue

            matching_known = [
                s for s, c in enumerate(p.cards)
                if c is not None and c.rank == top.rank and s in p.known_slots
            ]
            if not matching_known:
                continue
            if self.random.random() > 0.60:
                continue

            # Encontrou um bot que vai cortar - agendar a ação visual
            slot = self.random.choice(matching_known)
            card = p.cards[slot]
            
            self.pending_bot_cut_action = {
                "player_idx": idx,
                "slot": slot,
                "card_label": card.label()
            }
            
            # Definir bot_visual para mostrar "CORTOU" no slot
            self.bot_visual[idx] = {
                "mode": "cut",
                "slot": slot,
                "player_name": p.name,
                "clear_on": "after_cut"
            }
            
            return  # Processar apenas UM corte por vez

        # Ninguém mais pode cortar - limpar a janela de corte
        self.pending_bot_cut = False
        self.cut_window_opened_at = None
        self._process_pending_discard_flow()

    def _check_human_cut_opportunity(self, discarder_idx: int) -> bool:
        if self.players[0].locked:
            return False
        # Enquanto estiver com carta comprada e sem descartar, nao pode cortar.
        if self.current_player == 0 and self.drawn_card is not None:
            return False
        top = self._top_discard()
        if top is None:
            return False

        # Opcao 1: tentar corte com carta propria (inclusive chute)
        has_any_card = any(c is not None for c in self.players[0].cards)
        if has_any_card:
            return True

        return False

    def _human_cut_options(self) -> Dict[str, Any]:
        if not self._can_human_cut_now():
            return {"self_slots": [], "other_targets": []}

        self_slots = [i for i, c in enumerate(self.players[0].cards) if c is not None]
        other_targets: List[Dict[str, Any]] = []
        for p_idx, player in enumerate(self.players):
            if p_idx == 0:
                continue
            for slot, card in enumerate(player.cards):
                if card is None:
                    continue
                give_slots = [i for i, c in enumerate(self.players[0].cards) if c is not None]
                if give_slots:
                    other_targets.append(
                        {
                            "target_player": p_idx,
                            "target_slot": slot,
                            "give_slots": give_slots,
                        }
                    )

        return {"self_slots": self_slots, "other_targets": other_targets}

    # ---------- Bot turn ----------

    def _bot_turn(self, idx: int) -> None:
        p = self.players[idx]
        if p.locked:
            self._advance_turn()
            return

        if self.pending_bot_turn is not None:
            if not isinstance(self.pending_bot_turn, dict):
                self.pending_bot_turn = None
            elif int(self.pending_bot_turn.get("player", -1)) != idx:
                # Estado antigo inconsistente: descarta carta comprada pendente, se houver, e reseta.
                if self.drawn_card is not None:
                    self.discard_pile.append(self.drawn_card)
                    self.drawn_card = None
                self.pending_bot_turn = None

        if self.pending_bot_turn is not None and int(self.pending_bot_turn.get("player", -1)) == idx:
            plan = self.pending_bot_turn
            self.pending_bot_turn = None
            drawn = self.drawn_card
            if drawn is None:
                # Corrige estado quebrado sem derrubar a API.
                self._log(f"{p.name} retomou turno apos estado inconsistente.")
                return

            replace_slot = plan.get("replace_slot")
            if replace_slot is None:
                self.drawn_card = None
                self.discard_pile.append(drawn)
                self.bot_visual[idx] = {"side": "discarded", "slot_discarded": None, "clear_on": "next_turn"}
                self._log(f"{p.name} descartou a carta comprada.")
                self._on_discard(idx, drawn)
                return

            try:
                replace_slot = int(replace_slot)
            except (TypeError, ValueError):
                replace_slot = -1

            if replace_slot < 0 or replace_slot >= len(p.cards):
                self.drawn_card = None
                self.discard_pile.append(drawn)
                self.bot_visual[idx] = {"side": "discarded", "slot_discarded": None, "clear_on": "next_turn"}
                self._log(f"{p.name} descartou a carta comprada.")
                self._on_discard(idx, drawn)
                return

            old = p.cards[replace_slot]
            if old is None:
                self.drawn_card = None
                self.discard_pile.append(drawn)
                self.bot_visual[idx] = {"side": "discarded", "slot_discarded": None, "clear_on": "next_turn"}
                self._log(f"{p.name} descartou a carta comprada.")
                self._on_discard(idx, drawn)
                return

            p.cards[replace_slot] = drawn
            p.known_slots.add(replace_slot)
            self._forget_human_knowledge(idx, replace_slot)
            self.drawn_card = None
            self.discard_pile.append(old)
            self.bot_visual[idx] = {
                "side": "drawn",
                "slot_discarded": replace_slot,
                "clear_on": "next_draw",
            }
            self._log(f"{p.name} descartou a carta da mesa no slot {replace_slot}.")
            self._on_discard(idx, old)
            return

        self._clear_bot_visual_next_draw()
        drawn = self._draw_card()
        self.drawn_card = drawn
        self.bot_visual[idx] = {"side": "drawn", "slot_discarded": None, "clear_on": None}

        candidate_slots = [s for s, c in enumerate(p.cards) if c is not None]
        known_slots = [s for s in candidate_slots if s in p.known_slots]
        unknown_slots = [s for s in candidate_slots if s not in p.known_slots]
        replace_slot = None

        # Heuristica: bot decide com base no que conhece das proprias cartas.
        if known_slots:
            worst_known_slot = max(known_slots, key=lambda s: p.cards[s].points)
            worst_known_card = p.cards[worst_known_slot]
            if worst_known_card is not None and drawn.points < worst_known_card.points:
                replace_slot = worst_known_slot
            elif drawn.points <= 2 and unknown_slots:
                replace_slot = self.random.choice(unknown_slots)
        else:
            if unknown_slots and drawn.points <= 4:
                replace_slot = self.random.choice(unknown_slots)

        self.pending_bot_turn = {"player": idx, "replace_slot": replace_slot}
        if replace_slot is not None:
            self._log(f"{p.name} comprou uma carta e vai substituir slot {replace_slot}.")
        else:
            self._log(f"{p.name} comprou uma carta e vai descartá-la.")

    # ---------- Helpers ----------

    def _human_view_card(self, player_idx: int, slot: int, card: Optional[Card]) -> tuple[bool, str]:
        if card is None:
            return True, "--"
        if self.game_over:
            return True, card.label()

        if self.pending_ability8_preview is not None:
            preview = self.pending_ability8_preview
            if player_idx == 0 and slot == preview["own_slot"]:
                return True, preview["own_label"]
            if player_idx == preview["target_player"] and slot == preview["target_slot"]:
                return True, preview["target_label"]

        if player_idx == 0:
            if slot in self.players[0].known_slots:
                return True, card.label()
            return False, "??"

        known_label = self.human_known_other.get((player_idx, slot))
        if known_label is not None:
            return True, known_label
        return False, "??"

    def _validate_slot(self, player: PlayerState, slot: int) -> None:
        if slot < 0 or slot >= len(player.cards):
            raise ValueError("Slot invalido.")

    def _penalty_blind_draw(self, player_idx: int, n: int) -> None:
        p = self.players[player_idx]
        for _ in range(n):
            p.cards.append(self._draw_card())

    def _forget_human_knowledge(self, player_idx: int, slot: int) -> None:
        self.human_known_other.pop((player_idx, slot), None)

    def _scores_if_over(self) -> Optional[List[Dict[str, Any]]]:
        if not self.game_over:
            return None
        scores = []
        for i, p in enumerate(self.players):
            total = sum(c.points for c in p.cards if c is not None)
            scores.append({"player": i, "name": p.name, "score": total})
        scores.sort(key=lambda x: x["score"])
        return scores

    def _winner_ids_if_over(self) -> Optional[List[int]]:
        if not self.game_over:
            return None
        totals = [
            sum(c.points for c in p.cards if c is not None)
            for p in self.players
        ]
        if not totals:
            return []
        min_score = min(totals)
        candidates = [idx for idx, total in enumerate(totals) if total == min_score]
        if len(candidates) <= 1:
            return candidates

        # Regra: em empate com quem chamou Wellington, quem NAO chamou vence.
        caller = self.wellington_caller
        if caller is not None and caller in candidates:
            non_caller_candidates = [idx for idx in candidates if idx != caller]
            if non_caller_candidates:
                return non_caller_candidates
        return candidates

    def _can_human_draw(self) -> bool:
        return (
            not self.game_over
            and not self.paused
            and self.current_player == 0
            and not self.players[0].locked
            and self.drawn_card is None
            and self.pending_human_cut_other_transfer is None
            and self.pending_ability is None
            and not self.pending_human_wellington_window
        )

    def _can_human_discard_drawn(self) -> bool:
        return (
            not self.game_over
            and not self.paused
            and self.current_player == 0
            and not self.players[0].locked
            and self.drawn_card is not None
            and not self.pending_human_cut
            and self.pending_human_cut_other_transfer is None
            and self.pending_ability is None
            and not self.pending_human_wellington_window
        )

    def _human_replace_slots(self) -> List[int]:
        if not self._can_human_discard_drawn():
            return []
        return [i for i, c in enumerate(self.players[0].cards) if c is not None]

    def _can_human_call_wellington(self) -> bool:
        return (
            not self.game_over
            and not self.paused
            and self.current_player == 0
            and not self.players[0].locked
            and self.pending_human_cut_other_transfer is None
            and self.pending_human_wellington_window
            and self.wellington_caller is None
        )

    def _can_human_cut_now(self) -> bool:
        if self.game_over or self.paused or self.players[0].locked:
            return False
        if self.pending_human_cut_other_transfer is not None:
            return False
        if self.current_player == 0 and self.drawn_card is not None:
            return False
        if self.pending_human_cut:
            return self.pending_ability is None
        return (
            self.human_cut_available_until_draw
            and self.current_player == 0
            and self.drawn_card is None
            and self.pending_ability is None
        )

    def _sanitize_human_cut_state(self) -> None:
        if not self.players:
            return
        if self.players[0].locked:
            self.pending_human_cut = False
            self.pending_human_cut_other_transfer = None
            self.human_cut_available_until_draw = False

    def _human_send_cut_other_slots(self) -> List[int]:
        if self.pending_human_cut_other_transfer is None:
            return []
        return [i for i, c in enumerate(self.players[0].cards) if c is not None]

    def _clear_bot_visual_next_turn(self) -> None:
        to_clear = []
        for idx, visual in self.bot_visual.items():
            if visual.get("clear_on") == "next_turn":
                to_clear.append(idx)
        for idx in to_clear:
            self.bot_visual.pop(idx, None)

    def _clear_bot_visual_next_draw(self) -> None:
        to_clear = []
        for idx, visual in self.bot_visual.items():
            if visual.get("clear_on") == "next_draw":
                to_clear.append(idx)
        for idx in to_clear:
            self.bot_visual.pop(idx, None)

    def _log(self, message: str) -> None:
        self.log.append(message)


