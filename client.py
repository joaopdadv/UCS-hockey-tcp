import json
import socket
import sys

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
    return json.dumps(data, ensure_ascii=False, indent=4)

def json_string_to_dict(json_str: str) -> dict:
    return json.loads(json_str)


# TODO: enviar json com dados do jogador na conexão
# TODO: capturar movimento
# TODO: receber json com estado do jogo
# TODO: Renderizar frame

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))
print(f"Conectado ao servidor {host}:{port}")

try:
    while True:
        msg = input("> ")  # lê mensagem do teclado
        if not msg:
            continue
        s.sendall((msg + "\n").encode("utf-8"))  # envia com quebra de linha
        if msg.lower() in ("exit", "quit"):
            break
except KeyboardInterrupt:
    pass

print("Cliente encerrado.")
