import socket 
import sys
import struct
    
#------------------------------------------------------------------
if  ( len(sys.argv) != 2 ):
	print('%s <porta>' % sys.argv[0])
	sys.exit(0)
	
ip = ''
porta = int(sys.argv[1])

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((ip, porta)) 
sock.listen(10)

try:
    while True:
            conn, cliente = sock.accept()
            print("Conexão de", cliente)
            try:
                while True:
                    dados = conn.recv(4)
                    if dados is None:
                        break
                    n = struct.unpack('!I', dados)[0]
                    print(n)
            finally:
                conn.close()
except KeyboardInterrupt:
    print("\nCtrl + C detectado.")
finally:
    sock.close()
    print("Servidor encerrado.")
