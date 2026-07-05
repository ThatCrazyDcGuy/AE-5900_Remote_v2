# =========================================================================
# AE5900 PURE AUDIO GATEWAY & MUMBLE BOT
# =========================================================================
import eventlet
eventlet.monkey_patch()

import time
import pymumble_py3 as pymumble

# --- CONFIGURATION ---
MUMBLE_HOST = "127.0.0.1"
MUMBLE_PORT = 64738
BOT_NAME = "AE5900_Digi_Bot"

mumble_client = None

def init_mumble_bot():
    global mumble_client
    try:
        print(f"[MUMBLE] Starte Audio-Bot '{BOT_NAME}' via Eventlet-Bypass...")
        mumble_client = pymumble.Mumble(MUMBLE_HOST, BOT_NAME, port=MUMBLE_PORT)
        mumble_client.set_receive_sound(1)
        mumble_client.start()
        mumble_client.is_ready()
        
        if len(mumble_client.channels) > 1:
            target_channel = list(mumble_client.channels.values())[1]
            target_channel.move_in()
            print(f"[MUMBLE] Bot erfolgreich in Funk-Kanal verschoben.")
        print("=== MUMBLE BOT ONLINE UND AUDIO-READY ===")
    except Exception as e:
        print(f"[MUMBLE ERROR] Bot-Verbindung fehlgeschlagen: {e}")

if __name__ == "__main__":
    # Zündet exklusiv den Mumble-Audio-Client
    init_mumble_bot()
    
    # Hält das Skript lebendig
    while True:
        eventlet.sleep(1)
