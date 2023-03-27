from abc import ABC, abstractmethod

from utilities import attach_to_session


# Base abstract class for different chess sites
class Grabber(ABC):
    def __init__(self, chrome_url, chrome_session_id):
        self.chrome = attach_to_session(chrome_url, chrome_session_id)
        self._board_elem = None

    def get_board(self):
        return self._board_elem

    # Returns the coordinates of the top left corner of the ChromeDriver
    def get_top_left_corner(self):
        canvas_x_offset = self.chrome.execute_script(
            "return window.screenX + (window.outerWidth - window.innerWidth) / 2 - window.scrollX;"
        )
        canvas_y_offset = self.chrome.execute_script(
            "return window.screenY + (window.outerHeight - window.innerHeight) - window.scrollY;"
        )
        return canvas_x_offset, canvas_y_offset

    # Sets the _board_elem variable
    @staticmethod
    @abstractmethod
    def update_board_elem():
        pass

    # Returns True if white, False if black,
    # None if the color is not found
    @staticmethod
    @abstractmethod
    def is_white():
        pass

    # Checks if the game over window popup is open
    # Returns True if it is, False if it isn't
    @staticmethod
    @abstractmethod
    def is_game_over():
        pass

    # Returns the current board move list
    # Ex. ["e4", "c5", "Nf3"]
    @staticmethod
    @abstractmethod
    def get_move_list():
        pass

    # Returns True if the player does puzzles
    # and False if not
    @staticmethod
    @abstractmethod
    def is_game_puzzles():
        pass

    # Clicks the next button on the puzzles page
    @staticmethod
    @abstractmethod
    def click_puzzle_next():
        pass

    # Makes a mouseless move
    @staticmethod
    @abstractmethod
    def make_mouseless_move(move, move_count):
        pass