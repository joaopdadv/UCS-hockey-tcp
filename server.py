import json
import socket
import threading
import sys
from collections import namedtuple
import time
from config import TICK, GameState, PlayerInput, HEIGHT



clients = []
client_players = {}  # mapeia conexão para número do jogador (1 ou 2)
game_state = GameState(p1y=HEIGHT//2, p2y=HEIGHT//2, ballx=400, bally=300, score1=0, score2=0)
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

def game_loop():
    global game_state, p1_input, p2_input
    
    PADDLE_SPEED = 5
    PADDLE_HEIGHT = 80
    
    while True:
        start = time.perf_counter()

        with mutex:
            # jogador 1
            new_p1y = game_state.p1y + (p1_input.direction * PADDLE_SPEED)
            new_p1y = max(PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p1y))
            
            # jogador 2
            new_p2y = game_state.p2y + (p2_input.direction * PADDLE_SPEED)
            new_p2y = max(PADDLE_HEIGHT//2, min(HEIGHT - PADDLE_HEIGHT//2, new_p2y))

            game_state = GameState(
                p1y=new_p1y,
                p2y=new_p2y,
                ballx=game_state.ballx,
                bally=game_state.bally,
                score1=game_state.score1,
                score2=game_state.score2,
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

        threading.Thread(target=game_loop, daemon=True).start()

        while True:
            conn, addr = s.accept()
            clients.append(conn)
            # cada cliente em thread separada
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
