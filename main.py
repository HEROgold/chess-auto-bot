from src import gui
import tkinter as tk
import logging

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.FileHandler(filename='cab.log', encoding='utf-8', mode='w'))
    window = tk.Tk()
    my_gui = gui.GUI(window)
    window.mainloop()
