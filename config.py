from collections import namedtuple

TICK_RATE = 60
TICK = 1 / TICK_RATE

WIDTH = 800
HEIGHT = 600

# Pygame colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
BLUE = (0, 0, 255)

# Game constants
FPS = 60
PADDLE_WIDTH = 20
PADDLE_HEIGHT = 80
BALL_SIZE = 20
BALL_SPEED = 8

# Goal constants
GOAL_WIDTH = 20
GOAL_HEIGHT = int(HEIGHT * 0.33)  # 33% da altura
GOAL_Y = (HEIGHT - GOAL_HEIGHT) // 2  # Centralizado verticalmente

# Paddle positioning (in front of goals)
PADDLE_DISTANCE_FROM_GOAL = 30

# Drawing constants
FONT_SIZE = 36
SMALL_FONT_SIZE = 24

GameState = namedtuple("GameState", ["p1y", "p2y", "ballx", "bally", "ballvx", "ballvy", "score1", "score2", "game_started"])
PlayerInput = namedtuple("PlayerInput", ["direction"]) # direction: -1 (cima), 0 (parado), 1 (baixo)