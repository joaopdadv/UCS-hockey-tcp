import socket
import threading
import sys

if len(sys.argv) != 2:
    print(f"Uso: python {sys.argv[0]} <port>")
    sys.exit(1)

host = ''
porta = int(sys.argv[1])

BUFFER_SIZE = 8


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
    print(f"Conexão aceita de {addr}")
    try:
        for line in get_lines(conn):
            print(line)
    except Exception as e:
        print(f"Erro ao lidar com {addr}: {e}")
    finally:
        conn.close()
        print(f"Conexão com {addr} fechada")


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, porta))
        s.listen()
        print(f"Observando TCP na porta :{porta}")

        while True:
            conn, addr = s.accept()
            # cada cliente em thread separada
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()


if __name__ == "__main__":
    main()
