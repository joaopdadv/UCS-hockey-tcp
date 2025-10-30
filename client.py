import json
import socket
import sys
import pygame
import threading
import time
from config import (TICK, GameState, PlayerInput, WIDTH, HEIGHT, BLACK, WHITE, FPS, 
                   GRAY, RED, BLUE, PADDLE_WIDTH, PADDLE_HEIGHT, BALL_SIZE, 
                   FONT_SIZE, SMALL_FONT_SIZE, GOAL_WIDTH, GOAL_HEIGHT, GOAL_Y, 
                   PADDLE_DISTANCE_FROM_GOAL)

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
            data = s.recv(1024).decode("utf-8")
            if not data:
                break
            
            buffer += data
            while '{' in buffer and '}' in buffer:
                start = buffer.find('{')
                if start == -1:
                    break
                
                # Encontrar o JSON completo
                brace_count = 0
                end = start
                for i in range(start, len(buffer)):
                    if buffer[i] == '{':
                        brace_count += 1
                    elif buffer[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            end = i
                            break
                
                if brace_count == 0:
                    json_str = buffer[start:end+1]
                    buffer = buffer[end+1:]
                    
                    try:
                        game_state_data = json_string_to_dict(json_str)
                        print(f"Estado do jogo recebido: {game_state_data}")
                    except json.JSONDecodeError as e:
                        print(f"Erro ao decodificar JSON: {e}")
                else:
                    break
                    
        except Exception as e:
            print(f"Erro ao receber dados: {e}")
            break

def send_player_input():
    """Enviar input do jogador para o servidor"""
    player_input = PlayerInput(direction=current_direction)
    json_data = dict_to_json_string(player_input._asdict())
    try:
        s.sendall((json_data + "\n").encode("utf-8"))
    except Exception as e:
        print(f"Erro ao enviar input: {e}")

def draw_field():
    """Desenha o campo de jogo"""
    # Linha central
    pygame.draw.line(screen, WHITE, (WIDTH//2, 0), (WIDTH//2, HEIGHT), 3)
    
    # Círculo central
    pygame.draw.circle(screen, WHITE, (WIDTH//2, HEIGHT//2), 60, 3)
    
    # Bordas do campo
    pygame.draw.rect(screen, WHITE, (0, 0, WIDTH, HEIGHT), 3)

def draw_goals():
    """Desenha os gols"""
    # Gol esquerdo
    goal_left = pygame.Rect(0, GOAL_Y, GOAL_WIDTH, GOAL_HEIGHT)
    pygame.draw.rect(screen, WHITE, goal_left, 3)
    
    # Gol direito  
    goal_right = pygame.Rect(WIDTH - GOAL_WIDTH, GOAL_Y, GOAL_WIDTH, GOAL_HEIGHT)
    pygame.draw.rect(screen, WHITE, goal_right, 3)

def draw_paddles(p1y, p2y):
    """Desenha os paddles dos jogadores"""
    # Paddle esquerdo (Jogador 1) - Azul - na frente do gol
    paddle1_rect = pygame.Rect(
        PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2,
        p1y - PADDLE_HEIGHT//2,
        PADDLE_WIDTH,
        PADDLE_HEIGHT
    )
    pygame.draw.rect(screen, BLUE, paddle1_rect)
    pygame.draw.rect(screen, WHITE, paddle1_rect, 2)
    
    # Paddle direito (Jogador 2) - Vermelho - na frente do gol
    paddle2_rect = pygame.Rect(
        WIDTH - PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2,
        p2y - PADDLE_HEIGHT//2,
        PADDLE_WIDTH,
        PADDLE_HEIGHT
    )
    pygame.draw.rect(screen, RED, paddle2_rect)
    pygame.draw.rect(screen, WHITE, paddle2_rect, 2)

def draw_ball(ballx, bally):
    """Desenha a bola"""
    pygame.draw.circle(screen, WHITE, (int(ballx), int(bally)), BALL_SIZE//2)

def draw_score(score1, score2):
    """Desenha o placar"""
    score_text = font.render(f"{score1} - {score2}", True, WHITE)
    score_rect = score_text.get_rect(center=(WIDTH//2, 50))
    screen.blit(score_text, score_rect)

def draw_waiting_message():
    """Desenha mensagem de aguardando jogadores"""
    waiting_text = font.render("Aguardando jogadores...", True, WHITE)
    waiting_rect = waiting_text.get_rect(center=(WIDTH//2, HEIGHT//2))
    screen.blit(waiting_text, waiting_rect)
    
    instruction_text = small_font.render("Use ↑↓ para controlar", True, GRAY)
    instruction_rect = instruction_text.get_rect(center=(WIDTH//2, HEIGHT//2 + 50))
    screen.blit(instruction_text, instruction_rect)

def draw_game():
    """Desenha todo o jogo"""
    # Limpar tela
    screen.fill(BLACK)
    
    if game_state_data is None:
        draw_waiting_message()
        return
    
    # Verificar se o jogo começou
    if not game_state_data.get('game_started', False):
        draw_field()
        draw_goals()
        draw_paddles(
            game_state_data.get('p1y', HEIGHT//2),
            game_state_data.get('p2y', HEIGHT//2)
        )
        draw_waiting_message()
    else:
        # Desenhar jogo completo
        draw_field()
        draw_goals()
        draw_paddles(
            game_state_data.get('p1y', HEIGHT//2),
            game_state_data.get('p2y', HEIGHT//2)
        )
        draw_ball(
            game_state_data.get('ballx', WIDTH//2),
            game_state_data.get('bally', HEIGHT//2)
        )
        draw_score(
            game_state_data.get('score1', 0),
            game_state_data.get('score2', 0)
        )

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
        
        # Enviar input apenas se mudou
        if new_direction != current_direction:
            current_direction = new_direction
            send_player_input()
        
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
