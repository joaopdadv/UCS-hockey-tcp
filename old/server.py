import json
import socket
import threading
import sys
from collections import namedtuple
import time
from config import (
    TICK, GameState, PlayerInput, HEIGHT, WIDTH,
    PADDLE_WIDTH, PADDLE_HEIGHT, BALL_SIZE, BALL_SPEED,
    GOAL_HEIGHT, GOAL_Y, PADDLE_DISTANCE_FROM_GOAL,
    HUD_HEIGHT, GOAL_INSET, GOAL_BAR_LENGTH, GOAL_THICKNESS, TIME_LIMIT_SECONDS
)
import math

clients = []
client_players = {}  # mapeia conexão para número do jogador (1 ou 2)

# Posições iniciais (centradas no campo útil)
FIELD_CENTER_Y = HUD_HEIGHT + (HEIGHT - HUD_HEIGHT) // 2

game_state = GameState(
    p1y=FIELD_CENTER_Y,
    p2y=FIELD_CENTER_Y,
    ballx=WIDTH//2, bally=FIELD_CENTER_Y,
    ballvx=0, ballvy=0,
    score1=0, score2=0,
    game_started=False,
    time_left=TIME_LIMIT_SECONDS,
    game_over=False,
    winner=0
)

p1_input = PlayerInput(direction=0)
p2_input = PlayerInput(direction=0)
mutex = threading.Lock()

if len(sys.argv) != 2:
    print(f"Uso: python {sys.argv[0]} <port>")
    sys.exit(1)

host = ''
porta = int(sys.argv[1])

BUFFER_SIZE = 2048

# ------------------ Util ------------------

def get_lines(conn):
    """Monta linhas completas a partir do socket (delimitadas por \\n)."""
    current_line = ""
    while True:
        data = conn.recv(BUFFER_SIZE) 
        if not data:
            if current_line:
                yield current_line
            break

        decoded = data.decode("utf-8", errors="ignore")
        parts = decoded.split("\\n")

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
            if not line:
                continue
            try:
                input_data = json.loads(line.strip())
                direction = int(input_data.get('direction', 0))
                player_input = PlayerInput(direction=direction)
                with mutex:
                    if player_num == 1:
                        p1_input = player_input
                    elif player_num == 2:
                        p2_input = player_input
            except Exception as e:
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
    return json.dumps(data, ensure_ascii=False, separators=(',', ':'))

def reset_ball():
    """Reinicia a bola no centro indo para a direita."""
    return WIDTH//2, FIELD_CENTER_Y, BALL_SPEED, 0.0

def check_paddle_collision(ball_x, ball_y, ball_vx, ball_vy, paddle_x, paddle_y):
    """Verifica colisão da bola com paddle e retorna nova velocidade (com ângulo)."""
    if (ball_x - BALL_SIZE//2 <= paddle_x + PADDLE_WIDTH//2 and 
        ball_x + BALL_SIZE//2 >= paddle_x - PADDLE_WIDTH//2 and
        ball_y - BALL_SIZE//2 <= paddle_y + PADDLE_HEIGHT//2 and
        ball_y + BALL_SIZE//2 >= paddle_y - PADDLE_HEIGHT//2):
        
        # Onde bateu (-1..1)
        relative_intersect_y = (ball_y - paddle_y) / (PADDLE_HEIGHT//2)
        relative_intersect_y = max(-1.0, min(1.0, relative_intersect_y))
        
        bounce_angle = relative_intersect_y * (math.pi / 4)  # até 45º
        
        speed = float(BALL_SPEED)
        new_vx = speed * math.cos(bounce_angle) * (-1 if ball_vx > 0 else 1)
        new_vy = speed * math.sin(bounce_angle)
        
        # Reposiciona a bola para não "colar"
        if new_vx > 0:
            ball_x = paddle_x + PADDLE_WIDTH//2 + BALL_SIZE//2
        else:
            ball_x = paddle_x - PADDLE_WIDTH//2 - BALL_SIZE//2
        
        return True, ball_x, new_vx, new_vy
    
    return False, ball_x, ball_vx, ball_vy

# ------------------ Loop do jogo ------------------

def game_loop():
    global game_state, p1_input, p2_input
    
    PADDLE_SPEED = 5
    last_tick_time = time.perf_counter()

    while True:
        start = time.perf_counter()
        now = start
        dt = now - last_tick_time
        last_tick_time = now

        with mutex:
            # Controle de início/parada
            game_should_start = (len(client_players) >= 2) and (not game_state.game_over)
            
            # Se deve começar e ainda não começou
            if not game_state.game_started and game_should_start:
                ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                game_state = game_state._replace(
                    ballx=ball_x, bally=ball_y, ballvx=ball_vx, ballvy=ball_vy, 
                    game_started=True
                )
                print("Jogo iniciado! 2 jogadores conectados.")
            
            # Se estava rolando e parou (falta jogador) — apenas se não acabou
            elif game_state.game_started and (not game_should_start) and (not game_state.game_over):
                game_state = game_state._replace(
                    ballvx=0.0, ballvy=0.0, game_started=False
                )
                print("Jogo pausado. Aguardando 2 jogadores.")

            # Atualizar posições dos jogadores
            new_p1y = game_state.p1y + (p1_input.direction * PADDLE_SPEED)
            new_p1y = max(HUD_HEIGHT + PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p1y))
            
            new_p2y = game_state.p2y + (p2_input.direction * PADDLE_SPEED)
            new_p2y = max(HUD_HEIGHT + PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p2y))
            
            # Atualizar física da bola
            ball_x, ball_y = game_state.ballx, game_state.bally
            ball_vx, ball_vy = game_state.ballvx, game_state.ballvy
            score1, score2 = game_state.score1, game_state.score2
            time_left = game_state.time_left
            game_over = game_state.game_over
            winner = game_state.winner
            
            if game_state.game_started and not game_over:
                # cronômetro (contagem regressiva só enquanto rola)
                time_left = max(0.0, time_left - dt)
                if time_left <= 0.0 and not game_over:
                    game_over = True
                    # decide vencedor
                    if score1 > score2:
                        winner = 1
                    elif score2 > score1:
                        winner = 2
                    else:
                        winner = 0
                    ball_vx = 0.0
                    ball_vy = 0.0
                    print("Fim de jogo!")

                # Mover bola
                if not game_over:
                    ball_x += ball_vx
                    ball_y += ball_vy
                    
                    # Colisão com teto (topo do campo é HUD_HEIGHT) e chão
                    if ball_y <= HUD_HEIGHT + BALL_SIZE//2:
                        ball_vy = abs(ball_vy)
                        ball_y = HUD_HEIGHT + BALL_SIZE//2
                    elif ball_y >= HEIGHT - BALL_SIZE//2:
                        ball_vy = -abs(ball_vy)
                        ball_y = HEIGHT - BALL_SIZE//2
                    
                    # ---------- Gols em C (lógica com espessura e rebate externo) ----------
                    HALF_TH = GOAL_THICKNESS / 2.0
                    HALF_B = BALL_SIZE / 2.0
                    
                    TOP_BAR_Y = GOAL_Y
                    BOT_BAR_Y = GOAL_Y + GOAL_HEIGHT

                    # 1) Verificação de GOL
                    if ball_x - HALF_B <= GOAL_INSET and GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT:
                        # Gol do Jogador 2 (direita)
                        score2 += 1
                        ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                        print(f"Gol do Jogador 2! Placar: {score1} x {score2}")
                    elif ball_x + HALF_B >= WIDTH - GOAL_INSET and GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT:
                        # Gol do Jogador 1 (esquerda)
                        score1 += 1
                        ball_x, ball_y, ball_vx, ball_vy = reset_ball()
                        print(f"Gol do Jogador 1! Placar: {score1} x {score2}")
                    else:
                        # 2) Rebate nas HASTES VERTICAIS (traves), por fora/por dentro (fora da boca)
                        if (ball_x - HALF_B) <= (GOAL_INSET + HALF_TH) and not (GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT):
                            ball_vx = abs(ball_vx)
                            ball_x = GOAL_INSET + HALF_TH + HALF_B
                        if (ball_x + HALF_B) >= (WIDTH - GOAL_INSET - HALF_TH) and not (GOAL_Y <= ball_y <= GOAL_Y + GOAL_HEIGHT):
                            ball_vx = -abs(ball_vx)
                            ball_x = WIDTH - GOAL_INSET - HALF_TH - HALF_B
                        
                        # 3) Rebate nas BARRAS SUPERIOR/INFERIOR do "C" (ambos os lados)
                        if (GOAL_INSET - HALF_TH) <= ball_x <= (GOAL_INSET + GOAL_BAR_LENGTH + HALF_TH):
                            # Topo esquerdo
                            if abs(ball_y - TOP_BAR_Y) <= (HALF_TH + HALF_B):
                                if ball_y <= TOP_BAR_Y:
                                    ball_vy = -abs(ball_vy)
                                    ball_y = TOP_BAR_Y - HALF_TH - HALF_B
                                else:
                                    ball_vy = abs(ball_vy)
                                    ball_y = TOP_BAR_Y + HALF_TH + HALF_B
                            # Fundo esquerdo
                            if abs(ball_y - BOT_BAR_Y) <= (HALF_TH + HALF_B):
                                if ball_y <= BOT_BAR_Y:
                                    ball_vy = -abs(ball_vy)
                                    ball_y = BOT_BAR_Y - HALF_TH - HALF_B
                                else:
                                    ball_vy = abs(ball_vy)
                                    ball_y = BOT_BAR_Y + HALF_TH + HALF_B
                        
                        if (WIDTH - GOAL_INSET - GOAL_BAR_LENGTH - HALF_TH) <= ball_x <= (WIDTH - GOAL_INSET + HALF_TH):
                            if abs(ball_y - TOP_BAR_Y) <= (HALF_TH + HALF_B):
                                if ball_y <= TOP_BAR_Y:
                                    ball_vy = -abs(ball_vy)
                                    ball_y = TOP_BAR_Y - HALF_TH - HALF_B
                                else:
                                    ball_vy = abs(ball_vy)
                                    ball_y = TOP_BAR_Y + HALF_TH + HALF_B
                            if abs(ball_y - BOT_BAR_Y) <= (HALF_TH + HALF_B):
                                if ball_y <= BOT_BAR_Y:
                                    ball_vy = -abs(ball_vy)
                                    ball_y = BOT_BAR_Y - HALF_TH - HALF_B
                                else:
                                    ball_vy = abs(ball_vy)
                                    ball_y = BOT_BAR_Y + HALF_TH + HALF_B

                    # 4) Colisão com PADDLES (sempre verificar ambos)
                    _c, ball_x, ball_vx, ball_vy = check_paddle_collision(
                        ball_x, ball_y, ball_vx, ball_vy, PADDLE_DISTANCE_FROM_GOAL, new_p1y
                    )
                    _c, ball_x, ball_vx, ball_vy = check_paddle_collision(
                        ball_x, ball_y, ball_vx, ball_vy, WIDTH - PADDLE_DISTANCE_FROM_GOAL, new_p2y
                    )
                    
                    # Segurança: se sair da tela por algum bug, reseta
                    if ball_x < -BALL_SIZE or ball_x > WIDTH + BALL_SIZE:
                        ball_x, ball_y, ball_vx, ball_vy = reset_ball()

            # Commit do estado
            game_state = GameState(
                p1y=new_p1y,
                p2y=new_p2y,
                ballx=ball_x,
                bally=ball_y,
                ballvx=ball_vx,
                ballvy=ball_vy,
                score1=score1,
                score2=score2,
                game_started=game_state.game_started if game_over else game_state.game_started,
                time_left=time_left,
                game_over=game_over,
                winner=winner
            )

        # Broadcast game_state
        msg = dict_to_json_string(game_state._asdict())
        disconnected_clients = []
        
        for conn in clients:
            try:
                conn.sendall((msg + "\\n").encode("utf-8"))
            except Exception as e:
                # desconectar silenciosamente
                disconnected_clients.append(conn)
        
        # Remover clientes desconectados
        for conn in disconnected_clients:
            if conn in clients:
                clients.remove(conn)
            if conn in client_players:
                with mutex:
                    del client_players[conn]

        elapsed = time.perf_counter() - start
        sleep_time = max(0.0, TICK - elapsed)
        time.sleep(sleep_time)

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, porta))
        s.listen()
        print(f"Observando TCP na porta :{porta}")
        print("Aguardando 2 jogadores para iniciar o jogo...")

        threading.Thread(target=game_loop, daemon=True).start()

        while True:
            conn, addr = s.accept()
            clients.append(conn)
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()