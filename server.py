import json
import socket
import threading
import sys
from collections import namedtuple
import time
from config import (TICK, GameState, PlayerInput, HEIGHT, WIDTH, PADDLE_WIDTH, PADDLE_HEIGHT, 
                   BALL_SIZE, BALL_SPEED, GOAL_WIDTH, GOAL_HEIGHT, GOAL_Y, PADDLE_DISTANCE_FROM_GOAL)
import random
import math


clients = []
client_players = {}  # mapeia conexão para número do jogador (1 ou 2)
game_state = GameState(p1y=HEIGHT//2, p2y=HEIGHT//2, ballx=WIDTH//2, bally=HEIGHT//2, 
                      ballvx=0, ballvy=0, score1=0, score2=0, game_started=False)
p1_input = PlayerInput(direction=0)
p2_input = PlayerInput(direction=0)
mutex = threading.Lock()

if len(sys.argv) != 2:
    print(f"Uso: python {sys.argv[0]} <port>")
    sys.exit(1)

host = ''
porta = int(sys.argv[1])

BUFFER_SIZE = 1024


# Monta strings a partir dos dados recebidos
def get_lines(conn):
    current_line = ""
    while True:
        data = conn.recv(BUFFER_SIZE) 
        if not data:
            if current_line:
                yield current_line
            break

        decoded = data.decode("utf-8", errors="ignore")
        parts = decoded.split("\n")

        for part in parts[:-1]:
            yield current_line + part
            current_line = ""

        current_line += parts[-1]

def handle_client(conn, addr):
    global p1_input, p2_input
    
    # Determinar qual jogador é este cliente
    player_num = None
    with mutex:
        if conn not in client_players:
            if len(client_players) == 0:
                player_num = 1
            elif len(client_players) == 1:
                player_num = 2
            else:
                print(f"Máximo de 2 jogadores. Rejeitando {addr}")
                conn.close()
                return
            client_players[conn] = player_num
        else:
            player_num = client_players[conn]
    
    print(f"Conexão aceita de {addr} - Jogador {player_num}")
    
    try:
        for line in get_lines(conn):
            if line.strip():
                try:
                    # Parse do JSON do PlayerInput
                    input_data = json_string_to_dict(line.strip())
                    player_input = PlayerInput(direction=input_data.get('direction', 0))
                    
                    # Atualizar input do jogador correspondente
                    with mutex:
                        if player_num == 1:
                            p1_input = player_input
                        elif player_num == 2:
                            p2_input = player_input
                    
                    print(f"Jogador {player_num} input: {player_input.direction}")
                    
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Erro ao processar input de {addr}: {e}")
                    
    except Exception as e:
        print(f"Erro ao lidar com {addr}: {e}")
    finally:
        # Remover cliente da lista
        if conn in clients:
            clients.remove(conn)
        if conn in client_players:
            with mutex:
                del client_players[conn]
        conn.close()
        print(f"Conexão com {addr} fechada")

def dict_to_json_string(data: dict) -> str:
    return json.dumps(data, ensure_ascii=False, indent=4)

def json_string_to_dict(json_str: str) -> dict:
    return json.loads(json_str)

def reset_ball():
    """Reinicia a bola no centro indo para a direita"""
    return WIDTH//2, HEIGHT//2, BALL_SPEED, 0

def check_paddle_collision(ball_x, ball_y, ball_vx, ball_vy, paddle_x, paddle_y):
    """Verifica colisão da bola com paddle e retorna nova velocidade"""
    # Verificar se a bola está na área do paddle
    if (ball_x - BALL_SIZE//2 <= paddle_x + PADDLE_WIDTH//2 and 
        ball_x + BALL_SIZE//2 >= paddle_x - PADDLE_WIDTH//2 and
        ball_y - BALL_SIZE//2 <= paddle_y + PADDLE_HEIGHT//2 and
        ball_y + BALL_SIZE//2 >= paddle_y - PADDLE_HEIGHT//2):
        
        # Calcular onde na paddle a bola bateu (de -1 a 1)
        relative_intersect_y = (ball_y - paddle_y) / (PADDLE_HEIGHT//2)
        
        # Limitar entre -1 e 1
        relative_intersect_y = max(-1, min(1, relative_intersect_y))
        
        # Calcular ângulo baseado na posição do impacto
        bounce_angle = relative_intersect_y * (math.pi / 4)  # Max 45 graus
        
        # Nova velocidade baseada no ângulo - garante que a bola vá na direção oposta
        speed = BALL_SPEED  # Usar velocidade constante
        new_vx = speed * math.cos(bounce_angle) * (-1 if ball_vx > 0 else 1)
        new_vy = speed * math.sin(bounce_angle)
        
        print(f"Colisão! Ângulo: {bounce_angle:.2f}, Nova velocidade: ({new_vx:.2f}, {new_vy:.2f})")
        
        return True, new_vx, new_vy
    
    return False, ball_vx, ball_vy

def game_loop():
    global game_state, p1_input, p2_input
    
    PADDLE_SPEED = 5
    
    while True:
        start = time.perf_counter()

        with mutex:
            # Verificar se o jogo deve começar
            game_should_start = len(client_players) >= 2
            
            # Se o jogo não começou ainda, mas deve começar
            if not game_state.game_started and game_should_start:
                ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                game_state = game_state._replace(
                    ballx=ball_x, bally=ball_y, ballvx=ball_vx, ballvy=ball_vy, 
                    game_started=True
                )
                print("Jogo iniciado! 2 jogadores conectados.")
            
            # Se o jogo parou (menos de 2 jogadores)
            elif game_state.game_started and not game_should_start:
                game_state = game_state._replace(
                    ballvx=0, ballvy=0, game_started=False
                )
                print("Jogo pausado. Aguardando 2 jogadores.")
            
            # Atualizar posições dos jogadores
            new_p1y = game_state.p1y + (p1_input.direction * PADDLE_SPEED)
            new_p1y = max(PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p1y))
            
            new_p2y = game_state.p2y + (p2_input.direction * PADDLE_SPEED)
            new_p2y = max(PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p2y))
            
            # Atualizar física da bola (apenas se o jogo começou)
            ball_x, ball_y = game_state.ballx, game_state.bally
            ball_vx, ball_vy = game_state.ballvx, game_state.ballvy
            score1, score2 = game_state.score1, game_state.score2
            
            if game_state.game_started:
                # Mover bola
                ball_x += ball_vx
                ball_y += ball_vy
                
                # Colisão com paredes superior e inferior
                if ball_y <= BALL_SIZE//2:
                    ball_vy = abs(ball_vy)  # Força para baixo
                    ball_y = BALL_SIZE//2
                elif ball_y >= HEIGHT - BALL_SIZE//2:
                    ball_vy = -abs(ball_vy)  # Força para cima
                    ball_y = HEIGHT - BALL_SIZE//2
                
                # Verificar gols (bola entra nos gols)
                # Gol esquerdo (Jogador 2 marca)
                if ball_x <= GOAL_WIDTH and GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT:
                    score2 += 1
                    ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                    print(f"Gol do Jogador 2! Placar: {score1} x {score2}")
                
                # Gol direito (Jogador 1 marca)
                elif ball_x >= WIDTH - GOAL_WIDTH and GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT:
                    score1 += 1
                    ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                    print(f"Gol do Jogador 1! Placar: {score1} x {score2}")
                
                # Colisão com paredes dos gols (bola bate na lateral do gol)
                elif ball_x <= GOAL_WIDTH and (ball_y < GOAL_Y or ball_y > GOAL_Y + GOAL_HEIGHT):
                    ball_vx = abs(ball_vx)  # Rebate para a direita
                    ball_x = GOAL_WIDTH + BALL_SIZE//2
                
                elif ball_x >= WIDTH - GOAL_WIDTH and (ball_y < GOAL_Y or ball_y > GOAL_Y + GOAL_HEIGHT):
                    ball_vx = -abs(ball_vx)  # Rebate para a esquerda  
                    ball_x = WIDTH - GOAL_WIDTH - BALL_SIZE//2
                
                # Colisão com paddle esquerdo (Jogador 1)
                elif ball_vx < 0 and ball_x <= PADDLE_DISTANCE_FROM_GOAL + PADDLE_WIDTH//2 + BALL_SIZE//2:
                    collision, ball_vx, ball_vy = check_paddle_collision(
                        ball_x, ball_y, ball_vx, ball_vy, PADDLE_DISTANCE_FROM_GOAL, new_p1y
                    )
                    if collision:
                        ball_x = PADDLE_DISTANCE_FROM_GOAL + PADDLE_WIDTH//2 + BALL_SIZE//2
                
                # Colisão com paddle direito (Jogador 2)
                elif ball_vx > 0 and ball_x >= WIDTH - PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2 - BALL_SIZE//2:
                    collision, ball_vx, ball_vy = check_paddle_collision(
                        ball_x, ball_y, ball_vx, ball_vy, WIDTH - PADDLE_DISTANCE_FROM_GOAL, new_p2y
                    )
                    if collision:
                        ball_x = WIDTH - PADDLE_DISTANCE_FROM_GOAL - PADDLE_WIDTH//2 - BALL_SIZE//2
                
                # Verificação de segurança - se a bola escapou dos limites
                if ball_x < -BALL_SIZE or ball_x > WIDTH + BALL_SIZE:
                    print(f"ERRO: Bola escapou! Posição: ({ball_x}, {ball_y})")
                    ball_x, ball_y, ball_vx, ball_vy = reset_ball()

            game_state = GameState(
                p1y=new_p1y,
                p2y=new_p2y,
                ballx=ball_x,
                bally=ball_y,
                ballvx=ball_vx,
                ballvy=ball_vy,
                score1=score1,
                score2=score2,
                game_started=game_state.game_started
            )

        # Broadcast game_sstate
        msg = dict_to_json_string(game_state._asdict())
        disconnected_clients = []
        
        for conn in clients:
            try:
                conn.sendall((msg + "\n").encode())
            except Exception as e:
                print(f"Erro ao enviar dados para cliente: {e}")
                disconnected_clients.append(conn)
        
        # Remover clientes desconectados
        for conn in disconnected_clients:
            if conn in clients:
                clients.remove(conn)
            if conn in client_players:
                with mutex:
                    del client_players[conn]

        elapsed = time.perf_counter() - start
        time.sleep(max(0, TICK - elapsed))

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, porta))
        s.listen()
        print(f"Observando TCP na porta :{porta}")
        print("Aguardando 2 jogadores para iniciar o jogo...")

        threading.Thread(target=game_loop, daemon=True).start()

        while True:
            conn, addr = s.accept()
            clients.append(conn)
            # cada cliente em thread separada
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
