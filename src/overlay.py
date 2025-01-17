import logging
import math
import sys
import threading
from typing import Any, NoReturn

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QBrush, QColor, QGuiApplication, QPainter, QPen, QPolygon
from PyQt5.QtWidgets import QApplication, QWidget


class OverlayScreen(QWidget):
    def __init__(self, stockfish_queue) -> None:
        super().__init__()
        self.logger = logging.getLogger(f"CAB.{self.__class__.__name__}")
        self.stockfish_queue = stockfish_queue

        # Set the window to be the size of the screen
        self.screen = QGuiApplication.screens()[0]
        self.setFixedWidth(self.screen.size().width())
        self.setFixedHeight(self.screen.size().height())
        # Set the window to be transparent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        # A list of QPolygon objects containing the points of the arrows
        self.arrows = []
        # Start the message queue thread
        self.message_queue_thread = threading.Thread(target=self.message_queue_thread)
        self.message_queue_thread.start()

    def message_queue_thread(self) -> NoReturn:
        """
        This thread is used to receive messages from the stockfish message queue
        and update the arrows
        Args:
            None
        Returns:
            None
        """

        while True:
            message = self.stockfish_queue.get()
            self.set_arrows(message)

    def set_arrows(self, arrows) -> None:
        """
        This function is used to set the arrows to be drawn on the screen
        Args:
            arrows: A list of tuples containing the start and end position of the arrows
            in the form of ((start_point, end_point), (start_point, end_point))
        Returns:
            None
        """

        self.arrows = []
        for arrow in arrows:
            poly = self.get_arrow_polygon(
                QPoint(arrow[0][0], arrow[0][1]), QPoint(arrow[1][0], arrow[1][1])
            )
            self.arrows.append(poly)
        self.update()

    def paint_event(self, event) -> None:
        self.logger.debug("paint event")
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setPen(QPen(Qt.GlobalColor.red, 1, Qt.PenStyle.NoPen))
        painter.setBrush(QBrush(QColor(255, 0, 0, 122), Qt.BrushStyle.SolidPattern))
        for arrow in self.arrows:
            painter.drawPolygon(arrow)
        painter.end()

    # TODO: Catch and handle specific errors
    @staticmethod
    def get_arrow_polygon(start_point, end_point) -> Any:
        """
        This function is used to get the polygon for the arrow
        Args:
            start_point: The start point of the arrow
            end_point: The end point of the arrow
        Returns:
            A QPolygon object containing the points of the arrow
        """
        dx, dy = (
            start_point.x() - end_point.x(),
            start_point.y() - end_point.y(),
        )
        length = math.sqrt(dx**2 + dy**2)
        norm_x, norm_y = (dx / length, dy / length)
        perp_x = -norm_y
        perp_y = norm_x
        arrow_height = 25
        left_x = end_point.x() + arrow_height * norm_x * 1.5 + arrow_height * perp_x
        left_y = end_point.y() + arrow_height * norm_y * 1.5 + arrow_height * perp_y
        right_x = (
            end_point.x() + arrow_height * norm_x * 1.5 - arrow_height * perp_x
        )
        right_y = (
            end_point.y() + arrow_height * norm_y * 1.5 - arrow_height * perp_y
        )
        point2 = QPoint(int(left_x), int(left_y))
        point3 = QPoint(int(right_x), int(right_y))
        mid_point1 = QPoint(
            int(2 / 5 * point2.x() + 3 / 5 * point3.x()),
            int(2 / 5 * point2.y() + 3 / 5 * point3.y()),
        )
        mid_point2 = QPoint(
            int(3 / 5 * point2.x() + 2 / 5 * point3.x()),
            int(3 / 5 * point2.y() + 2 / 5 * point3.y()),
        )
        start_left = QPoint(
            int(start_point.x() + arrow_height / 5 * perp_x),
            int(start_point.y() + arrow_height / 5 * perp_y),
        )
        start_right = QPoint(
            int(start_point.x() - arrow_height / 5 * perp_x),
            int(start_point.y() - arrow_height / 5 * perp_y),
        )
        return QPolygon(
            [
                end_point,
                point2,
                mid_point1,
                start_right,
                start_left,
                mid_point2,
                point3,
            ]
        )

def run(stockfish_queue) -> None:
    """
    This function is used to run the overlay
    Args:
        stockfish_queue: The message queue used to communicate with the stockfish thread
    Returns:
        None
    """

    app = QApplication(sys.argv)
    overlay = OverlayScreen(stockfish_queue)
    overlay.show()
    app.exec()