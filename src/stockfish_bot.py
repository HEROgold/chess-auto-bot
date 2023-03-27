import os
import re
import sys
import time

import chess
import keyboard
import multiprocess
import pyautogui
from stockfish import Stockfish

from grabbers.chesscom_grabber import ChesscomGrabber
from grabbers.lichess_grabber import LichessGrabber
from utilities import char_to_num


class StockfishBot(multiprocess.Process):
    def __init__(
        self,
        chrome_url,
        chrome_session_id,
        website,
        pipe,
        overlay_queue,
        stockfish_path,
        enable_manual_mode,
        enable_mouseless_mode,
        enable_non_stop_puzzles,
        bongcloud,
        slow_mover,
        skill_level,
        stockfish_depth,
        memory,
        cpu_threads,
    ) -> None:
        multiprocess.Process.__init__(self)

        self.chrome_url = chrome_url
        self.chrome_session_id = chrome_session_id
        self.website = website
        self.pipe = pipe
        self.overlay_queue = overlay_queue
        self.stockfish_path = stockfish_path
        self.enable_manual_mode = enable_manual_mode
        self.enable_mouseless_mode = enable_mouseless_mode
        self.enable_non_stop_puzzles = enable_non_stop_puzzles
        self.bongcloud = bongcloud
        self.slow_mover = slow_mover
        self.skill_level = skill_level
        self.stockfish_depth = stockfish_depth
        self.grabber = None
        self.memory = memory
        self.cpu_threads = cpu_threads
        self.is_white = None

    # Converts a move to screen coordinates
    # Example: "a1" -> (x, y)
    def move_to_screen_pos(self, move) -> tuple:
        # Get the absolute top left corner of the website
        canvas_x_offset, canvas_y_offset = self.grabber.get_top_left_corner()

        # Get the absolute board position
        board_x = canvas_x_offset + self.grabber.get_board().location["x"]
        board_y = canvas_y_offset + self.grabber.get_board().location["y"]

        # Get the square size
        square_size = self.grabber.get_board().size["width"] / 8

        # Depending on the player color, the board is flipped, so the coordinates need to be adjusted
        if self.is_white:
            x = board_x + square_size * (char_to_num(move[0]) - 1) + square_size / 2
            y = board_y + square_size * (8 - int(move[1])) + square_size / 2
        else:
            x = board_x + square_size * (8 - char_to_num(move[0])) + square_size / 2
            y = board_y + square_size * (int(move[1]) - 1) + square_size / 2

        return x, y

    def get_move_pos(self, move) -> tuple[tuple, tuple]:
        # Get the start and end position screen coordinates
        start_pos_x, start_pos_y = self.move_to_screen_pos(move[:2])
        end_pos_x, end_pos_y = self.move_to_screen_pos(move[2:4])

        return (start_pos_x, start_pos_y), (end_pos_x, end_pos_y)

    def make_move(self, move) -> None:
        # Get the start and end position screen coordinates
        start_pos, end_pos = self.get_move_pos(move)

        # Drag the piece from the start to the end position
        pyautogui.moveTo(start_pos[0], start_pos[1])
        pyautogui.dragTo(end_pos[0], end_pos[1])

        # Check for promotion. If there is a promotion,
        # promote to the corresponding piece type
        if len(move) == 5:
            self.promote_piece(move)

    # TODO Rename this here and in `make_move`
    def promote_piece(self, move) -> None:
        time.sleep(0.1)
        end_pos_x = None
        end_pos_y = None
        if move[4] == "n":
            end_pos_x, end_pos_y = self.move_to_screen_pos(
                move[2] + str(int(move[3]) - 1)
            )
        elif move[4] == "r":
            end_pos_x, end_pos_y = self.move_to_screen_pos(
                move[2] + str(int(move[3]) - 2)
            )
        elif move[4] == "b":
            end_pos_x, end_pos_y = self.move_to_screen_pos(
                move[2] + str(int(move[3]) - 3)
            )

        pyautogui.moveTo(x=end_pos_x, y=end_pos_y)
        pyautogui.click(button="left")

    def wait_for_gui_to_delete(self) -> None:
        while self.pipe.recv() != "DELETE":
            pass # NOSONAR

    def _init_stockfish(self) -> None:
        """Initialize Stockfish"""
        parameters = {
            "Threads": self.cpu_threads,
            "Hash": self.memory,
            "Ponder": "true",
            "Slow Mover": self.slow_mover,
            "Skill Level": self.skill_level,
        }
        try:
            return Stockfish(
                path=self.stockfish_path,
                depth=self.stockfish_depth,
                parameters=parameters,
            )
        except PermissionError:
            self.pipe.send("ERR_PERM")
            return
        except OSError:
            self.pipe.send("ERR_EXE")
            return

    def _check_board(self) -> bool:
        # Return if the board element is not found
        self.grabber.update_board_elem()
        return self.grabber.get_board() is not None

    def _check_starting_position(self) -> list | None:
        # Get the starting position
        # Return if the starting position is not found
        move_list = self.grabber.get_move_list()
        if move_list is None:
            self.pipe.send("ERR_MOVES")
            return None
        return move_list

    def _check_is_white(self) -> bool:
        self.is_white = self.grabber.is_white()
        return self.is_white is not None

    def _check_game_over(self, move_list: list) -> bool:
        # Check if the game is over
        score_pattern = r"(\d+)\-(\d+)"
        if move_list and re.match(score_pattern, move_list[-1]):
            self.pipe.send("ERR_GAMEOVER")
            return False
        return True

    def _move_board(self, board: chess.Board, move_list: list) -> list:
        # Update the board with the starting position
        for move in move_list:
            board.push_san(move)
        return [move.uci() for move in board.move_stack]

    def _send_restart(self) -> None:
        self.grabber.click_puzzle_next()
        self.pipe.send("RESTART")
        self.wait_for_gui_to_delete()

    def run(self) -> None:
        if self.website == "chesscom":
            self.grabber = ChesscomGrabber(self.chrome_url, self.chrome_session_id)
        else:
            self.grabber = LichessGrabber(self.chrome_url, self.chrome_session_id)

        stockfish: Stockfish = self._init_stockfish()

        if self._check_board() == False:
            self.pipe.send("ERR_BOARD")
            return

        if self._check_is_white() == False:
            self.pipe.send("ERR_COLOR")
            return

        move_list = self._check_starting_position()
        if not move_list:
            self.pipe.send("ERR_MOVES")
            return

        if self._check_game_over(move_list) == False:
            self.pipe.send("ERR_GAMEOVER")
            return

        board = chess.Board()
        move_list_uci = self._move_board(board, move_list)

        # Update Stockfish with the starting position
        stockfish.set_position(move_list_uci)

        # Notify GUI that bot is ready
        self.pipe.send("START")

        # Send the first moves to the GUI (if there are any)
        if len(move_list) > 0:
            self.pipe.send("M_MOVE" + ",".join(move_list))

        # Start the game loop
        while True:
            # Think of a move
            move = None
            move_count = len(board.move_stack)
            if self.bongcloud and move_count <= 3:
                if move_count == 0:
                    move = "e2e3"
                elif move_count == 1:
                    move = "e7e6"
                elif move_count == 2:
                    move = "e1e2"
                elif move_count == 3:
                    move = "e8e7"

                # Hardcoded bongcloud move is not legal,
                # so find a legal move
                if not board.is_legal(chess.Move.from_uci(move)):
                    move = stockfish.get_best_move()
            else:
                move = stockfish.get_best_move()

            # Wait for keypress or player movement if in manual mode
            self_moved = False
            if self.enable_manual_mode:
                move_start_pos, move_end_pos = self.get_move_pos(move)
                self.overlay_queue.put(
                    [
                        (
                            (int(move_start_pos[0]), int(move_start_pos[1])),
                            (int(move_end_pos[0]), int(move_end_pos[1])),
                        ),
                    ]
                )
                while not keyboard.is_pressed("3"):
                    if len(move_list) != len(self.grabber.get_move_list()):
                        self_moved = True
                        move_list = self.grabber.get_move_list()
                        move_san = move_list[-1]
                        move = board.parse_san(move_san).uci()
                        board.push_uci(move)
                        stockfish.make_moves_from_current_position([move])
                        break

            if not self_moved:
                move_san = board.san(
                    chess.Move(
                        chess.parse_square(move[:2]),
                        chess.parse_square(move[2:4]),
                    )
                )
                board.push_uci(move)
                stockfish.make_moves_from_current_position([move])
                move_list.append(move_san)
                if (
                    self.enable_mouseless_mode
                    and not self.grabber.is_game_puzzles()
                ):
                    self.grabber.make_mouseless_move(move, move_count + 1)
                else:
                    self.make_move(move)

            self.overlay_queue.put([])

            # Send the move to the GUI
            self.pipe.send(f"S_MOVE{move_san}")

            # Check if the game is over
            if board.is_checkmate():
                # Send restart message to GUI
                if (
                    self.enable_non_stop_puzzles
                    and self.grabber.is_game_puzzles()
                ):
                    self._send_restart()
                return

            time.sleep(0.1)

            # Wait for a response from the opponent
            # by finding the differences between
            # the previous and current position
            previous_move_list = move_list.copy()
            while True:
                if self.grabber.is_game_over():
                    # Send restart message to GUI
                    if (
                        self.enable_non_stop_puzzles
                        and self.grabber.is_game_puzzles()
                    ):
                        self._send_restart()
                    return
                move_list = self.grabber.get_move_list()
                if move_list is None:
                    return
                if len(move_list) > len(previous_move_list):
                    break

            # Get the move that the opponent made
            move = move_list[-1]
            self.pipe.send(f"S_MOVE{move}")
            board.push_san(move)
            stockfish.make_moves_from_current_position([str(board.peek())])
            if board.is_checkmate():
                # Send restart message to GUI
                if self.enable_non_stop_puzzles and self.grabber.is_game_puzzles():
                    self._send_restart()
                return