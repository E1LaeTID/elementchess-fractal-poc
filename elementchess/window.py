from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from math import cos, pi, sin
import tkinter as tk
from enum import Enum

from .board import Board
from .balance import BalanceCombatCalculator
from .combat import CombatCalculator, CombatReport
from .combat_failures import CombatFailureTracker
from .domain import Cell, CellTransition, ChessCellState, Element, Orientation, TerrainOwner
from .events import GameEventType, OpeningEventSystem
from .glyphs import GlyphToken, chess_glyph, terrain_glyph
from .guide import GuideBook
from .layer_cycles import CycleAxis, CycleRecord, LayerCycleEngine, MobileLayer
from .projection import ChessPosition, ChessProjection
from .movement import DefensiveMoveTransaction, MoveTransaction, MovementEngine, PieceMove
from .sudoku import PlacementError, PlacementPhase, TokenPlacementController
from .sudoku_balance import CorrectionOperation, SudokuCorrectionEngine, SudokuRiskAnalyzer
from .simulation import SIMULATION_PAGES, load_simulation
from .time_engine import IncrementalTimeEngine, WHEEL_GAME, WHEEL_ICE
from .turn_cycle import RoundCycle


class WindowView(Enum):
    TERRAIN = "TERRAIN 17×17"
    CHESS = "BOARD MIXTE 17×17"
    TIME = "TEMPS INCRÉMENTAL"


ELEMENT_COLORS = {
    Element.NONE: "#252a30",
    Element.WATER: "#116b89",
    Element.FIRE: "#a93632",
    Element.WIND: "#3f8296",
    Element.WOOD: "#24754c",
    Element.EARTH: "#94752f",
    Element.ICE: "#b9dbe4",
    Element.MAGMAT: "#8e2947",
    Element.THUNDER: "#62429a",
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{component:02x}" for component in rgb)


def _mix_color(color: str, target: str, ratio: float) -> str:
    source_rgb = _hex_to_rgb(color)
    target_rgb = _hex_to_rgb(target)
    return _rgb_to_hex(tuple(
        round(source + (destination - source) * ratio)
        for source, destination in zip(source_rgb, target_rgb)
    ))


class ElementChessWindow:
    MIN_BOARD = 360
    MARGIN = 54

    def __init__(self, board: Board | None = None) -> None:
        self.board = board or Board()
        self.board.clear_demo()
        self.view = WindowView.CHESS
        self.selected_chess = ChessPosition(3, 3)
        self.guide = GuideBook()
        self.guide_visible = False
        self.simulation_visible = False
        self.simulation_index = 0
        self.simulation_mode = False
        self._game_session_snapshot: dict | None = None
        self._simulation_exit_popup: tk.Toplevel | None = None
        self.forced_orientation: Orientation | None = None
        self.orientation_effect: tuple[Element, tuple[tuple[int, int, int], ...]] | None = None
        self.time_engine = IncrementalTimeEngine()
        self.opening = OpeningEventSystem(self.board, self.time_engine)
        self.elements_hidden = True
        self.number_peek = False
        self.power_preview = False
        self.hover_canvas_position: tuple[float, float] | None = None
        self.hover_destination: tuple[int, int] | None = None
        self.balance_calculator = BalanceCombatCalculator()
        self.revealed_elements: set[Element] = set()
        self.opening_active = True
        self.opening_message = "PRÉPARATION DU PLATEAU"
        self.opening_cards: list[Element] = []
        self.visible_token_owners: set[TerrainOwner] = set()
        self.current_turn = 0
        self.round_cycle = RoundCycle()
        self.token_placement: TokenPlacementController | None = None
        self.token_hitboxes: dict[str, tuple[float, float, float, float]] = {}
        self.token_control_hitboxes: dict[str, tuple[float, float, float, float]] = {}
        self.token_scroll_offsets = {TerrainOwner.WHITE: 0, TerrainOwner.BLACK: 0}
        self.recycle_mode = False
        self.action_message = ""
        self.piece_turn_owner = "BLANC"
        self.selected_piece_position: tuple[int, int] | None = None
        self.legal_piece_moves: dict[tuple[int, int], PieceMove] = {}
        self.alt_selection_active = False
        self.defensive_pair_selection: list[tuple[int, int]] = []
        self.pending_orientation_position: tuple[int, int] | None = None
        self.pending_orientation_queue: list[tuple[int, int]] = []
        self.pending_move_transaction: MoveTransaction | DefensiveMoveTransaction | None = None
        self.pending_move_can_rollback = False
        self.orientation_confirming = False
        self.pending_attack: tuple[PieceMove, CombatReport] | None = None
        self.combat_notice: tuple[CombatReport, bool, tuple[int, int]] | None = None
        self.combat_failures = CombatFailureTracker()
        self.game_over_owner: str | None = None
        self._game_over_popup: tk.Toplevel | None = None
        self.orientation_hitboxes: dict[str, tuple[float, float, float, float]] = {}
        self.attack_hitboxes: dict[str, tuple[float, float, float, float]] = {}
        self.wheel_visual_positions = {
            identifier: float(state.position)
            for identifier, state in self.time_engine.states.items()
        }
        self.wheel_animating = False
        self.time_control_ids = self.time_engine.controllable_identifiers
        self.selected_time_id: str | None = None
        self.time_hitboxes: dict[str, tuple[float, float, float, float]] = {}
        self.rotation_hitboxes: dict[int, tuple[float, float, float, float]] = {}
        self.permutation_indicator: tuple[CycleRecord, int, int] | None = None
        self.sudoku_correction = SudokuCorrectionEngine(seed=426)
        self.blocked_zone_streaks = {f"Z{row}{column}": 0 for row in range(1, 4) for column in range(1, 4)}
        self.balance_checked_rounds: set[int] = set()
        self.combat_rejections: list[bool] = []
        self.combat_expected_rejections: list[float] = []

        self.root = tk.Tk()
        self.root.title("ElementChess — Console graphique")
        self.root.geometry("1100x850")
        self.root.minsize(620, 560)
        self.root.configure(bg="#11151a")

        self.title = tk.Label(
            self.root,
            text="",
            bg="#11151a",
            fg="#f1f4f7",
            font=("Consolas", 16, "bold"),
            anchor="w",
        )
        self.title.pack(fill="x", padx=20, pady=(14, 4))

        self.canvas = tk.Canvas(
            self.root,
            bg="#171c22",
            highlightthickness=0,
            takefocus=True,
        )
        self.canvas.pack(fill="both", expand=True, padx=20, pady=8)

        self.status = tk.Label(
            self.root,
            text="",
            bg="#11151a",
            fg="#cdd6df",
            font=("Consolas", 11),
            anchor="w",
            justify="left",
        )
        self.status.pack(fill="x", padx=20, pady=(4, 3))

        self.help = tk.Label(
            self.root,
            text="[1/T] terrain   [2/E] board   [Maj] numéros   [Ctrl] potentiel A/D   [Alt] roi + tour   [4/H] temps   [F1/G] notice   [F2/L] simulations   [F11] plein écran",
            bg="#0b0e12",
            fg="#8fa2b5",
            font=("Consolas", 10),
            anchor="w",
        )
        self.help.pack(fill="x", ipady=8, padx=20, pady=(0, 14))

        self._create_guide_overlay()
        self._create_simulation_overlay()

        self.canvas.bind("<Configure>", lambda _event: self.draw())
        self.root.bind("<Key>", self.on_key)
        self.root.bind("<KeyPress-Shift_L>", lambda _event: self._set_number_peek(True))
        self.root.bind("<KeyPress-Shift_R>", lambda _event: self._set_number_peek(True))
        self.root.bind("<KeyRelease-Shift_L>", lambda _event: self._set_number_peek(False))
        self.root.bind("<KeyRelease-Shift_R>", lambda _event: self._set_number_peek(False))
        self.root.bind("<KeyPress-Control_L>", lambda _event: self._set_power_preview(True))
        self.root.bind("<KeyPress-Control_R>", lambda _event: self._set_power_preview(True))
        self.root.bind("<KeyRelease-Control_L>", lambda _event: self._set_power_preview(False))
        self.root.bind("<KeyRelease-Control_R>", lambda _event: self._set_power_preview(False))
        self.root.bind("<KeyPress-Alt_L>", lambda _event: self._set_alt_selection(True))
        self.root.bind("<KeyPress-Alt_R>", lambda _event: self._set_alt_selection(True))
        self.root.bind("<KeyRelease-Alt_L>", lambda _event: self._set_alt_selection(False))
        self.root.bind("<KeyRelease-Alt_R>", lambda _event: self._set_alt_selection(False))
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Alt-Button-1>", self.on_alt_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.canvas.bind("<Leave>", self._clear_hover)
        self.canvas.focus_set()
        self.draw()
        self.root.after(450, self._opening_grid)

    def run(self) -> None:
        self.root.mainloop()

    def _set_number_peek(self, visible: bool) -> None:
        if self.number_peek == visible:
            return
        self.number_peek = visible
        if self.view is WindowView.CHESS:
            self.draw()

    def _set_power_preview(self, visible: bool) -> None:
        if self.power_preview == visible:
            return
        self.power_preview = visible
        if not visible:
            self.hover_destination = None
        elif self.hover_canvas_position is not None:
            self.hover_destination = self._legal_destination_at(*self.hover_canvas_position)
        self.draw()

    def _set_alt_selection(self, active: bool) -> None:
        self.alt_selection_active = active
        if active:
            self.action_message = (
                "ALT maintenu : sélectionnez le roi et la tour, dans l'ordre de votre choix"
            )
            self.draw()

    def on_motion(self, event: tk.Event) -> None:
        self.hover_canvas_position = (event.x, event.y)
        destination = self._legal_destination_at(event.x, event.y)
        if destination != self.hover_destination or (self.power_preview and destination is not None):
            self.hover_destination = destination
            if self.power_preview:
                self.draw()

    def _clear_hover(self, _event: tk.Event | None = None) -> None:
        self.hover_canvas_position = None
        if self.hover_destination is not None:
            self.hover_destination = None
            if self.power_preview:
                self.draw()

    def _legal_destination_at(self, x: float, y: float) -> tuple[int, int] | None:
        if self.view not in (WindowView.CHESS, WindowView.TERRAIN):
            return None
        left, top, size = self._layout()
        if not (left <= x < left + size and top <= y < top + size):
            return None
        cell_size = size / Board.SIZE
        coordinate = (int((x - left) / cell_size), int((y - top) / cell_size))
        return coordinate if coordinate in self.legal_piece_moves else None

    def on_key(self, event: tk.Event) -> None:
        key = event.keysym.lower()
        if key in ("f2", "l"):
            self.toggle_simulation()
            return
        if self.simulation_visible:
            if key == "escape":
                self.toggle_simulation(False)
            elif key in ("right", "pagedown"):
                self._simulation_move(1)
            elif key in ("left", "pageup"):
                self._simulation_move(-1)
            elif key in ("return", "space"):
                self._load_current_simulation()
            return
        if key in ("f1", "g"):
            self.toggle_guide()
            return
        if self.guide_visible:
            if key == "escape":
                self.toggle_guide(False)
            elif key in ("right", "pagedown", "space"):
                self._guide_next()
            elif key in ("left", "pageup", "backspace"):
                self._guide_previous()
            elif key == "home":
                self._guide_select(0)
            return
        if self.simulation_mode and key == "2":
            self._prompt_exit_simulation()
            return
        if self.opening_active:
            return
        if key in ("escape",):
            self.root.destroy()
            return
        if key == "f11":
            current = bool(self.root.attributes("-fullscreen"))
            self.root.attributes("-fullscreen", not current)
            return
        if key in ("1", "t"):
            self.view = WindowView.TERRAIN
        elif key in ("2", "e"):
            self.view = WindowView.CHESS
        elif key in ("4", "h"):
            self.view = WindowView.TIME
        elif key in ("left", "q"):
            self._move_selection(-1, 0)
        elif key in ("right", "d"):
            self._move_selection(1, 0)
        elif key in ("up", "z"):
            self._move_selection(0, -1)
        elif key in ("down", "s"):
            self._move_selection(0, 1)
        self.draw()

    def _rotate_selected_wheel(self, direction: int) -> None:
        if self.wheel_animating or self.selected_time_id is None:
            return
        source = self.selected_time_id
        steps = self.time_engine.rotate_manual(source, direction)
        starts = dict(self.wheel_visual_positions)
        self.wheel_animating = True
        self._animate_rotation(starts, steps, frame=0, frame_count=16)

    def _animate_rotation(self, starts, steps, frame: int, frame_count: int, on_complete=None) -> None:
        progress = frame / frame_count
        eased = 1 - (1 - progress) ** 3
        for step in steps:
            self.wheel_visual_positions[step.identifier] = starts[step.identifier] + step.delta_teeth * eased
        self.draw()
        if frame < frame_count:
            self.root.after(25, self._animate_rotation, starts, steps, frame + 1, frame_count, on_complete)
            return
        for identifier, state in self.time_engine.states.items():
            self.wheel_visual_positions[identifier] = float(state.position)
        self.wheel_animating = False
        self.draw()
        if on_complete:
            self.root.after(180, on_complete)

    def animate_permutation(
        self, record: CycleRecord, frame: int = 0, frame_count: int = 20,
        on_complete=None,
    ) -> None:
        """Annonce visuellement une permutation logique déjà appliquée."""
        self.permutation_indicator = (record, frame, frame_count)
        self.draw()
        if frame < frame_count:
            self.root.after(70, self.animate_permutation, record, frame + 1, frame_count, on_complete)
            return
        self.permutation_indicator = None
        self.draw()
        if on_complete:
            self.root.after(120, on_complete)

    def _create_guide_overlay(self) -> None:
        self.guide_frame = tk.Frame(
            self.root,
            bg="#111820",
            highlightbackground="#e4c95b",
            highlightthickness=2,
        )
        header = tk.Label(
            self.guide_frame,
            text="NOTICE ELEMENTCHESS",
            bg="#111820",
            fg="#ffffff",
            font=("Consolas", 18, "bold"),
            anchor="w",
        )
        header.pack(fill="x", padx=18, pady=(14, 8))

        content = tk.Frame(self.guide_frame, bg="#111820")
        content.pack(fill="both", expand=True, padx=16)

        self.guide_menu = tk.Listbox(
            content,
            width=35,
            bg="#17212b",
            fg="#dbe5ed",
            selectbackground="#745f1c",
            selectforeground="#ffffff",
            font=("Consolas", 10),
            activestyle="none",
            exportselection=False,
            highlightthickness=0,
        )
        self.guide_menu.pack(side="left", fill="y", padx=(0, 12))
        for page in self.guide.pages:
            self.guide_menu.insert("end", page.menu_label)
        self.guide_menu.bind("<<ListboxSelect>>", self._on_guide_menu_select)

        text_frame = tk.Frame(content, bg="#111820")
        text_frame.pack(side="left", fill="both", expand=True)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        self.guide_text = tk.Text(
            text_frame,
            wrap="word",
            bg="#f3f0e7",
            fg="#182028",
            insertbackground="#182028",
            font=("Segoe UI", 12),
            padx=24,
            pady=20,
            relief="flat",
            yscrollcommand=scrollbar.set,
        )
        self.guide_text.pack(side="left", fill="both", expand=True)
        scrollbar.configure(command=self.guide_text.yview)
        self.guide_text.tag_configure("title", font=("Segoe UI", 18, "bold"), spacing3=16)

        footer = tk.Frame(self.guide_frame, bg="#111820")
        footer.pack(fill="x", padx=16, pady=12)
        tk.Button(footer, text="◀ Page précédente", command=self._guide_previous).pack(side="left")
        tk.Button(footer, text="Page suivante ▶", command=self._guide_next).pack(side="left", padx=8)
        self.guide_counter = tk.Label(
            footer, text="", bg="#111820", fg="#9fb0bf", font=("Consolas", 10)
        )
        self.guide_counter.pack(side="left", padx=12)
        tk.Button(footer, text="Fermer [F1 / G / Échap]", command=lambda: self.toggle_guide(False)).pack(side="right")

    def toggle_guide(self, visible: bool | None = None) -> None:
        self.guide_visible = not self.guide_visible if visible is None else visible
        if self.guide_visible:
            self.guide_frame.place(relx=0.025, rely=0.055, relwidth=0.95, relheight=0.89)
            self.guide_frame.lift()
            self._render_guide_page()
            self.guide_menu.focus_set()
        else:
            self.guide_frame.place_forget()
            self.canvas.focus_set()

    def _render_guide_page(self) -> None:
        page = self.guide.current
        self.guide_text.configure(state="normal")
        self.guide_text.delete("1.0", "end")
        self.guide_text.insert("end", f"{page.chapter}. {page.title}\n", "title")
        self.guide_text.insert("end", page.body)
        self.guide_text.configure(state="disabled")
        self.guide_text.yview_moveto(0)
        self.guide_menu.selection_clear(0, "end")
        self.guide_menu.selection_set(self.guide.index)
        self.guide_menu.see(self.guide.index)
        self.guide_counter.configure(text=f"Page {self.guide.index + 1} / {len(self.guide.pages)}")

    def _on_guide_menu_select(self, _event: tk.Event) -> None:
        selection = self.guide_menu.curselection()
        if selection:
            self._guide_select(selection[0])

    def _guide_select(self, index: int) -> None:
        self.guide.select(index)
        self._render_guide_page()

    def _guide_next(self) -> None:
        self.guide.next()
        self._render_guide_page()

    def _guide_previous(self) -> None:
        self.guide.previous()
        self._render_guide_page()

    def _create_simulation_overlay(self) -> None:
        self.simulation_frame = tk.Frame(
            self.root, bg="#111820", highlightbackground="#54c7e8", highlightthickness=2,
        )
        tk.Label(
            self.simulation_frame, text="LIVRET DE SIMULATION",
            bg="#111820", fg="#ffffff", font=("Consolas", 20, "bold"),
        ).pack(pady=(24, 10))
        self.simulation_title = tk.Label(
            self.simulation_frame, bg="#111820", fg="#e4c95b",
            font=("Segoe UI", 18, "bold"), wraplength=720,
        )
        self.simulation_title.pack(padx=35, pady=8)
        self.simulation_objective = tk.Label(
            self.simulation_frame, bg="#17212b", fg="#ffffff",
            font=("Segoe UI", 13, "bold"), wraplength=760, justify="left", padx=22, pady=18,
        )
        self.simulation_objective.pack(fill="x", padx=35, pady=8)
        self.simulation_text = tk.Label(
            self.simulation_frame, bg="#111820", fg="#dbe5ed",
            font=("Segoe UI", 13), wraplength=760, justify="left",
        )
        self.simulation_text.pack(fill="x", padx=45, pady=18)
        footer = tk.Frame(self.simulation_frame, bg="#111820")
        footer.pack(side="bottom", fill="x", padx=28, pady=24)
        tk.Button(footer, text="◀ Précédent", command=lambda: self._simulation_move(-1)).pack(side="left")
        self.simulation_counter = tk.Label(
            footer, bg="#111820", fg="#9fb0bf", font=("Consolas", 11),
        )
        self.simulation_counter.pack(side="left", padx=18)
        tk.Button(footer, text="Suivant ▶", command=lambda: self._simulation_move(1)).pack(side="left")
        self.simulation_load = tk.Button(
            footer, text="CHARGER LA MISE EN SITUATION [Entrée]",
            bg="#745f1c", fg="#ffffff", command=self._load_current_simulation,
        )
        self.simulation_load.pack(side="right", padx=(8, 0))
        tk.Button(
            footer, text="Fermer [F2 / L / Échap]",
            command=lambda: self.toggle_simulation(False),
        ).pack(side="right")

    def toggle_simulation(self, visible: bool | None = None) -> None:
        self.simulation_visible = not self.simulation_visible if visible is None else visible
        if self.simulation_visible:
            self.toggle_guide(False)
            self.simulation_frame.place(relx=0.10, rely=0.10, relwidth=0.80, relheight=0.76)
            self.simulation_frame.lift()
            self._render_simulation_page()
        else:
            self.simulation_frame.place_forget()
            self.canvas.focus_set()

    def _simulation_move(self, delta: int) -> None:
        self.simulation_index = max(0, min(len(SIMULATION_PAGES) - 1, self.simulation_index + delta))
        self._render_simulation_page()

    def _render_simulation_page(self) -> None:
        page = SIMULATION_PAGES[self.simulation_index]
        self.simulation_title.configure(text=page.title)
        self.simulation_objective.configure(text=f"OBJECTIF\n{page.objective}")
        self.simulation_text.configure(text=page.instructions)
        self.simulation_counter.configure(
            text=f"Page {self.simulation_index + 1} / {len(SIMULATION_PAGES)}"
        )
        self.simulation_load.configure(
            state=("normal" if page.scenario else "disabled"),
            text=("CHARGER LA MISE EN SITUATION [Entrée]" if page.scenario else "CONSULTEZ LA NOTICE [F1 / G]"),
        )

    def _load_current_simulation(self) -> None:
        page = SIMULATION_PAGES[self.simulation_index]
        if page.scenario is None:
            return
        if self.opening_active and not self.simulation_mode:
            self.simulation_text.configure(
                text=(
                    "La partie termine actuellement un interstice animé. Attendez l'annonce du joueur "
                    "suivant avant de charger cette simulation afin de sauvegarder un état stable."
                )
            )
            return
        if not self.simulation_mode:
            self._game_session_snapshot = deepcopy({
                "board": self.board,
                "time_engine": self.time_engine,
                "opening": self.opening,
                "elements_hidden": self.elements_hidden,
                "revealed_elements": self.revealed_elements,
                "opening_active": self.opening_active,
                "opening_message": self.opening_message,
                "opening_cards": self.opening_cards,
                "visible_token_owners": self.visible_token_owners,
                "current_turn": self.current_turn,
                "round_cycle": self.round_cycle,
                "token_placement": self.token_placement,
                "token_scroll_offsets": self.token_scroll_offsets,
                "recycle_mode": self.recycle_mode,
                "action_message": self.action_message,
                "piece_turn_owner": self.piece_turn_owner,
                "selected_chess": self.selected_chess,
                "selected_piece_position": self.selected_piece_position,
                "legal_piece_moves": self.legal_piece_moves,
                "defensive_pair_selection": self.defensive_pair_selection,
                "pending_orientation_position": self.pending_orientation_position,
                "pending_orientation_queue": self.pending_orientation_queue,
                "pending_move_transaction": self.pending_move_transaction,
                "pending_move_can_rollback": self.pending_move_can_rollback,
                "orientation_confirming": self.orientation_confirming,
                "combat_notice": self.combat_notice,
                "combat_failures": self.combat_failures,
                "blocked_zone_streaks": self.blocked_zone_streaks,
                "balance_checked_rounds": self.balance_checked_rounds,
                "combat_rejections": self.combat_rejections,
                "combat_expected_rejections": self.combat_expected_rejections,
                "game_over_owner": self.game_over_owner,
                "wheel_visual_positions": self.wheel_visual_positions,
                "selected_time_id": self.selected_time_id,
                "view": self.view,
            })
        self.simulation_mode = True
        setup = load_simulation(self.board, page.scenario)
        self.time_engine = IncrementalTimeEngine()
        self.opening = OpeningEventSystem(self.board, self.time_engine, seed=8241)
        self.opening.player_tokens = setup.hands
        self.wheel_visual_positions = {
            identifier: float(state.position) for identifier, state in self.time_engine.states.items()
        }
        self.opening_active = False
        self.elements_hidden = True
        self.revealed_elements.clear()
        self.opening_cards.clear()
        self.visible_token_owners = {TerrainOwner.WHITE, TerrainOwner.BLACK}
        self.current_turn = 1
        self.round_cycle = RoundCycle(active_owner=setup.active_owner)
        self.piece_turn_owner = setup.active_owner.value
        self.token_placement = TokenPlacementController(
            self.board, self.opening.player_tokens, (setup.active_owner,)
        )
        if setup.phase == "pieces":
            self.token_placement.pass_tokens()
        self.pending_orientation_position = setup.orientation_position
        self.pending_orientation_queue = []
        self.pending_move_transaction = None
        self.pending_move_can_rollback = False
        self.forced_orientation = setup.forced_orientation
        self.orientation_effect = setup.orientation_effect
        self.orientation_confirming = False
        self.selected_piece_position = None
        self.defensive_pair_selection.clear()
        self.legal_piece_moves.clear()
        self.combat_notice = None
        self.combat_failures = CombatFailureTracker()
        self.combat_failures.failures[setup.active_owner.value] = setup.failure_count
        self.game_over_owner = None
        self.blocked_zone_streaks = {f"Z{row}{column}": 0 for row in range(1, 4) for column in range(1, 4)}
        self.balance_checked_rounds = set()
        self.combat_rejections = []
        self.combat_expected_rejections = []
        self.action_message = setup.message
        self.view = WindowView.CHESS
        self.toggle_simulation(False)
        self.draw()

    def _prompt_exit_simulation(self) -> None:
        if not self.simulation_mode:
            return
        if self._simulation_exit_popup is not None and self._simulation_exit_popup.winfo_exists():
            self._simulation_exit_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        self._simulation_exit_popup = popup
        popup.title("Quitter la simulation")
        popup.configure(bg="#111820")
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(False, False)
        tk.Label(
            popup, text="QUITTER LA SIMULATION ?", bg="#111820", fg="#ffffff",
            font=("Consolas", 16, "bold"), padx=30, pady=18,
        ).pack()
        tk.Label(
            popup,
            text="Votre partie normale est restée en pause et n'a pas été modifiée.",
            bg="#111820", fg="#cdd6df", font=("Segoe UI", 11), padx=30, pady=8,
        ).pack()
        buttons = tk.Frame(popup, bg="#111820")
        buttons.pack(padx=24, pady=22)
        tk.Button(
            buttons, text="REPRENDRE LA PARTIE", bg="#236348", fg="#ffffff",
            command=self._resume_saved_game, width=22,
        ).pack(side="left", padx=8)
        tk.Button(
            buttons, text="NOUVELLE PARTIE", bg="#745f1c", fg="#ffffff",
            command=self._start_new_game, width=20,
        ).pack(side="left", padx=8)
        tk.Button(
            buttons, text="RESTER EN SIMULATION", bg="#613741", fg="#ffffff",
            command=self._close_simulation_exit_popup, width=22,
        ).pack(side="left", padx=8)
        popup.protocol("WM_DELETE_WINDOW", self._close_simulation_exit_popup)
        popup.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - popup.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")

    def _close_simulation_exit_popup(self) -> None:
        if self._simulation_exit_popup is not None:
            self._simulation_exit_popup.grab_release()
            self._simulation_exit_popup.destroy()
            self._simulation_exit_popup = None
        self.canvas.focus_set()

    def _finish_game(self, winner: str, loser: str, reason: str) -> None:
        """Fige la partie et programme une annonce d'issue non ambiguë."""
        self.game_over_owner = loser
        self.action_message = (
            f"FIN DE PARTIE · {winner} A GAGNÉ · {loser} A PERDU · {reason}"
        )
        self.draw()
        self.root.after_idle(lambda: self._show_game_over_popup(winner, loser, reason))

    def _show_game_over_popup(self, winner: str, loser: str, reason: str) -> None:
        if self._game_over_popup is not None and self._game_over_popup.winfo_exists():
            self._game_over_popup.lift()
            return
        popup = tk.Toplevel(self.root)
        self._game_over_popup = popup
        popup.title("Fin de la partie")
        popup.configure(bg="#111820")
        popup.transient(self.root)
        popup.grab_set()
        popup.resizable(False, False)
        tk.Label(
            popup,
            text="FIN DE LA PARTIE",
            bg="#111820",
            fg="#f0d56b",
            font=("Consolas", 18, "bold"),
            padx=36,
            pady=16,
        ).pack()
        tk.Label(
            popup,
            text=f"{winner} A GAGNÉ\n{loser} A PERDU",
            bg="#111820",
            fg="#ffffff",
            font=("Consolas", 15, "bold"),
            justify="center",
            padx=36,
            pady=8,
        ).pack()
        tk.Label(
            popup,
            text=reason.capitalize(),
            bg="#111820",
            fg="#cdd6df",
            font=("Segoe UI", 11),
            padx=36,
            pady=10,
        ).pack()
        buttons = tk.Frame(popup, bg="#111820")
        buttons.pack(padx=24, pady=(4, 24))
        tk.Button(
            buttons,
            text="NOUVELLE PARTIE",
            bg="#236348",
            fg="#ffffff",
            command=self._start_new_game,
            width=20,
        ).pack(side="left", padx=8)
        tk.Button(
            buttons,
            text="QUITTER LE JEU",
            bg="#613741",
            fg="#ffffff",
            command=self.root.destroy,
            width=20,
        ).pack(side="left", padx=8)
        popup.protocol("WM_DELETE_WINDOW", self.root.destroy)
        popup.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - popup.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")

    def _close_game_over_popup(self) -> None:
        if self._game_over_popup is not None and self._game_over_popup.winfo_exists():
            self._game_over_popup.grab_release()
            self._game_over_popup.destroy()
        self._game_over_popup = None

    def _resume_saved_game(self) -> None:
        snapshot = self._game_session_snapshot
        self._close_simulation_exit_popup()
        if snapshot is None:
            return
        for name, value in snapshot.items():
            setattr(self, name, value)
        self.simulation_mode = False
        self._game_session_snapshot = None
        self.forced_orientation = None
        self.orientation_effect = None
        self.draw()

    def _start_new_game(self) -> None:
        self._close_simulation_exit_popup()
        self._close_game_over_popup()
        self.simulation_mode = False
        self._game_session_snapshot = None
        self.board = Board()
        self.time_engine = IncrementalTimeEngine()
        self.opening = OpeningEventSystem(self.board, self.time_engine)
        self.elements_hidden = True
        self.revealed_elements.clear()
        self.opening_cards.clear()
        self.visible_token_owners.clear()
        self.current_turn = 0
        self.round_cycle = RoundCycle()
        self.token_placement = None
        self.pending_orientation_position = None
        self.pending_orientation_queue = []
        self.pending_move_transaction = None
        self.pending_move_can_rollback = False
        self.forced_orientation = None
        self.orientation_effect = None
        self.combat_failures = CombatFailureTracker()
        self.game_over_owner = None
        self.sudoku_correction = SudokuCorrectionEngine(seed=426)
        self.blocked_zone_streaks = {f"Z{row}{column}": 0 for row in range(1, 4) for column in range(1, 4)}
        self.balance_checked_rounds = set()
        self.combat_rejections = []
        self.combat_expected_rejections = []
        self.defensive_pair_selection.clear()
        self.wheel_visual_positions = {
            identifier: float(state.position) for identifier, state in self.time_engine.states.items()
        }
        self.view = WindowView.CHESS
        self.opening_active = True
        self.opening_message = "PRÉPARATION DU PLATEAU"
        self.action_message = ""
        self.draw()
        self.root.after(50, self._opening_grid)

    def _move_selection(self, dx: int, dy: int) -> None:
        self.selected_chess = ChessPosition(
            max(0, min(7, self.selected_chess.file + dx)),
            max(0, min(7, self.selected_chess.rank + dy)),
        )

    def _layout(self) -> tuple[float, float, float]:
        available = min(
            max(self.canvas.winfo_width() - 340, self.MIN_BOARD),
            max(self.canvas.winfo_height() - 2 * self.MARGIN, self.MIN_BOARD),
        )
        left = (self.canvas.winfo_width() - available) / 2
        top = (self.canvas.winfo_height() - available) / 2
        return left, top, available

    def draw(self) -> None:
        self.canvas.delete("all")
        if self.current_turn == 0:
            turn_suffix = ""
        elif self.opening_active:
            turn_suffix = (
                f"   ·   INTERSTICE — RONDE {max(1, self.current_turn - 1)} TERMINÉE"
            )
        elif self.token_placement and self.token_placement.phase is not PlacementPhase.PIECES_PENDING:
            turn_suffix = (
                f"   ·   RONDE {self.current_turn}   ·   JETONS — "
                f"{self.token_placement.active_owner.value}"
            )
        elif self.token_placement:
            turn_suffix = (
                f"   ·   RONDE {self.current_turn}   ·   PIÈCES — {self.piece_turn_owner}"
            )
        else:
            turn_suffix = "   ·   TOUR 1 — BLANC"
        simulation_suffix = "   ·   MODE SIMULATION [2 POUR QUITTER]" if self.simulation_mode else ""
        self.title.configure(text=f"ELEMENTCHESS   ·   {self.view.value}{turn_suffix}{simulation_suffix}")
        if self.view is WindowView.TERRAIN:
            self._draw_terrain()
        elif self.view is WindowView.CHESS:
            self._draw_chess()
        else:
            self._draw_time()
        if self.opening_active:
            self._draw_opening_overlay()
        self._update_status()

    def _opening_grid(self) -> None:
        event = self.opening.display_grid()
        self.opening_message = event.message
        self.draw()
        self.root.after(650, self._opening_pieces)

    def _opening_pieces(self) -> None:
        event = self.opening.place_pieces()
        self.opening_message = event.message
        self.draw()
        self.root.after(650, self._opening_elements)

    def _opening_elements(self) -> None:
        event = self.opening.assign_elements()
        self.opening_message = event.message
        self.draw()
        self.root.after(700, self._opening_numbers)

    def _opening_numbers(self) -> None:
        event = self.opening.preposition_numbers()
        self.opening_message = event.message
        self.draw()
        self.root.after(700, self._opening_interstice)

    def _opening_interstice(self) -> None:
        events = self.opening.open_first_interstice()
        self._opening_events = list(events)
        self._advance_opening_event()

    def _advance_opening_event(self) -> None:
        if not self._opening_events:
            self.opening.apply_rotation_commands()
            for identifier, state in self.time_engine.states.items():
                self.wheel_visual_positions[identifier] = float(state.position)
            self.current_turn = 1
            self.opening_message = "TOUR 1 — BLANC"
            self.draw()
            self.root.after(1200, self._finish_opening)
            return
        event = self._opening_events.pop(0)
        self.opening_message = event.message
        if event.type is GameEventType.INTERSTICE_OPENED:
            self.opening_cards.clear()
            self.revealed_elements.clear()
        elif event.type is GameEventType.ELEMENT_DRAWN:
            self.opening_cards.append(event.element)
            self.revealed_elements.add(event.element)
        elif event.type is GameEventType.TOKENS_DISTRIBUTED:
            self.visible_token_owners.add(event.owner)
        self.draw()
        delay = 700 if event.type is GameEventType.ELEMENT_DRAWN else 420
        self.root.after(delay, self._advance_opening_event)

    def _finish_opening(self) -> None:
        self.opening_active = False
        self.revealed_elements.clear()
        self.opening_cards.clear()
        self.visible_token_owners = {TerrainOwner.WHITE, TerrainOwner.BLACK}
        self.token_placement = TokenPlacementController(
            self.board, self.opening.player_tokens, (TerrainOwner.WHITE,)
        )
        self.action_message = "BLANC : placez un jeton ou passez, puis déplacez une pièce"
        self.draw()

    def _draw_opening_overlay(self) -> None:
        width = max(self.canvas.winfo_width(), 1)
        height = max(self.canvas.winfo_height(), 1)
        panel_width = min(620, width * 0.72)
        panel_height = min(250, height * 0.38)
        x0 = (width - panel_width) / 2
        y0 = (height - panel_height) / 2
        self.canvas.create_rectangle(
            x0, y0, x0 + panel_width, y0 + panel_height,
            fill="#101820", outline="#f0d56b", width=3,
        )
        self.canvas.create_text(
            width / 2, y0 + 36,
            text=(
                "EFFET D'ORIENTATION" if self.simulation_mode else
                "OUVERTURE ELEMENTCHESS" if self.current_turn == 0 else
                "INTERSTICE ELEMENTCHESS"
            ),
            fill="#ffffff", font=("Consolas", 18, "bold"),
        )
        self.canvas.create_text(
            width / 2, y0 + 72, text=self.opening_message,
            fill="#f0d56b", font=("Segoe UI", 13, "bold"),
        )
        card_width = 118
        gap = 16
        total = 3 * card_width + 2 * gap
        start = width / 2 - total / 2
        for index in range(3):
            left = start + index * (card_width + gap)
            element = self.opening_cards[index] if index < len(self.opening_cards) else None
            fill = ELEMENT_COLORS[element] if element else "#27313a"
            self.canvas.create_rectangle(
                left, y0 + 105, left + card_width, y0 + 205,
                fill=fill, outline="#dbe7ef", width=2,
            )
            self.canvas.create_text(
                left + card_width / 2, y0 + 155,
                text=element.label.upper() if element else "?",
                fill="#ffffff", font=("Consolas", 12, "bold"),
            )

    def _draw_time(self) -> None:
        width = max(self.canvas.winfo_width(), 760)
        height = max(self.canvas.winfo_height(), 520)
        cx, cy = width * 0.5, height * 0.44
        earth_radius = min(width * 0.28, height * 0.38)
        earth_inner_radius = earth_radius * (800 / 1200)
        main_radius = earth_radius * 0.34
        small_radius = earth_radius * 0.105
        first_distance = main_radius + small_radius
        second_distance = first_distance + 2 * small_radius
        rack_height = max(24, earth_radius * 0.12)
        rack_y = cy + earth_radius + rack_height / 2

        centers = {
            "wheel_game": (cx, cy),
            "wheel_fire": (cx - first_distance, cy),
            "wheel_wind": (cx, cy - first_distance),
            "wheel_magmat": (cx, cy - second_distance),
            "wheel_wood": (cx + first_distance, cy),
            "wheel_thunder": (cx + second_distance, cy),
            "wheel_water": (cx, cy + first_distance),
            "wheel_earth": (cx, cy),
            "wheel_ice": (cx, rack_y),
        }

        self.time_hitboxes.clear()
        self.rotation_hitboxes.clear()
        self.control_anchors: dict[str, tuple[float, float, float]] = {}
        self.earth_hit_region = (cx, cy, earth_inner_radius, earth_radius)

        self._draw_earth_ring(
            cx,
            cy,
            earth_inner_radius,
            earth_radius,
            self.time_engine.states["wheel_earth"],
            self.selected_time_id == "wheel_earth",
        )

        for identifier in (
            "wheel_game", "wheel_fire", "wheel_wind", "wheel_magmat",
            "wheel_wood", "wheel_thunder", "wheel_water",
        ):
            state = self.time_engine.states[identifier]
            wheel_cx, wheel_cy = centers[identifier]
            radius = main_radius if identifier == WHEEL_GAME else small_radius
            selected = identifier == self.selected_time_id
            self._draw_wheel(wheel_cx, wheel_cy, radius, state, selected)
            if identifier != WHEEL_GAME:
                self.time_hitboxes[identifier] = (
                    wheel_cx - radius, wheel_cy - radius,
                    wheel_cx + radius, wheel_cy + radius,
                )
                self.control_anchors[identifier] = (wheel_cx, wheel_cy, radius)

        rack_width = earth_radius * 1.75
        self._draw_ice_rack(
            cx,
            rack_y,
            rack_width,
            self.time_engine.states[WHEEL_ICE],
            self.selected_time_id == WHEEL_ICE,
            rack_height,
        )
        self.time_hitboxes[WHEEL_ICE] = (
            cx - rack_width / 2, rack_y - rack_height / 2,
            cx + rack_width / 2, rack_y + rack_height / 2,
        )
        self.control_anchors[WHEEL_ICE] = (cx, rack_y, rack_height)
        self.control_anchors["wheel_earth"] = (cx - earth_radius * 0.80, cy, small_radius)

        if self.selected_time_id is not None:
            anchor = self.control_anchors[self.selected_time_id]
            self._draw_rotation_overlay(*anchor)

        self.canvas.create_text(
            18,
            16,
            anchor="nw",
            text="Cliquer un élément pour afficher ses commandes · une flèche = un incrément",
            fill="#c7d2dc",
            font=("Consolas", 10, "bold"),
        )

    def _draw_wheel(self, cx, cy, radius, state, selected: bool) -> None:
        identifier = state.spec.identifier
        fill = "#33414d" if identifier == WHEEL_GAME else "#24303a"
        outline = "#ffd15c" if selected else "#8ba1b2"
        self.canvas.create_oval(
            cx - radius, cy - radius, cx + radius, cy + radius,
            fill=fill, outline=outline, width=3 if selected else 2,
        )
        visual_position = self.wheel_visual_positions[identifier]
        angle = visual_position * (state.spec.tooth_angle or 0)
        marker_x = cx + cos(angle) * radius * 0.82
        marker_y = cy + sin(angle) * radius * 0.82
        self.canvas.create_line(cx, cy, marker_x, marker_y, fill="#ffd15c", width=4)
        for index in range(8):
            tooth_angle = angle + index * pi / 4
            inner = radius * 0.88
            self.canvas.create_line(
                cx + cos(tooth_angle) * inner,
                cy + sin(tooth_angle) * inner,
                cx + cos(tooth_angle) * radius,
                cy + sin(tooth_angle) * radius,
                fill="#b9c7d2",
                width=2,
            )
        position = state.position
        if identifier == WHEEL_GAME:
            self.canvas.create_text(
                cx, cy - radius * 0.10, text="ROUE\nPRINCIPALE", justify="center",
                fill="#ffffff", font=("Segoe UI", max(10, int(radius * 0.14)), "bold"),
            )
            self.canvas.create_text(
                cx, cy + radius * 0.40, text=f"{position}/{state.spec.tooth_count}",
                fill="#f2d66b", font=("Consolas", max(8, int(radius * 0.12)), "bold"),
            )
        else:
            label_size = max(7, int(radius * 0.25))
            self.canvas.create_text(cx, cy - 6, text=state.spec.label, fill="#ffffff", font=("Segoe UI", label_size, "bold"))
            self.canvas.create_text(
                cx, cy + 11, text=f"{position}/{state.spec.tooth_count}",
                fill="#b7c5d0", font=("Consolas", max(6, int(radius * 0.18))),
            )
        if identifier == WHEEL_GAME:
            self.canvas.create_text(cx, cy + radius + 13, text="sans commande", fill="#7f93a4", font=("Consolas", 8))

    def _draw_earth_ring(self, cx, cy, inner_radius, outer_radius, state, selected: bool) -> None:
        outline = "#ffd15c" if selected else "#7392a7"
        self.canvas.create_oval(
            cx - outer_radius, cy - outer_radius,
            cx + outer_radius, cy + outer_radius,
            fill="#6b5730", outline=outline, width=4 if selected else 3,
        )
        self.canvas.create_oval(
            cx - inner_radius, cy - inner_radius,
            cx + inner_radius, cy + inner_radius,
            fill="#171c22", outline=outline, width=3,
        )
        angle = self.wheel_visual_positions[state.spec.identifier] * (state.spec.tooth_angle or 0)
        for index in range(24):
            tooth_angle = angle + index * 2 * pi / 24
            for radius, direction in ((outer_radius, -1), (inner_radius, 1)):
                tooth_depth = max(5, outer_radius * 0.025)
                self.canvas.create_line(
                    cx + cos(tooth_angle) * radius,
                    cy + sin(tooth_angle) * radius,
                    cx + cos(tooth_angle) * (radius + direction * tooth_depth),
                    cy + sin(tooth_angle) * (radius + direction * tooth_depth),
                    fill="#e0c875",
                    width=2,
                )
        self.canvas.create_text(
            cx - outer_radius * 0.78,
            cy - outer_radius * 0.34,
            text=f"Terre\n{state.position}/96",
            fill="#fff2bd",
            font=("Consolas", max(7, int(outer_radius * 0.045)), "bold"),
            justify="center",
        )

    def _draw_ice_rack(self, cx, cy, rack_width, state, selected: bool, height: float = 30) -> None:
        offset = (self.wheel_visual_positions[WHEEL_ICE] % 8) * 11
        outline = "#ffd15c" if selected else "#8ba1b2"
        self.canvas.create_rectangle(
            cx - rack_width / 2, cy - height / 2,
            cx + rack_width / 2, cy + height / 2,
            fill="#d8edf2", outline=outline, width=3 if selected else 2,
        )
        start = cx - rack_width / 2 - offset
        x = start
        while x < cx + rack_width / 2:
            self.canvas.create_line(x, cy - height / 2, x + 6, cy - height / 2 - 8, fill="#8ba1b2", width=2)
            x += 11
        self.canvas.create_text(cx, cy, text=f"Glace · position {state.position:+d}", fill="#14202a", font=("Segoe UI", 10, "bold"))

    def _draw_rotation_overlay(self, cx: float, cy: float, radius: float) -> None:
        button_radius = max(18, min(25, radius * 0.55))
        gap = radius + button_radius + 6
        for direction, x, symbol, fill, color in (
            (-1, cx - gap, "↺", "#20374a", "#69d5ff"),
            (1, cx + gap, "↻", "#4a3520", "#ffd15c"),
        ):
            self.canvas.create_oval(
                x - button_radius, cy - button_radius,
                x + button_radius, cy + button_radius,
                fill=fill, outline="#f1f5f8", width=2,
            )
            self.canvas.create_text(
                x, cy, text=symbol, fill=color,
                font=("Segoe UI Symbol", max(16, int(button_radius * 1.05)), "bold"),
            )
            self.rotation_hitboxes[direction] = (
                x - button_radius, cy - button_radius,
                x + button_radius, cy + button_radius,
            )

    def _draw_terrain(self) -> None:
        left, top, size = self._layout()
        cell = size / Board.SIZE

        for y, row in enumerate(self.board.rows()):
            for x, board_cell in enumerate(row):
                x0, y0 = left + x * cell, top + y * cell
                color = self._environment_color(x, y)
                self.canvas.create_rectangle(
                    x0, y0, x0 + cell, y0 + cell,
                    fill=color,
                    outline="#38434e",
                    width=max(1, size // 850),
                )
                self._draw_cell_glyph(
                    x0, y0, cell,
                    self._terrain_glyph_for_cell(board_cell),
                )
                if board_cell.transition is not CellTransition.STABLE:
                    self.canvas.create_text(
                        x0 + cell / 2,
                        y0 + cell / 2,
                        text=board_cell.transition.symbol,
                        fill="#ffffff",
                        font=("Consolas", max(7, int(cell * 0.33)), "bold"),
                    )

        # Les traits épais ne délimitent que les parcelles, jamais les cases de pièces.
        self._draw_zone_capture_overlays(left, top, cell)
        for start_x in (1, 6, 11):
            for start_y in (1, 6, 11):
                x0, y0 = left + start_x * cell, top + start_y * cell
                self.canvas.create_rectangle(
                    x0, y0, x0 + 5 * cell, y0 + 5 * cell,
                    outline="#dbe5ee",
                    width=max(2, int(size / 300)),
                )

        self._draw_circumference_frame(left, top, cell)

        self._draw_axis(left, top, size, Board.SIZE, "terrain")
        self._draw_player_hands(left, top, size)
        self._draw_terrain_move_preview(left, top, cell)
        self._draw_hover_forecast()
        self._draw_permutation_indicator(left, top, size)

    def _draw_chess(self) -> None:
        left, top, size = self._layout()
        cell_size = size / Board.SIZE
        path_cells = {
            coordinate
            for move in self.legal_piece_moves.values()
            for coordinate in move.path
        }
        destinations = set(self.legal_piece_moves)

        # Première couche : support de jeu. Les halos de capture sont posés
        # au-dessus du terrain, mais avant les nombres et les pièces.
        for y, row in enumerate(self.board.rows()):
            for x, board_cell in enumerate(row):
                x0, y0 = left + x * cell_size, top + y * cell_size
                color = self._environment_color(x, y)
                self.canvas.create_rectangle(
                    x0, y0, x0 + cell_size, y0 + cell_size,
                    fill=color, outline="#394550", width=1,
                )

        self._draw_zone_capture_overlays(left, top, cell_size)

        # Deuxième couche : déplacements, informations et pièces. Le halo ne
        # peut donc plus teinter ni masquer les glyphes des pièces.
        for y, row in enumerate(self.board.rows()):
            for x, board_cell in enumerate(row):
                x0, y0 = left + x * cell_size, top + y * cell_size

                if (x, y) in path_cells:
                    self.canvas.create_rectangle(
                        x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
                        fill="#00a878", stipple="gray50", outline="#65f2c4", width=2,
                    )
                if (x, y) in destinations:
                    self.canvas.create_rectangle(
                        x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
                        fill="#1687e8", stipple="gray50", outline="#75c7ff", width=3,
                    )

                if board_cell.is_chess_cell:
                    self.canvas.create_rectangle(
                        x0 + 1,
                        y0 + 1,
                        x0 + cell_size - 1,
                        y0 + cell_size - 1,
                        outline="#91a3b3",
                        width=max(1, int(cell_size * 0.045)),
                    )

                self._draw_cell_glyph(
                    x0,
                    y0,
                    cell_size,
                    self._terrain_glyph_for_cell(board_cell, include_number=self.number_peek),
                )

                if board_cell.is_chess_cell and board_cell.piece:
                    self._draw_cell_glyph(
                        x0,
                        y0,
                        cell_size,
                        chess_glyph(board_cell.piece),
                    )

        self._draw_zone_frames(left, top, cell_size)
        self._draw_circumference_frame(left, top, cell_size)

        # La sélection encadre exactement la cellule jouable impair/impair.
        anchor_x, anchor_y = ChessProjection.terrain_anchor(self.selected_chess)
        x0 = left + anchor_x * cell_size
        y0 = top + anchor_y * cell_size
        self.canvas.create_rectangle(
            x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
            outline="#ffec57", width=max(2, int(size / 280)),
        )
        for selected_x, selected_y in self.defensive_pair_selection:
            sx0 = left + selected_x * cell_size
            sy0 = top + selected_y * cell_size
            self.canvas.create_rectangle(
                sx0 + 2, sy0 + 2, sx0 + cell_size - 2, sy0 + cell_size - 2,
                outline="#d889ff", width=max(3, int(cell_size * 0.1)),
            )
        self._draw_axis(left, top, size, Board.SIZE, "board")
        self._draw_player_hands(left, top, size)
        self._draw_piece_action_overlay(left, top, cell_size)
        self._draw_hover_forecast()
        self._draw_permutation_indicator(left, top, size)

    def _draw_permutation_indicator(self, left: float, top: float, size: float) -> None:
        if self.permutation_indicator is None:
            return
        record, frame, frame_count = self.permutation_indicator
        if frame % 2:
            return
        progress = min(1.0, frame / max(1, frame_count))
        cell = size / Board.SIZE
        if record.global_scope:
            start_x = start_y = 0
            span = Board.SIZE
            line_index = record.index or 0
        else:
            start_x, start_y = LayerCycleEngine._origin(record.zone_id)
            span = Board.ZONE_SIZE
            line_index = record.index or 0
        if record.axis is CycleAxis.ROW:
            logical = progress if record.direction > 0 else 1.0 - progress
            cx = left + (start_x + logical * (span - 1) + 0.5) * cell
            cy = top + (start_y + line_index + 0.5) * cell
        elif record.axis is CycleAxis.COLUMN:
            logical = progress if record.direction > 0 else 1.0 - progress
            cx = left + (start_x + line_index + 0.5) * cell
            cy = top + (start_y + logical * (span - 1) + 0.5) * cell
        else:
            cx = left + (start_x + span / 2) * cell
            cy = top + (start_y + span / 2) * cell
        color = "#f4d35e" if record.indicator_badge == "99" else "#68dcff"
        self.canvas.create_text(
            cx, cy - cell * 0.48, text=record.indicator_badge,
            fill=color, font=("Consolas", max(9, int(cell * 0.38)), "bold"),
        )
        self.canvas.create_text(
            cx, cy, text=record.indicator_arrow,
            fill=color, font=("Segoe UI Symbol", max(18, int(cell * 0.8)), "bold"),
        )

    def _draw_terrain_move_preview(self, left: float, top: float, cell_size: float) -> None:
        if self.selected_piece_position is None or not self.legal_piece_moves:
            return
        path_cells = {
            coordinate
            for move in self.legal_piece_moves.values()
            for coordinate in move.path
        }
        for x, y in path_cells:
            x0, y0 = left + x * cell_size, top + y * cell_size
            self.canvas.create_rectangle(
                x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
                fill="#00a878", stipple="gray50", outline="#65f2c4", width=2,
            )
        for x, y in self.legal_piece_moves:
            x0, y0 = left + x * cell_size, top + y * cell_size
            self.canvas.create_rectangle(
                x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
                fill="#1687e8", stipple="gray50", outline="#75c7ff", width=3,
            )

    def _draw_hover_forecast(self) -> None:
        if (
            not self.power_preview
            or self.hover_destination is None
            or self.hover_canvas_position is None
        ):
            return
        move = self.legal_piece_moves.get(self.hover_destination)
        if move is None:
            return
        forecast = self.balance_calculator.estimate_move(self.board, move)
        left, top, size = self._layout()
        cell_size = size / Board.SIZE
        x, y = self.hover_destination
        x0, y0 = left + x * cell_size, top + y * cell_size
        self.canvas.create_rectangle(
            x0 + 1, y0 + 1, x0 + cell_size - 1, y0 + cell_size - 1,
            outline="#ffec57", width=max(3, int(cell_size * 0.12)),
        )
        box_width = max(170, cell_size * 4.4)
        box_height = 62
        cursor_x, cursor_y = self.hover_canvas_position
        canvas_width = max(1, self.canvas.winfo_width())
        canvas_height = max(1, self.canvas.winfo_height())
        bx = min(cursor_x + 18, canvas_width - box_width - 8)
        by = min(cursor_y + 18, canvas_height - box_height - 8)
        bx = max(8, bx)
        by = max(8, by)
        self.canvas.create_rectangle(
            bx, by, bx + box_width, by + box_height,
            fill="#101820", outline="#ffec57", width=2,
        )
        self.canvas.create_text(
            bx + box_width / 2, by + box_height / 2,
            text=(
                f"{self.board.cell(x, y).coordinate} · POTENTIEL\n"
                f"ATTAQUE  {forecast.attack.minimum}–{forecast.attack.maximum}\n"
                f"DÉFENSE  {forecast.defense.minimum}–{forecast.defense.maximum}"
            ),
            fill="#f5f7f9", font=("Consolas", 8, "bold"), justify="center",
        )

    def _draw_piece_action_overlay(self, left: float, top: float, cell_size: float) -> None:
        self.orientation_hitboxes.clear()
        self.attack_hitboxes.clear()
        checked_kings = MovementEngine.checked_kings(self.board)
        for owner, (king_x, king_y) in checked_kings.items():
            x0 = left + king_x * cell_size
            y0 = top + king_y * cell_size
            self.canvas.create_rectangle(
                x0 + 2, y0 + 2, x0 + cell_size - 2, y0 + cell_size - 2,
                outline="#ff4d5e", width=max(3, int(cell_size * 0.1)),
            )
            self.canvas.create_text(
                x0 + cell_size / 2, y0 - 9,
                text=f"ÉCHEC {owner}", fill="#ff7a86", font=("Consolas", 8, "bold"),
            )
        if self.combat_notice:
            report, success, anchor = self.combat_notice
            board_size = cell_size * Board.SIZE
            cx = left - 130 if anchor[0] >= Board.SIZE // 2 else left + board_size + 130
            cy = top + board_size / 2
            panel_width = 240
            panel_height = 150
            x0, y0 = cx - panel_width / 2, cy - panel_height / 2
            self.canvas.create_rectangle(
                x0, y0, x0 + panel_width, y0 + panel_height,
                fill="#101820", outline="#62e2a6" if success else "#ff7373", width=3,
            )
            self.canvas.create_text(
                cx, y0 + 22,
                text="CAPTURE RÉUSSIE" if success else "ATTAQUE REPOUSSÉE",
                fill="#ffffff", font=("Consolas", 11, "bold"),
            )
            self.canvas.create_text(
                cx, y0 + 54,
                text=(
                    f"ATTAQUE {report.attack.total}  /  DÉFENSE {report.defense.total}\n\n"
                    f"Chance calculée : capture {report.attack_win_probability:.0%} · "
                    f"rejet {report.defense_win_probability:.0%}"
                ),
                fill="#b9c9d5", font=("Consolas", 8), justify="center",
            )

        if self.pending_orientation_position is None:
            return
        x, y = self.pending_orientation_position
        cx = left + (x + 0.5) * cell_size
        cy = top + (y + 0.5) * cell_size
        radius = max(20, cell_size * 0.55)
        horizontal_gap = max(72, cell_size * 2.45)
        vertical_gap = max(82, cell_size * 2.7)
        # Le halo utilise la pièce réelle comme centre : aucune copie n'est dessinée.
        self.canvas.create_oval(
            cx - cell_size * 0.72, cy - cell_size * 0.72,
            cx + cell_size * 0.72, cy + cell_size * 0.72,
            outline="#f0d56b", width=3,
        )
        if not self.orientation_confirming:
            for key, offset, symbol in (
                ("left", -horizontal_gap, "↺"),
                ("right", horizontal_gap, "↻"),
            ):
                bx = cx + offset
                self.canvas.create_oval(
                    bx - radius, cy - radius, bx + radius, cy + radius,
                    fill="#20374a", outline="#73d8ff", width=2,
                )
                self.canvas.create_text(bx, cy, text=symbol, fill="#ffffff", font=("Segoe UI Symbol", 15, "bold"))
                self.orientation_hitboxes[key] = (bx - radius, cy - radius, bx + radius, cy + radius)
            lock_y = cy + vertical_gap
            self.canvas.create_rectangle(
                cx - 65, lock_y - 16, cx + 65, lock_y + 16,
                fill="#6b5423", outline="#f1d35e", width=2,
            )
            self.canvas.create_text(cx, lock_y, text="VERROUILLER", fill="#ffffff", font=("Consolas", 8, "bold"))
            self.orientation_hitboxes["lock"] = (cx - 65, lock_y - 16, cx + 65, lock_y + 16)
        else:
            for key, offset, label, fill in (
                ("confirm", -76, "CONFIRMER", "#276847"),
                ("cancel", 76, "RETOUR", "#68333a"),
            ):
                bx0, by0 = cx + offset - 58, cy + vertical_gap
                bx1, by1 = cx + offset + 58, cy + vertical_gap + 36
                self.canvas.create_rectangle(bx0, by0, bx1, by1, fill=fill, outline="#ffffff", width=2)
                self.canvas.create_text(cx + offset, (by0 + by1) / 2, text=label, fill="#ffffff", font=("Consolas", 8, "bold"))
                self.orientation_hitboxes[key] = (bx0, by0, bx1, by1)

    def _draw_player_hands(self, left: float, top: float, size: float) -> None:
        self._draw_failure_gauges(left, top, size)
        hands = self.opening.player_tokens
        if not any(hands.values()):
            return
        self.token_hitboxes.clear()
        self.token_control_hitboxes.clear()
        token_radius = max(15, min(24, size / 24))
        gap = token_radius * 2.65
        band_width = token_radius * 4.20
        visible_count = 4
        band_height = gap * visible_count + 148
        # Réserve une zone respirante sous la jauge des attaques repoussées.
        center_y = top + size * 0.61
        for owner, center_x, band_fill, text_fill, accent in (
            (TerrainOwner.BLACK, left - band_width * 0.70, "#111820", "#f2f6f8", "#5edcff"),
            (TerrainOwner.WHITE, left + size + band_width * 0.70, "#eee9dc", "#182028", "#f2d66b"),
        ):
            tokens = hands[owner] if owner in self.visible_token_owners else ()
            if self.token_placement:
                tokens = self.token_placement.remaining(owner)
            if not tokens:
                continue
            maximum_offset = max(0, len(tokens) - visible_count)
            offset = min(self.token_scroll_offsets[owner], maximum_offset)
            self.token_scroll_offsets[owner] = offset
            visible_tokens = tokens[offset:offset + visible_count]
            y0 = center_y - band_height / 2
            self.canvas.create_rectangle(
                center_x - band_width / 2, y0,
                center_x + band_width / 2, y0 + band_height,
                fill=band_fill, outline=accent, width=3,
            )
            self.canvas.create_text(
                center_x, y0 + 26, text=f"{owner.value}\n{len(tokens)} / 21",
                fill=text_fill, font=("Consolas", max(9, int(token_radius * 0.48)), "bold"),
                justify="center",
            )
            if maximum_offset:
                for key, symbol, button_y in (("up", "▲", y0 + 45), ("down", "▼", y0 + band_height - 96)):
                    self.canvas.create_text(center_x, button_y, text=symbol, fill=accent, font=("Consolas", 11, "bold"))
                    self.token_control_hitboxes[f"scroll:{owner.value}:{key}"] = (
                        center_x - 20, button_y - 11, center_x + 20, button_y + 11
                    )
            for index, token in enumerate(visible_tokens):
                cy = y0 + 78 + index * gap
                selected = bool(
                    self.token_placement
                    and self.token_placement.selected_token_id == token.identifier
                )
                self.canvas.create_oval(
                    center_x - token_radius, cy - token_radius,
                    center_x + token_radius, cy + token_radius,
                    fill="#d6aa35",
                    outline="#fff06a" if selected else "#8f5bb7",
                    width=6 if selected else 4,
                )
                self.canvas.create_text(
                    center_x, cy, text=str(token.value),
                    fill="#22172a", font=("Consolas", max(10, int(token_radius * 0.80)), "bold"),
                )
                self.token_hitboxes[token.identifier] = (
                    center_x - token_radius, cy - token_radius,
                    center_x + token_radius, cy + token_radius,
                )
            if (
                self.token_placement
                and self.token_placement.phase is not PlacementPhase.PIECES_PENDING
                and self.token_placement.active_owner is owner
            ):
                recycle_y = y0 + band_height - 57
                self.canvas.create_rectangle(
                    center_x - band_width * 0.48, recycle_y - 13,
                    center_x + band_width * 0.48, recycle_y + 13,
                    fill="#4d3861", outline=accent, width=2,
                )
                self.canvas.create_text(
                    center_x, recycle_y, text="RECYCLER", fill=text_fill,
                    font=("Consolas", 7, "bold"),
                )
                self.token_control_hitboxes["recycle"] = (
                    center_x - band_width * 0.48, recycle_y - 13,
                    center_x + band_width * 0.48, recycle_y + 13,
                )
                pass_y = y0 + band_height - 21
                self.canvas.create_rectangle(
                    center_x - band_width * 0.48, pass_y - 13,
                    center_x + band_width * 0.48, pass_y + 13,
                    fill="#33414d", outline=accent, width=2,
                )
                self.canvas.create_text(
                    center_x, pass_y, text="PASSER", fill=text_fill,
                    font=("Consolas", 8, "bold"),
                )
                self.token_control_hitboxes["pass"] = (
                    center_x - band_width * 0.48, pass_y - 13,
                    center_x + band_width * 0.48, pass_y + 13,
                )

    def _draw_failure_gauges(self, left: float, top: float, size: float) -> None:
        for owner, owner_name, center_x, accent in (
            (TerrainOwner.BLACK, "NOIR", left - 92, "#5edcff"),
            (TerrainOwner.WHITE, "BLANC", left + size + 92, "#f2d66b"),
        ):
            value = self.combat_failures.failures[owner.value]
            y = top + 20
            self.canvas.create_text(
                center_x, y, text=f"ÉCHECS D'ATTAQUE · {owner_name} · {value}/3",
                fill=accent, font=("Consolas", 7, "bold"),
            )
            for index in range(3):
                x = center_x - 25 + index * 25
                self.canvas.create_oval(
                    x - 8, y + 12, x + 8, y + 28,
                    fill="#d94f5c" if index < value else "#26323c",
                    outline=accent, width=2,
                )

    def _draw_cell_glyph(
        self,
        x0: float,
        y0: float,
        cell_size: float,
        tokens: tuple[GlyphToken, ...],
    ) -> None:
        slot = cell_size / 5
        for token in tokens:
            px = x0 + (token.column + 0.5) * slot
            py = y0 + (token.row + 0.5) * slot
            if token.role == "piece_white":
                color = "#fffdf2"
                outline = "#182028"
                font = ("Segoe UI Symbol", max(9, int(cell_size * 0.52)), "bold")
            elif token.role == "piece_black":
                color = "#111820"
                outline = "#eef5fa"
                font = ("Segoe UI Symbol", max(9, int(cell_size * 0.52)), "bold")
            elif token.role == "orientation_white":
                color = "#ffe34f"
                outline = "#182028"
                font = ("Segoe UI Symbol", max(7, int(cell_size * 0.28)), "bold")
            elif token.role == "orientation_black":
                color = "#59ddff"
                outline = "#101820"
                font = ("Segoe UI Symbol", max(7, int(cell_size * 0.28)), "bold")
            elif token.role.startswith("number_center_"):
                role_parts = token.role.split("_")
                element_name = role_parts[2]
                owner_name = role_parts[3] if len(role_parts) > 3 else "neutral"
                element = Element[element_name.upper()]
                base = ELEMENT_COLORS[element]
                color = _mix_color(base, "#ffffff", 0.38)
                outline = {
                    "white": "#f3cf55",
                    "black": "#55d8ff",
                }.get(owner_name, _mix_color(base, "#000000", 0.52))
                font = ("Consolas", max(10, int(cell_size * 0.55)), "bold")
            elif token.role == "placed_number":
                color = "#e1b53d"
                outline = "#6f3d91"
                font = ("Consolas", max(7, int(cell_size * 0.23)), "bold")
            elif token.role == "placed_number_white":
                color = "#fff7c7"
                outline = "#9b6a13"
                font = ("Consolas", max(7, int(cell_size * 0.23)), "bold")
            elif token.role == "placed_number_black":
                color = "#66ddff"
                outline = "#07141d"
                font = ("Consolas", max(7, int(cell_size * 0.23)), "bold")
            elif token.role == "element_corner":
                color = "#e7f0f6"
                outline = "#172029"
                font = ("Segoe UI Symbol", max(6, int(cell_size * 0.20)), "bold")
            else:
                color = "#d8e4ec"
                outline = "#182028"
                font = ("Segoe UI Symbol", max(7, int(cell_size * 0.25)), "bold")
            self._draw_outlined_text(px, py, token.text, color, outline, font)

    def _draw_outlined_text(
        self,
        x: float,
        y: float,
        text: str,
        fill: str,
        outline: str,
        font: tuple[str, int, str],
    ) -> None:
        radius = 1
        for dx, dy in ((-radius, 0), (radius, 0), (0, -radius), (0, radius)):
            self.canvas.create_text(x + dx, y + dy, text=text, fill=outline, font=font)
        self.canvas.create_text(x, y, text=text, fill=fill, font=font)

    def _draw_zone_frames(self, left: float, top: float, cell_size: float) -> None:
        for start_x in (1, 6, 11):
            for start_y in (1, 6, 11):
                x0, y0 = left + start_x * cell_size, top + start_y * cell_size
                self.canvas.create_rectangle(
                    x0, y0, x0 + 5 * cell_size, y0 + 5 * cell_size,
                    outline="#f2f5f8", width=max(2, int(cell_size * 0.09)),
                )

    def _draw_zone_capture_overlays(self, left: float, top: float, cell_size: float) -> None:
        for zone_row, start_y in enumerate((1, 6, 11), start=1):
            for zone_col, start_x in enumerate((1, 6, 11), start=1):
                owner = self.board.zone_owner(f"Z{zone_row}{zone_col}")
                if owner is TerrainOwner.NONE:
                    continue
                x0, y0 = left + start_x * cell_size, top + start_y * cell_size
                fill = "#fff0a8" if owner is TerrainOwner.WHITE else "#087ca5"
                outline = "#fff07a" if owner is TerrainOwner.WHITE else "#61dcff"
                self.canvas.create_rectangle(
                    x0, y0, x0 + 5 * cell_size, y0 + 5 * cell_size,
                    fill=fill, stipple="gray12", outline=outline,
                    width=max(2, int(cell_size * 0.08)),
                )

    def _draw_circumference_frame(self, left: float, top: float, cell_size: float) -> None:
        total = Board.SIZE * cell_size
        self.canvas.create_rectangle(
            left, top, left + total, top + total,
            outline="#f7fafc", width=max(2, int(cell_size * 0.10)),
        )
        self.canvas.create_rectangle(
            left + cell_size,
            top + cell_size,
            left + total - cell_size,
            top + total - cell_size,
            outline="#d7e1e9",
            width=max(2, int(cell_size * 0.08)),
        )
        corner = cell_size
        for x, y in (
            (left, top),
            (left + total - corner, top),
            (left, top + total - corner),
            (left + total - corner, top + total - corner),
        ):
            self.canvas.create_rectangle(
                x, y, x + corner, y + corner,
                outline="#ffe574", width=max(2, int(cell_size * 0.10)),
            )

    def _environment_color(self, x: int, y: int) -> str:
        cell = self.board.cell(x, y)
        if cell.terrain is not Element.NONE and self._element_is_visible(cell.terrain):
            return ELEMENT_COLORS[cell.terrain]
        return "#10151a" if cell.is_border else ELEMENT_COLORS[Element.NONE]

    def _element_is_visible(self, element: Element) -> bool:
        return (
            self.view is WindowView.TERRAIN
            or self.number_peek
            or not self.elements_hidden
            or element in self.revealed_elements
        )

    def _terrain_glyph_for_cell(self, cell: Cell, include_number: bool = True):
        if cell.is_chess_cell:
            return ()
        if cell.terrain is Element.NONE:
            return terrain_glyph(Element.NONE, cell.terrain_number if include_number else None)
        tokens = terrain_glyph(cell.terrain, cell.terrain_number if include_number else None)
        owner_role = {
            TerrainOwner.NONE: "neutral",
            TerrainOwner.WHITE: "white",
            TerrainOwner.BLACK: "black",
        }[cell.terrain_owner]
        return tuple(
            GlyphToken(token.column, token.row, token.text, f"{token.role}_{owner_role}")
            if token.role.startswith("number_center_") else token
            for token in tokens
        )

    def _draw_axis(self, left: float, top: float, size: float, count: int, _kind: str) -> None:
        cell = size / count
        font_size = max(7, int(cell * 0.28))
        for index in range(count):
            self.canvas.create_text(
                left + (index + 0.5) * cell, top - 14,
                text=chr(65 + index), fill="#8fa2b5", font=("Consolas", font_size),
            )
            self.canvas.create_text(
                left - 18, top + (index + 0.5) * cell,
                text=str(index + 1), fill="#8fa2b5", font=("Consolas", font_size),
            )

    def _draw_chess_axis(self, left: float, top: float, size: float, terrain_cell: float) -> None:
        font_size = max(9, int(terrain_cell * 0.42))
        for index in range(8):
            anchor = index * 2 + 1
            center = (anchor + 0.5) * terrain_cell
            self.canvas.create_text(
                left + center, top - 16,
                text=chr(65 + index), fill="#c8d2dc", font=("Consolas", font_size, "bold"),
            )
            self.canvas.create_text(
                left - 20, top + center,
                text=str(index + 1), fill="#c8d2dc", font=("Consolas", font_size, "bold"),
            )

    def _update_status(self) -> None:
        if self.view is WindowView.TIME:
            selected = self.selected_time_id
            if selected is None:
                self.status.configure(
                    text=(
                        "Commande manuelle : cliquez sur un élément, puis utilisez la flèche ↺ ou ↻ affichée "
                        "en surimpression.\nChaque activation vaut exactement un incrément."
                    )
                )
                return
            selected_state = self.time_engine.states[selected]
            wave = self.time_engine.last_wave
            if wave:
                clockwise = sum(1 for step in wave if step.delta_teeth > 0)
                counterclockwise = sum(1 for step in wave if step.delta_teeth < 0)
                transmission = f"dernière vague : {len(wave)} composants · ↻ {clockwise} · ↺ {counterclockwise}"
            else:
                transmission = "aucune impulsion transmise"
            self.status.configure(
                text=(
                    f"Commande : {selected_state.spec.label} · position {selected_state.position:+d} dent(s) · "
                    f"pas commun 25π\n{transmission} · roue principale sans commande manuelle"
                )
            )
            return
        tx, ty = ChessProjection.terrain_anchor(self.selected_chess)
        cell = self.board.cell(tx, ty)
        if cell.terrain is Element.NONE:
            element_label = "aucun — case réservée à l'échiquier"
        elif self._element_is_visible(cell.terrain):
            element_label = cell.terrain.label
        else:
            element_label = "face cachée"
        piece = "aucune"
        if cell.piece:
            piece = (
                f"{cell.piece.identifier} · orientation {cell.piece.orientation.code} · "
                f"affinité {cell.piece.affinity.label}"
            )
        move = (
            self.legal_piece_moves.get(self.hover_destination)
            if self.power_preview and self.hover_destination is not None
            else None
        )
        if move is not None:
            forecast = self.balance_calculator.estimate_move(self.board, move)
            estimate_label = (
                f"Ctrl + survol {self.board.cell(*move.destination).coordinate} · "
                f"ATTAQUE {forecast.attack.minimum}–{forecast.attack.maximum} · "
                f"DÉFENSE {forecast.defense.minimum}–{forecast.defense.maximum} · "
                f"{forecast.attack.adjacent_elements} voisin(s) élémentaire(s), "
                f"{forecast.attack.uncertain_elements} état(s) variable(s)"
            )
        elif self.selected_piece_position is None:
            estimate_label = (
                "Prévision inactive : sélectionnez d'abord une pièce pour afficher ses destinations légales."
            )
        else:
            estimate_label = (
                "Maintenez Ctrl et survolez une destination bleue pour afficher "
                "les potentiels min–max d'attaque et de défense."
            )
        self.status.configure(
            text=(
                f"Position {self.selected_chess.coordinate} → terrain {cell.coordinate} · "
                f"zone {cell.zone_id or 'bordure'} · élément {element_label} · "
            f"valeur {cell.terrain_number or '—'}\n"
                f"Terrain : {cell.terrain_state.value} · échiquier : {cell.chess_state.value} · "
                f"pièce : {piece} · transition : {cell.transition.label}"
                f"\n{estimate_label}"
                + (f"\n{self.action_message}" if self.action_message else "")
            )
        )

    def on_click(self, event: tk.Event) -> None:
        if self.opening_active:
            return
        if self.game_over_owner:
            return
        if self.view is WindowView.TIME:
            self._on_time_click(event.x, event.y)
            return
        if self.view is WindowView.TERRAIN:
            self._select_nearest_chess_cell(event.x, event.y)
            return
        if self.view is not WindowView.CHESS:
            return
        if self.view is WindowView.CHESS:
            for action, bounds in self.attack_hitboxes.items():
                if self._point_in_bounds(event.x, event.y, bounds):
                    self._handle_attack_action(action)
                    return
            for action, bounds in self.orientation_hitboxes.items():
                if self._point_in_bounds(event.x, event.y, bounds):
                    self._handle_orientation_action(action)
                    return
        if self.token_placement and self.token_placement.phase is not PlacementPhase.PIECES_PENDING:
            for action, bounds in self.token_control_hitboxes.items():
                if not self._point_in_bounds(event.x, event.y, bounds):
                    continue
                if action == "pass":
                    self.recycle_mode = False
                    owner = self.token_placement.pass_tokens()
                    self.action_message = (
                        f"{owner.value} conserve ses jetons · sélectionnez maintenant une pièce"
                    )
                elif action == "recycle":
                    self.recycle_mode = True
                    self.action_message = (
                        "RECYCLAGE TOTAL : cliquez la parcelle dont tous vos jetons seront repris"
                    )
                elif action.startswith("scroll:"):
                    _, owner_value, direction = action.split(":")
                    owner = TerrainOwner(owner_value)
                    delta = -1 if direction == "up" else 1
                    maximum = max(0, len(self.token_placement.remaining(owner)) - 5)
                    self.token_scroll_offsets[owner] = max(
                        0, min(maximum, self.token_scroll_offsets[owner] + delta)
                    )
                self.draw()
                return
            for token_id, bounds in self.token_hitboxes.items():
                x0, y0, x1, y1 = bounds
                if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                    try:
                        token = self.token_placement.select(token_id)
                        self.action_message = (
                            f"Jeton {token.value} sélectionné — choisissez une cellule terrain"
                        )
                    except PlacementError as error:
                        self.action_message = str(error)
                    self.draw()
                    return

            left, top, size = self._layout()
            if left <= event.x < left + size and top <= event.y < top + size:
                cell_size = size / Board.SIZE
                x = int((event.x - left) / cell_size)
                y = int((event.y - top) / cell_size)
                try:
                    if self.recycle_mode:
                        recycled = self.token_placement.recycle_zone_at(x, y)
                        self.recycle_mode = False
                        self.action_message = (
                            f"{recycled.zone_id} recyclée en totalité : "
                            f"{recycled.returned}/{recycled.removed} jeton(s) récupéré(s)"
                        )
                        if recycled.discarded:
                            self.action_message += f" · {recycled.discarded} perdu(s), réserve limitée à 21"
                    else:
                        result = self.token_placement.place_selected(x, y)
                        suffix = " · parcelle complétée" if result.zone_complete else ""
                        if result.captured_owner is not TerrainOwner.NONE:
                            suffix += f" · CAPTURÉE PAR {result.captured_owner.value}"
                        self.action_message = (
                            f"Jeton {result.token.value} placé en {result.coordinate}{suffix}"
                        )
                        if self.token_placement.phase is PlacementPhase.PIECES_PENDING:
                            self.action_message += " · sélectionnez maintenant une pièce"
                        winner = self.board.terrain_winner()
                        if winner is not TerrainOwner.NONE:
                            loser = (
                                TerrainOwner.BLACK.value
                                if winner is TerrainOwner.WHITE
                                else TerrainOwner.WHITE.value
                            )
                            self._finish_game(
                                winner.value,
                                loser,
                                "trois terrains capturés et alignés",
                            )
                except PlacementError as error:
                    self.action_message = f"Placement refusé : {error}"
                self.draw()
                return
        if (
            self.view is WindowView.CHESS
            and self.token_placement
            and self.token_placement.phase is PlacementPhase.PIECES_PENDING
        ):
            left, top, size = self._layout()
            if left <= event.x < left + size and top <= event.y < top + size:
                cell_size = size / Board.SIZE
                x = int((event.x - left) / cell_size)
                y = int((event.y - top) / cell_size)
                self._select_or_move_piece(x, y)
                return
        self._select_nearest_chess_cell(event.x, event.y)

    def on_alt_click(self, event: tk.Event) -> None:
        """Garantit la sélection combinée même si le système absorbe Alt."""
        self.alt_selection_active = True
        self.on_click(event)

    def _select_nearest_chess_cell(self, x: float, y: float) -> None:
        left, top, size = self._layout()
        terrain_cell = size / Board.SIZE
        nearest_file = round(((x - left) / terrain_cell - 1.5) / 2)
        nearest_rank = round(((y - top) / terrain_cell - 1.5) / 2)
        if 0 <= nearest_file < 8 and 0 <= nearest_rank < 8:
            self.selected_chess = ChessPosition(nearest_file, nearest_rank)
            self.draw()

    @staticmethod
    def _point_in_bounds(x: float, y: float, bounds: tuple[float, float, float, float]) -> bool:
        x0, y0, x1, y1 = bounds
        return x0 <= x <= x1 and y0 <= y <= y1

    def _select_or_move_piece(self, x: int, y: int) -> None:
        if self.pending_orientation_position is not None:
            return
        if self.alt_selection_active:
            self._select_defensive_pair_piece(x, y)
            return
        move = self.legal_piece_moves.get((x, y))
        if move:
            if move.is_attack:
                report = CombatCalculator.calculate(self.board, move)
                attack_succeeds = self.opening.rng.random() < report.attack_win_probability
                self.combat_rejections.append(not attack_succeeds)
                self.combat_expected_rejections.append(report.defense_win_probability)
                self.combat_rejections = self.combat_rejections[-8:]
                self.combat_expected_rejections = self.combat_expected_rejections[-8:]
                if attack_succeeds:
                    self._show_combat_notice(report, True, move.destination)
                    self._execute_piece_move(move, allow_rollback=False)
                    self.action_message = "Capture réussie · choisissez l'orientation"
                    self.draw()
                else:
                    attacker = self.board.cell(*move.start).piece
                    if attacker is None:
                        return
                    self.combat_failures.record_failure(attacker.owner)
                    self._show_combat_notice(report, False, move.destination)
                    if self._finish_failed_defense_if_checked(attacker.owner):
                        return
                    fallback = MovementEngine.failed_attack_destination(self.board, move)
                    if fallback == move.start:
                        self.pending_orientation_position = move.start
                        self.selected_piece_position = None
                        self.legal_piece_moves.clear()
                    else:
                        self._execute_piece_move(
                            PieceMove(move.start, fallback, ()), allow_rollback=False
                        )
                    if self.combat_failures.defeated(attacker.owner):
                        self.pending_orientation_position = None
                        winner = (
                            TerrainOwner.BLACK.value
                            if attacker.owner == TerrainOwner.WHITE.value
                            else TerrainOwner.WHITE.value
                        )
                        self._finish_game(
                            winner,
                            attacker.owner,
                            "trois attaques repoussées",
                        )
                    else:
                        self.action_message = (
                            "Attaque repoussée · pièce arrêtée au plus près · choisissez l'orientation"
                        )
                    self.draw()
                return
            self._execute_piece_move(move)
            return

        cell = self.board.cell(x, y)
        if cell.piece and cell.piece.owner == self.piece_turn_owner:
            self.selected_piece_position = (x, y)
            self.legal_piece_moves = {
                candidate.destination: candidate
                for candidate in MovementEngine.legal_moves(self.board, x, y)
            }
            self.selected_chess = ChessPosition((x - 1) // 2, (y - 1) // 2)
            self.action_message = (
                f"{cell.piece.identifier} sélectionnée · {len(self.legal_piece_moves)} destination(s)"
            )
        else:
            self.selected_piece_position = None
            self.legal_piece_moves.clear()
            self.action_message = f"Sélectionnez une pièce {self.piece_turn_owner}"
        self.draw()

    def _finish_failed_defense_if_checked(self, attacker_owner: str) -> bool:
        """Termine la partie si l'assaut devait obligatoirement lever l'échec.

        Une capture proposée par le moteur est légale parce qu'elle supprimerait
        la menace. Si le combat la repousse, cette suppression n'a jamais lieu :
        le roi reste en échec et le tour ne peut pas être transmis.
        """
        if attacker_owner not in MovementEngine.checked_kings(self.board):
            return False
        winner = (
            TerrainOwner.BLACK.value
            if attacker_owner == TerrainOwner.WHITE.value
            else TerrainOwner.WHITE.value
        )
        self.pending_orientation_position = None
        self.pending_orientation_queue.clear()
        self.pending_move_transaction = None
        self.pending_move_can_rollback = False
        self.selected_piece_position = None
        self.legal_piece_moves.clear()
        self._finish_game(
            winner,
            attacker_owner,
            "attaque défensive repoussée : roi toujours en échec",
        )
        return True

    def _select_defensive_pair_piece(self, x: int, y: int) -> None:
        coordinate = (x, y)
        cell = self.board.cell(x, y)
        if coordinate in self.defensive_pair_selection:
            self.defensive_pair_selection.remove(coordinate)
            self.action_message = "Sélection défensive retirée"
            self.draw()
            return
        if (
            cell.piece is None
            or cell.piece.owner != self.piece_turn_owner
            or not cell.piece.identifier.endswith(("-king", "-rook"))
        ):
            self.action_message = "ALT : choisissez uniquement votre roi ou votre tour"
            self.draw()
            return
        self.defensive_pair_selection.append(coordinate)
        if len(self.defensive_pair_selection) == 1:
            self.selected_piece_position = None
            self.legal_piece_moves.clear()
            self.action_message = (
                f"{cell.piece.identifier} sélectionnée · maintenez ALT et choisissez l'autre pièce"
            )
            self.draw()
            return
        first, second = self.defensive_pair_selection[:2]
        try:
            king_start, rook_start, king_destination, rook_destination = (
                MovementEngine.defensive_pair_geometry(self.board, first, second)
            )
        except ValueError as error:
            self.defensive_pair_selection = [first]
            self.action_message = f"Déplacement défensif refusé : {error}"
            self.draw()
            return
        self.pending_move_transaction = DefensiveMoveTransaction.apply(
            self.board, king_start, rook_start, king_destination, rook_destination
        )
        self.pending_move_can_rollback = True
        self.pending_orientation_position = rook_destination
        self.pending_orientation_queue = [king_destination]
        self.orientation_confirming = False
        self.defensive_pair_selection.clear()
        self.selected_piece_position = None
        self.legal_piece_moves.clear()
        self.action_message = (
            "Déplacement défensif effectué · orientez d'abord la tour, puis le roi"
        )
        self.draw()

    def _execute_piece_move(self, move: PieceMove, *, allow_rollback: bool = True) -> None:
        if self.board.cell(*move.start).piece is None:
            return
        self.pending_move_transaction = MoveTransaction.apply(self.board, move)
        self.pending_move_can_rollback = allow_rollback
        self.pending_orientation_position = move.destination
        self.orientation_confirming = False
        self.selected_piece_position = None
        self.legal_piece_moves.clear()
        checked = MovementEngine.checked_kings(self.board)
        check_suffix = ""
        if checked:
            owners = " ET ".join(checked)
            check_suffix = f" · ROI {owners} EN ÉCHEC"
        self.action_message = (
            "Déplacement effectué · choisissez l'orientation puis verrouillez-la"
            f"{check_suffix}"
        )
        self.draw()

    def _show_combat_notice(
        self,
        report: CombatReport,
        success: bool,
        anchor: tuple[int, int],
    ) -> None:
        notice = (report, success, anchor)
        self.combat_notice = notice
        self.root.after(1900, self._clear_combat_notice, notice)

    def _clear_combat_notice(self, notice) -> None:
        if self.combat_notice == notice:
            self.combat_notice = None
            self.draw()

    def _handle_orientation_action(self, action: str) -> None:
        if self.pending_orientation_position is None:
            return
        cell = self.board.cell(*self.pending_orientation_position)
        if cell.piece is None:
            return
        if action in ("left", "right"):
            direction = -1 if action == "left" else 1
            orientations = list(Orientation)
            orientation = orientations[(cell.piece.orientation.step + direction) % len(orientations)]
            cell.piece = replace(cell.piece, orientation=orientation)
            self.action_message = f"Orientation provisoire : {orientation.code}"
        elif action == "lock":
            if self.forced_orientation is not None and cell.piece.orientation is not self.forced_orientation:
                self.action_message = (
                    f"Cette simulation impose l'orientation {self.forced_orientation.code} "
                    f"{self.forced_orientation.arrow}"
                )
                self.draw()
                return
            self.orientation_confirming = True
            self.action_message = f"Confirmer le verrouillage en {cell.piece.orientation.code} ?"
        elif action == "cancel":
            if self.pending_move_transaction is not None and self.pending_move_can_rollback:
                origin = self.pending_move_transaction.move.start
                self.pending_move_transaction.rollback(self.board)
                self.pending_move_transaction = None
                self.pending_move_can_rollback = False
                self.pending_orientation_position = None
                self.pending_orientation_queue.clear()
                self.orientation_confirming = False
                self.selected_piece_position = origin
                self.legal_piece_moves = {
                    move.destination: move
                    for move in MovementEngine.legal_moves(self.board, *origin)
                }
                self.action_message = "Déplacement annulé · pièce restaurée sur sa case initiale"
            else:
                self.orientation_confirming = False
                self.action_message = "Verrouillage annulé · ajustez l'orientation"
        elif action == "confirm":
            cell.piece = replace(cell.piece, orientation_locked=True)
            self.action_message = f"Orientation {cell.piece.orientation.code} verrouillée"
            if self.pending_orientation_queue:
                self.pending_orientation_position = self.pending_orientation_queue.pop(0)
                self.orientation_confirming = False
                next_piece = self.board.cell(*self.pending_orientation_position).piece
                self.action_message += (
                    f" · orientez maintenant {next_piece.identifier if next_piece else 'la seconde pièce'}"
                )
                self.draw()
                return
            if self.orientation_effect is not None:
                self.pending_orientation_position = None
                self.orientation_confirming = False
                self.forced_orientation = None
                self._start_orientation_simulation_effect()
                return
            self.pending_move_transaction = None
            self.pending_move_can_rollback = False
            self.pending_orientation_position = None
            self.orientation_confirming = False
            self._finish_piece_turn()
            return
        self.draw()

    def _start_orientation_simulation_effect(self) -> None:
        if self.orientation_effect is None:
            return
        element, placements = self.orientation_effect
        self.opening_active = True
        self.opening_cards = [element]
        self.revealed_elements = {element}
        self.opening_message = (
            f"ÉLÉMENT POINTÉ : {element.label.upper()} · TIRAGE FORCÉ SUR {element.label.upper()}"
        )
        self.action_message = (
            f"La pièce pointe vers {element.label}. L'interstice force son tirage."
        )
        self.draw()
        self.root.after(1100, self._fill_orientation_simulation_cells, list(placements), element)

    def _fill_orientation_simulation_cells(
        self,
        placements: list[tuple[int, int, int]],
        element: Element,
    ) -> None:
        if not self.simulation_mode or self.orientation_effect is None:
            return
        if not placements:
            self.opening_active = False
            self.opening_cards.clear()
            self.revealed_elements.clear()
            self.orientation_effect = None
            self.action_message = (
                f"Effet {element.label} terminé : la ligne et la colonne contenant "
                "la cellule pointée ont été complétées pour accélérer la capture."
            )
            self.draw()
            return
        x, y, value = placements.pop(0)
        target = self.board.cell(x, y)
        target.terrain_number = value
        target.terrain_owner = TerrainOwner.WHITE
        target.transition = CellTransition.TRANSFORMING
        self.opening_message = (
            f"{element.label.upper()} RÉVÉLÉ · COMPLÉTION {target.coordinate} = {value}"
        )
        self.action_message = (
            f"Remplissage de la ligne et de la colonne de l'élément pointé : {target.coordinate} = {value}"
        )
        self.draw()
        self.root.after(420, self._fill_orientation_simulation_cells, placements, element)

    def _finish_piece_turn(self) -> None:
        finished_owner = self.piece_turn_owner
        if self._finish_checkmate_if_any():
            return
        self.combat_failures.finish_turn(finished_owner)
        self.time_engine.advance_main()
        for identifier, state in self.time_engine.states.items():
            self.wheel_visual_positions[identifier] = float(state.position)
        interstice_due = self.round_cycle.finish_piece_move()
        self.piece_turn_owner = self.round_cycle.active_owner.value
        self.current_turn = self.round_cycle.round_number
        if interstice_due:
            self.action_message += " · ronde terminée, ouverture de l'interstice"
            self._start_turn_interstice()
            return

        self._preserve_unplayed_tokens()
        owner = self.round_cycle.active_owner
        self.token_placement = TokenPlacementController(
            self.board, self.opening.player_tokens, (owner,)
        )
        self.action_message += (
            f" · au tour de {owner.value} : placez un jeton ou passez"
        )
        if owner.value in MovementEngine.checked_kings(self.board):
            self.action_message += f" · ROI {owner.value} EN ÉCHEC"
        self.draw()

    def _preserve_unplayed_tokens(self) -> None:
        if not self.token_placement:
            return
        for owner in (TerrainOwner.WHITE, TerrainOwner.BLACK):
            self.opening.player_tokens[owner] = self.token_placement.remaining(owner)

    def _start_turn_interstice(self) -> None:
        self._preserve_unplayed_tokens()
        next_owner = self.round_cycle.active_owner
        self._turn_interstice_events = list(
            self.opening.open_interstice(self.current_turn, next_owner)
        )
        self.opening_active = True
        self.opening_cards.clear()
        self.revealed_elements.clear()
        self.view = WindowView.TIME
        self._advance_turn_interstice()

    def _finish_checkmate_if_any(self) -> bool:
        for loser in (TerrainOwner.WHITE.value, TerrainOwner.BLACK.value):
            if not MovementEngine.is_checkmate(self.board, loser):
                continue
            winner = (
                TerrainOwner.BLACK.value
                if loser == TerrainOwner.WHITE.value
                else TerrainOwner.WHITE.value
            )
            self._finish_game(winner, loser, "échec et mat")
            return True
        return False

    @staticmethod
    def _cycle_record_from_correction(zone_id: str, result) -> CycleRecord:
        operation = result.operation
        if operation in (
            CorrectionOperation.ROTATE_ROW_LEFT,
            CorrectionOperation.ROTATE_ROW_RIGHT,
        ):
            axis = CycleAxis.ROW
            direction = -1 if operation is CorrectionOperation.ROTATE_ROW_LEFT else 1
        elif operation in (
            CorrectionOperation.ROTATE_COLUMN_UP,
            CorrectionOperation.ROTATE_COLUMN_DOWN,
        ):
            axis = CycleAxis.COLUMN
            direction = -1 if operation is CorrectionOperation.ROTATE_COLUMN_UP else 1
        else:
            axis = (
                CycleAxis.TRANSPOSE
                if operation is CorrectionOperation.TRANSPOSE
                else CycleAxis.ANTI_TRANSPOSE
            )
            direction = 1 if operation is CorrectionOperation.TRANSPOSE else -1
        return CycleRecord(
            zone_id, MobileLayer.TERRAIN_NUMBER, axis,
            result.support_index, direction, (),
        )

    def _run_balance_cycle(self) -> CycleRecord | None:
        """Diagnostique chaque ronde et corrige au plus tard au 3e état bloqué."""
        blocked_zones: list[str] = []
        for row in range(1, 4):
            for column in range(1, 4):
                zone_id = f"Z{row}{column}"
                if self.board.zone_owner(zone_id) is not TerrainOwner.NONE:
                    self.blocked_zone_streaks[zone_id] = 0
                    continue
                risk = SudokuRiskAnalyzer.analyze(self.board, zone_id)
                if risk.blocked:
                    self.blocked_zone_streaks[zone_id] += 1
                    blocked_zones.append(zone_id)
                else:
                    self.blocked_zone_streaks[zone_id] = 0

        due_zones = [
            zone_id for zone_id in blocked_zones
            if self.blocked_zone_streaks[zone_id] >= 3 or self.current_turn % 4 == 0
        ]
        operations = (
            CorrectionOperation.ROTATE_ROW_LEFT,
            CorrectionOperation.ROTATE_ROW_RIGHT,
            CorrectionOperation.ROTATE_COLUMN_UP,
            CorrectionOperation.ROTATE_COLUMN_DOWN,
            CorrectionOperation.TRANSPOSE,
            CorrectionOperation.ANTI_TRANSPOSE,
        )
        for zone_id in due_zones:
            for operation in operations:
                result = self.sudoku_correction.apply(
                    self.board, zone_id, operation, allow_locked=True,
                )
                if result.applied:
                    self.blocked_zone_streaks[zone_id] = 0
                    self.action_message = (
                        f"Équilibrage N+4 · permutation numérique {zone_id} · "
                        f"blocage {result.before.blocked_cells}→{result.after.blocked_cells}"
                    )
                    return self._cycle_record_from_correction(zone_id, result)

        # Une sous-fréquence de rejets inférieure au modèle de combat autorise
        # une permutation élémentaire globale, sans compensation par joueur.
        if self.current_turn % 4 != 0 or len(self.combat_rejections) < 3:
            return None
        observed = sum(self.combat_rejections) / len(self.combat_rejections)
        expected = sum(self.combat_expected_rejections) / len(self.combat_expected_rejections)
        if observed + 0.05 >= expected:
            return None
        eligible = tuple(range(0, Board.SIZE, 2))
        axis = CycleAxis.ROW if (self.current_turn // 4) % 2 else CycleAxis.COLUMN
        index = eligible[(self.current_turn // 4) % len(eligible)]
        direction = 1 if (self.current_turn // 4) % 2 else -1
        record = LayerCycleEngine().rotate_global_elements(
            self.board, axis, index, direction,
        )
        self.action_message = (
            f"Équilibrage N+4 · permutation élémentaire · rejets observés "
            f"{observed:.0%}, référence conditionnelle {expected:.0%}"
        )
        return record

    def _complete_turn_interstice(self) -> None:
        winner = self.board.terrain_winner()
        if winner is not TerrainOwner.NONE:
            self.view = WindowView.CHESS
            loser = (
                TerrainOwner.BLACK.value
                if winner is TerrainOwner.WHITE
                else TerrainOwner.WHITE.value
            )
            self._finish_game(
                winner.value, loser,
                "trois terrains capturés et alignés après le bonus d'orientation",
            )
            return
        if self._finish_checkmate_if_any():
            return
        owner = self.round_cycle.active_owner
        self.token_placement = TokenPlacementController(
            self.board, self.opening.player_tokens, (owner,)
        )
        self.view = WindowView.CHESS
        self.action_message = (
            f"{owner.value} : placez un jeton ou passez, puis déplacez une pièce"
        )
        if owner.value in MovementEngine.checked_kings(self.board):
            self.action_message += f" · ROI {owner.value} EN ÉCHEC"
        self.draw()

    def _advance_turn_interstice(self) -> None:
        if not self._turn_interstice_events:
            self.opening_active = False
            self.opening_cards.clear()
            self.revealed_elements.clear()
            self.view = WindowView.CHESS
            if self.current_turn not in self.balance_checked_rounds:
                self.balance_checked_rounds.add(self.current_turn)
                record = self._run_balance_cycle()
                if record is not None:
                    self.animate_permutation(
                        record, frame_count=20,
                        on_complete=self._complete_turn_interstice,
                    )
                    return
            self._complete_turn_interstice()
            return

        event = self._turn_interstice_events.pop(0)
        self.opening_message = event.message
        if event.type is GameEventType.INTERSTICE_OPENED:
            self.opening_cards.clear()
            self.revealed_elements.clear()
        elif event.type is GameEventType.ELEMENT_DRAWN:
            self.opening_cards.append(event.element)
            self.revealed_elements.add(event.element)
        elif event.type is GameEventType.TOKENS_DISTRIBUTED:
            self.visible_token_owners.add(event.owner)
        elif event.type is GameEventType.ROTATION_QUEUED:
            command = next(
                command for command in self.opening.rotation_commands
                if command.element is event.element
            )
            if command.increments:
                direction = 1 if command.increments > 0 else -1
                starts = dict(self.wheel_visual_positions)
                steps = self.time_engine.rotate_manual(
                    command.wheel_id, direction, abs(command.increments)
                )
                self.wheel_animating = True
                self._animate_rotation(
                    starts, steps, 0, 18, self._advance_turn_interstice
                )
                return
        self.draw()
        delay = 650 if event.type is GameEventType.ELEMENT_DRAWN else 360
        self.root.after(delay, self._advance_turn_interstice)

    def _on_time_click(self, x: float, y: float) -> None:
        if self.wheel_animating:
            return
        for direction, bounds in self.rotation_hitboxes.items():
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                self._rotate_selected_wheel(direction)
                return

        for identifier, bounds in reversed(tuple(self.time_hitboxes.items())):
            x0, y0, x1, y1 = bounds
            if x0 <= x <= x1 and y0 <= y <= y1:
                self.selected_time_id = identifier
                self.draw()
                return

        earth_cx, earth_cy, inner_radius, outer_radius = self.earth_hit_region
        distance_squared = (x - earth_cx) ** 2 + (y - earth_cy) ** 2
        if inner_radius ** 2 <= distance_squared <= outer_radius ** 2:
            self.selected_time_id = "wheel_earth"
            self.draw()


def run_window() -> None:
    ElementChessWindow().run()
