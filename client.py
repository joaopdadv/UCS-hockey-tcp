import json
import socket
import sys
import pygame
import threading
import time
from config import TICK, GameState, PlayerInput, WIDTH, HEIGHT, BLACK, WHITE, FPS

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

# Inicializar pygame
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Hockey Client")
clock = pygame.time.Clock()

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
        
        # Limpar tela
        screen.fill(BLACK)
        
        # Aqui você pode adicionar renderização básica se quiser
        # Por enquanto, apenas uma tela preta
        
        pygame.display.flip()
        clock.tick(FPS)

except KeyboardInterrupt:
    pass

running = False
s.close()
pygame.quit()
print("Cliente encerrado.")
