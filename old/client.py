import json
import socket
import sys
import pygame
import threading
import time
from config import (
    TICK, GameState, PlayerInput, WIDTH, HEIGHT,
    BLACK, WHITE, GRAY,
    FPS, LIGHT_BLUE, PINK, YELLOW,
    PADDLE_WIDTH, PADDLE_HEIGHT, BALL_SIZE,
    FONT_SIZE, SMALL_FONT_SIZE,
    GOAL_HEIGHT, GOAL_Y, PADDLE_DISTANCE_FROM_GOAL,
    HUD_HEIGHT, GOAL_INSET, GOAL_BAR_LENGTH, GOAL_THICKNESS
)

if len(sys.argv) != 3:
    print(f"Uso: python {sys.argv[0]} <host> <porta>")
    sys.exit(1)

host = sys.argv[1]
try:
    port = int(sys.argv[2])
except ValueError:
    print("A porta deve ser um número inteiro.")
    sys.exit(1)

def dict_to_json_string(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False)

def json_string_to_dict(json_str: str) -> dict:
    return json.loads(json_str)

# Variáveis globais
running = True
current_direction = 0
game_state_data = None

# Conectar ao servidor
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
print(f"Conectado ao servidor {host}:{port}")

def receive_game_state():
    """Thread para receber o estado do jogo do servidor"""
    global game_state_data
    buffer = ""
    while running:
        try:
            data = s.recv(4096).decode("utf-8", errors="ignore")
            if not data:
                break
            buffer += data
            while True:
                start = buffer.find('{')
                if start == -1:
                    buffer = ""
                    break
                # balanceamento de chaves
                brace = 0
                end = None
                for i,ch in enumerate(buffer[start:], start):
                    if ch == '{':
                        brace += 1
                    elif ch == '}':
                        brace -= 1
                        if brace == 0:
                            end = i
                            break
                if end is None:
                    # aguardar mais dados
                    # mantém o buffer até próxima iteração
                    if start > 0:
                        buffer = buffer[start:]
                    break
                try:
                    json_str = buffer[start:end+1]
                    buffer = buffer[end+1:]
                    game_state_data = json_string_to_dict(json_str)
                except json.JSONDecodeError:
                    # descarta este bloco e continua
                    buffer = buffer[end+1:]
                    continue
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
            break

def send_player_input():
    """Enviar input do jogador para o servidor"""
    player_input = PlayerInput(direction=current_direction)
    json_data = dict_to_json_string(player_input._asdict())
    try:
        s.sendall((json_data + "\\n").encode("utf-8"))
    except Exception as e:
        print(f"Erro ao enviar input: {e}")

# ---------------------- Desenho ----------------------

def draw_hud(score1, score2, time_left, game_started, game_over):
    """Faixa superior com placar e tempo (separada do campo)."""
    # faixa
    pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, HUD_HEIGHT))
    # linha de separação
    pygame.draw.line(screen, WHITE, (0, HUD_HEIGHT), (WIDTH, HUD_HEIGHT), 2)

    # placar centralizado
    score_text = font.render(f"{score1} - {score2}", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH//2, HUD_HEIGHT//2))
    screen.blit(score_text, score_rect)

    # tempo no canto direito
    total_secs = int(max(0, time_left))
    minutes = total_secs // 60
    seconds = total_secs % 60
    time_text = small_font.render(f"{minutes:01d}:{seconds:02d}", True, WHITE)
    time_rect = time_text.get_rect(midright=(WIDTH - 16, HUD_HEIGHT//2))
    screen.blit(time_text, time_rect)

    # mensagem de espera
    if not game_started and not game_over:
        waiting_text = small_font.render("Aguardando jogadores...", True, GRAY)
        waiting_rect = waiting_text.get_rect(midleft=(16, HUD_HEIGHT//2))
        screen.blit(waiting_text, waiting_rect)

def draw_field():
    """Desenha somente o campo (sem linha/círculo central, estilo Video Olympics)."""
    # Fundo azul claro
    screen.fill(LIGHT_BLUE)
    # linhas laterais e inferior (o topo é a HUD)
    pygame.draw.line(screen, WHITE, (0, HUD_HEIGHT), (0, HEIGHT), 2)
    pygame.draw.line(screen, WHITE, (WIDTH-1, HUD_HEIGHT), (WIDTH-1, HEIGHT), 2)
    pygame.draw.line(screen, WHITE, (0, HEIGHT-1), (WIDTH, HEIGHT-1), 2)

def draw_goals():
    """Desenha os gols em 'C', pretos e separados da parede do fundo."""
    # Esquerda (abre para a direita)
    x_left = GOAL_INSET
    y_top = GOAL_Y
    y_bot = GOAL_Y + GOAL_HEIGHT
    pygame.draw.line(screen, BLACK, (x_left, y_top), (x_left, y_bot), GOAL_THICKNESS)  # haste vertical
    pygame.draw.line(screen, BLACK, (x_left, y_top), (x_left + GOAL_BAR_LENGTH, y_top), GOAL_THICKNESS)  # barra superior
    pygame.draw.line(screen, BLACK, (x_left, y_bot), (x_left + GOAL_BAR_LENGTH, y_bot), GOAL_THICKNESS)  # barra inferior

    # Direita (abre para a esquerda)
    x_right = WIDTH - GOAL_INSET
    pygame.draw.line(screen, BLACK, (x_right, y_top), (x_right, y_bot), GOAL_THICKNESS)
    pygame.draw.line(screen, BLACK, (x_right - GOAL_BAR_LENGTH, y_top), (x_right, y_top), GOAL_THICKNESS)
    pygame.draw.line(screen, BLACK, (x_right - GOAL_BAR_LENGTH, y_bot), (x_right, y_bot), GOAL_THICKNESS)

def draw_paddles(p1y, p2y):
    """Desenha os paddles dos jogadores - menores, à frente do gol."""
    # Paddle esquerdo (Rosa)
    paddle1_rect = pygame.Rect(
        PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2,
        p1y - PADDLE_HEIGHT//2,
        PADDLE_WIDTH,
        PADDLE_HEIGHT
    )
    pygame.draw.rect(screen, PINK, paddle1_rect)

    # Paddle direito (Amarelo)
    paddle2_rect = pygame.Rect(
        WIDTH - PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2,
        p2y - PADDLE_HEIGHT//2,
        PADDLE_WIDTH,
        PADDLE_HEIGHT
    )
    pygame.draw.rect(screen, YELLOW, paddle2_rect)

def draw_ball(ballx, bally):
    """Desenha a bola"""
    pygame.draw.rect(screen, WHITE, pygame.Rect(int(ballx - BALL_SIZE//2), int(bally - BALL_SIZE//2), BALL_SIZE, BALL_SIZE))

def draw_game_over(winner, score1, score2):
    """Overlay de fim de jogo com vencedor."""
    overlay = pygame.Surface((WIDTH, HEIGHT - HUD_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (0, HUD_HEIGHT))

    title = font.render("FIM DE JOGO", True, WHITE)
    title_rect = title.get_rect(center=(WIDTH//2, HUD_HEIGHT + (HEIGHT - HUD_HEIGHT)//2 - 30))
    screen.blit(title, title_rect)

    if winner == 1:
        msg = "Vencedor: Jogador 1 (Rosa)"
    elif winner == 2:
        msg = "Vencedor: Jogador 2 (Amarelo)"
    else:
        msg = "Empate"
    msg_text = small_font.render(msg, True, WHITE)
    msg_rect = msg_text.get_rect(center=(WIDTH//2, HUD_HEIGHT + (HEIGHT - HUD_HEIGHT)//2 + 20))
    screen.blit(msg_text, msg_rect)

def draw_game():
    """Desenha todo o jogo"""
    draw_field()

    # HUD (em cima do fundo, antes do campo)
    time_left = game_state_data.get('time_left', 180) if game_state_data else 180
    game_started = game_state_data.get('game_started', False) if game_state_data else False
    game_over = game_state_data.get('game_over', False) if game_state_data else False
    score1 = game_state_data.get('score1', 0) if game_state_data else 0
    score2 = game_state_data.get('score2', 0) if game_state_data else 0
    draw_hud(score1, score2, time_left, game_started, game_over)

    if game_state_data is None:
        return
    
    draw_goals()

    # Se não começou, desenha posições e instrução já aparecem na HUD
    draw_paddles(
        game_state_data.get('p1y', HEIGHT//2),
        game_state_data.get('p2y', HEIGHT//2)
    )

    if game_started:
        draw_ball(
            game_state_data.get('ballx', WIDTH//2),
            game_state_data.get('bally', HEIGHT//2)
        )

    if game_over:
        winner = game_state_data.get('winner', 0)
        draw_game_over(winner, score1, score2)

# Inicializar pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hockey Client")
clock = pygame.time.Clock()

# Inicializar fontes
font = pygame.font.Font(None, FONT_SIZE)
small_font = pygame.font.Font(None, SMALL_FONT_SIZE)

# Iniciar thread para receber dados do servidor
receive_thread = threading.Thread(target=receive_game_state, daemon=True)
receive_thread.start()

print("Cliente iniciado. Use as setas para cima/baixo para controlar. Pressione ESC para sair.")

last_send = 0.0
SEND_EVERY = 0.10  # segundos

try:
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
        
        # Capturar input das teclas
        keys = pygame.key.get_pressed()
        new_direction = 0
        
        if keys[pygame.K_UP]:
            new_direction = -1
        elif keys[pygame.K_DOWN]:
            new_direction = 1
        
        # Enviar input quando mudar OU a cada SEND_EVERY
        now = time.time()
        if new_direction != current_direction or (now - last_send) >= SEND_EVERY:
            current_direction = new_direction
            send_player_input()
            last_send = now
        
        # Desenhar jogo
        draw_game()
        
        pygame.display.flip()
        clock.tick(FPS)

except KeyboardInterrupt:
    pass

running = False
s.close()
pygame.quit()
print("Cliente encerrado.")