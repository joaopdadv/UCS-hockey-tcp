from collections import namedtuple

TICK_RATE = 60
TICK = 1 / TICK_RATE

WIDTH = 800
HEIGHT = 600

# Pygame colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Game constants
FPS = 60

GameState = namedtuple("GameState", ["p1y", "p2y", "ballx", "bally", "score1", "score2"])
PlayerInput = namedtuple("PlayerInput", ["direction"]) # direction: -1 (cima), 0 (parado), 1 (baixo)