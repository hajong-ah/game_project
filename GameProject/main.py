import tkinter as tk
from game_core import AdventureRPGGame
import os, sys
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

if __name__ == "__main__":
    root = tk.Tk()
    game = AdventureRPGGame(root)
    root.mainloop()