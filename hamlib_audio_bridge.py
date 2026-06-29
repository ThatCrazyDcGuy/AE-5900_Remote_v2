# =========================================================================
# From DIGI-TOOLS to hamlib-rigctltd & mumble to mumble audio bot.
#
# Create a null sink for your mumble and digi tool:
# pactl load-module module-null-sink
#
# =========================================================================
import eventlet
eventlet.monkey_patch()

import socket
import threading
import urllib.request
import time
import subprocess
import pymumble_py3 as pymumble

# --- KONFIGURATION ---
HAMLIB_PORT = 4532          
REAL_HAMLIB_PORT = 4533     
API_URL = "http://127.0.0.1:5000/api/cmd/TX"

MUMBLE_HOST = "127.0.0.1"
MUMBLE_PORT = 64738
BOT_NAME = "AE5900_Digi_Bot"

mumble_client = None

def start_real_hamlib():
    try:
        subprocess.Popen([
            "rigctld", "-m", "1", "-t", str(REAL_HAMLIB_PORT), "-T", "127.0.0.1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"[BRÜCKE 1] Echtes Hamlib-Dummy-Rig auf Port {REAL_HAMLIB_PORT} gestartet.")
    except Exception as e:
        print(f"[WARNUNG] rigctld Start-Check: {e}")

def trigger_ptt(state):
    try:
        url = f"{API_URL}?state={state}"
        with urllib.request.urlopen(url, timeout=1) as response:
            response.read()
        print(f"[ALBRECHT API] PTT -> state={state}")
    except Exception as e:
        print(f"[API ERROR] {e}")

def init_mumble_bot():
    global mumble_client
    try:
        print(f"[MUMBLE] Starte Bot '{BOT_NAME}' via Eventlet-Bypass...")
        mumble_client = pymumble.Mumble(MUMBLE_HOST, BOT_NAME, port=MUMBLE_PORT)
        mumble_client.set_receive_sound(1)
        mumble_client.start()
        mumble_client.is_ready()
        
        if len(mumble_client.channels) > 1:
            target_channel = list(mumble_client.channels.values())[1]
            target_channel.move_in()
            print(f"[MUMBLE] Bot erfolgreich in Funk-Kanal verschoben.")
        print("=== MUMBLE BOT ONLINE UND LAUSCHT BEREIT ===")
    except Exception as e:
        print(f"[MUMBLE ERROR] Bot-Verbindung fehlgeschlagen: {e}")

def forward_to_real_hamlib(command):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", REAL_HAMLIB_PORT))
        s.sendall(command.encode('utf-8'))
        response = s.recv(4096)
        s.close()
        return response
    except Exception:
        return b"RPRT -1\n"

def handle_client(client_socket):
    client_socket.settimeout(10.0)
    buffer = ""
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8', errors='ignore')
            if not data: break
            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                cmd = line.strip()
                if not cmd: continue
                
                clean_cmd = cmd.lstrip('+').strip()
                if clean_cmd.startswith('T') or clean_cmd.startswith('\\set_ptt'):
                    parts = clean_cmd.split()
                    state = parts[1] if len(parts) > 1 else '0'
                    if state == '1':
                        print("[DOPPELBRÜCKE] ---> PTT TX ON!")
                        trigger_ptt(1)
                    else:
                        print("[DOPPELBRÜCKE] <--- PTT TX OFF!")
                        trigger_ptt(0)
                    response = forward_to_real_hamlib(line + "\n")
                    client_socket.sendall(response)
                else:
                    response = forward_to_real_hamlib(line + "\n")
                    client_socket.sendall(response)
        except socket.timeout:
            continue
        except Exception:
            break
    client_socket.close()

def start_server():
    start_real_hamlib()
    time.sleep(1)
    
    # Bot asynchron via eventlet starten, damit er perfekt ins System flutscht
    eventlet.spawn(init_mumble_bot)
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", HAMLIB_PORT))
    server.listen(5)
    print(f"=== SPERRFREIER COMBINED CAT PROXY ON PORT {HAMLIB_PORT} ===")
    
    while True:
        try:
            client_sock, addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock,), daemon=True).start()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    start_server()
