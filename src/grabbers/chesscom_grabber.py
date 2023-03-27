import logging
from typing import Literal

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By

from .grabber import Grabber


class ChesscomGrabber(Grabber):
    def __init__(self, chrome_url, chrome_session_id) -> None:
        super().__init__(chrome_url, chrome_session_id)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.moves_list = {}

    def update_board_element(self) -> None:
        self.logger.debug("Updating board element")
        try:
            self._board_element = self.chrome.find_element(
                By.XPATH, "//*[@id='board-vs-personalities']"
            )
        except NoSuchElementException:
            try:
                self._board_element = self.chrome.find_element(
                    By.XPATH, "//*[@id='board-single']"
                )
            except NoSuchElementException:
                self._board_element = None
        self.logger.debug(f"Updated board element: {self._board_element}")

    def is_white(self) -> bool | None:
        # Find the square names list
        self.logger.debug("checking is white")
        square_names = None
        try:
            coordinates = self.chrome.find_element(
                By.XPATH, "//*[@id='board-vs-personalities']//*[name()='svg']"
            )
            square_names = coordinates.find_elements(By.XPATH, ".//*")
        except NoSuchElementException:
            try:
                coordinates = self.chrome.find_elements(
                    By.XPATH, "//*[@id='board-single']//*[name()='svg']"
                )
                coordinates = [
                    x for x in coordinates if x.get_attribute("class") == "coordinates"
                ][0]
                square_names = coordinates.find_elements(By.XPATH, ".//*")
            except NoSuchElementException:
                return None

        # Find the square with the smallest x and biggest y values (bottom left number)
        self.logger.debug("finding bottom left square")
        elem = None
        min_x = None
        max_y = None
        for i in range(len(square_names)):
            name_element = square_names[i]
            x = float(name_element.get_attribute("x"))
            y = float(name_element.get_attribute("y"))

            if i == 0 or (x <= min_x and y >= max_y):
                min_x = x
                max_y = y
                elem = name_element

        # Use this square to determine whether the player is white or black
        self.logger.debug("determining if player is black of white")
        num = elem.text
        return num == "1"

    def is_game_over(self) -> bool:
        self.logger.debug("checking game over")
        try:
            # Find the game over window
            game_over_window = self.chrome.find_element(
                By.CLASS_NAME, "board-modal-container"
            )
            return game_over_window is not None
        except NoSuchElementException:
            # Return False since the game over window is not found
            return False

    def get_move_list(self) -> list | None:
        self.logger.debug("getting moves list")
        # Find the moves list
        try:
            move_list_elem = self.chrome.find_element(By.TAG_NAME, "vertical-move-list")
        except NoSuchElementException:
            return None
        # Select all children with class containing "white node" or "black node"
        # Moves that are not pawn moves have a different structure
        # containing children
        # If the moves list is not empty, find only the new moves
        # If the moves list is empty, find all moves
        moves = (
            move_list_elem.find_elements(
                By.CSS_SELECTOR, "div.move [data-ply]:not([data-processed])"
            )
            if self.moves_list
            else move_list_elem.find_elements(
                By.CSS_SELECTOR, "div.move [data-ply]"
            )
        )
        for move in moves:
            move_class = move.get_attribute("class")

            # Check if it is indeed a move
            if "white node" not in move_class and "black node" not in move_class:
                continue

            try:
                child = move.find_element(By.XPATH, "./*")
                figure = child.get_attribute("data-figurine")
            except NoSuchElementException:
                figure = None
            if figure is None:
                self.moves_list[move.get_attribute("data-ply")] = move.text
            elif "=" in move.text:
                m = move.text + figure
                if "+" in m:
                    m = m.replace("+", "")
                    m += "+"
                self.moves_list[move.get_attribute("data-ply")] = m
            else:
                self.moves_list[move.get_attribute("data-ply")] = figure + move.text
            self.chrome.execute_script("arguments[0].setAttribute('data-processed', 'true')", move)

        return list(self.moves_list.values())

    @staticmethod
    def is_game_puzzles() -> Literal[False]:
        return False

    @staticmethod
    def click_puzzle_next() -> None:
        # TODO document why this method is empty
        pass

    @staticmethod
    def make_mouseless_move(move, move_count) -> None:
        # TODO document why this method is empty
        pass
