from collections import namedtuple

# Tick e FPS
TICK_RATE = 60
TICK = 1 / TICK_RATE
FPS = 60

# Tamanho da janela
WIDTH = 800
HEIGHT = 600

# HUD (faixa do placar) separada do campo
HUD_HEIGHT = 60  # altura da faixa superior

# Cores
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)   # (mantida para compatibilidade)
BLUE = (0, 0, 255)  # (mantida para compatibilidade)

# >>> Novas cores usadas pelo cliente <<<
LIGHT_BLUE = (173, 216, 230)  # fundo do campo
PINK = (255, 105, 180)        # jogador esquerdo
YELLOW = (255, 255, 0)        # jogador direito

# Tamanhos dos paddles/bola
PADDLE_WIDTH = 12
PADDLE_HEIGHT = 48
BALL_SIZE = 14
BALL_SPEED = 6

# Campo útil (sem a HUD)
FIELD_HEIGHT = HEIGHT - HUD_HEIGHT

# Gols em formato de "C" (dentro do campo, separados da parede do fundo)
GOAL_INSET = 40           # distância da parede lateral até a "haste" vertical do C
GOAL_BAR_LENGTH = 48      # comprimento das barras superior/inferior do C
GOAL_THICKNESS = 18       # espessura visual das linhas do gol (deixei mais grossa a seu pedido)

GOAL_HEIGHT = int(FIELD_HEIGHT * 0.33)                  # 33% da altura útil
GOAL_Y = HUD_HEIGHT + (FIELD_HEIGHT - GOAL_HEIGHT) // 2 # centralizado verticalmente

# Posição dos paddles (um pouco à frente do gol)
PADDLE_DISTANCE_FROM_GOAL = GOAL_INSET + 70

# Fontes
FONT_SIZE = 36
SMALL_FONT_SIZE = 24

# Tempo de partida (3 minutos)
TIME_LIMIT_SECONDS = 180

# Estado do jogo (inclui tempo e status de game over)
GameState = namedtuple(
    "GameState",
    [
        "p1y", "p2y",
        "ballx", "bally", "ballvx", "ballvy",
        "score1", "score2",
        "game_started",
        "time_left",     # segundos restantes
        "game_over",     # bool
        "winner"         # 0=empate, 1=esquerda(rosa), 2=direita(amarelo)
    ]
)

# Input do jogador: -1 (cima), 0 (parado), 1 (baixo)
PlayerInput = namedtuple("PlayerInput", ["direction"])
