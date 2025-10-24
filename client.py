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

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
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
