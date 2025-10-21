import socket
import sys
import struct
import sys, tty, termios

# Função escrita por IA para ler teclas no terminal
def read_key():
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    try:
        tty.setraw(fd)
        ch1 = sys.stdin.buffer.read(1)
        if not ch1:
            return None
        if ch1 == b"\x03":  # Ctrl+C
            raise KeyboardInterrupt
        if ch1 in (b"q", b"Q"):
            return "QUIT"
        if ch1 == b"\x1b":
            ch2 = sys.stdin.buffer.read(1)
            if ch2 != b"[":
                return None
            ch3 = sys.stdin.buffer.read(1)
            if ch3 == b"A":
                return "UP"
            if ch3 == b"B":
                return "DOWN"
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)

if len(sys.argv) != 3:
    print(f"{sys.argv[0]} <ip> <porta>")
    sys.exit(1)

ip = sys.argv[1]
porta = int(sys.argv[2])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((ip, porta))
print("Conectado. Use as setas ↑/↓. Tecle 'q' para sair.")

try:
    while True:
        k = read_key()
        if k is None:
            continue
        if k == "QUIT":
            break
        n = 1 if k == "UP" else 0
        sock.sendall(struct.pack("!I", n))
except KeyboardInterrupt:
    print("Ctrl + C detectado.")
finally:
    sock.close()
    print("Cliente encerrado.")
