import time
import serial
import sys
import select

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'  
BAUDRATE = 115200       
TIMEOUT = 0.1

# HIER DIE CODES EINTRAGEN, DIE ÜBERSPRUNGEN WERDEN SOLLEN:
IGNORE_KEYS = [0x1F, 0x1A, 0x1B, 0x1C, 0x1D, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06 ,0x07, 0x08, 0x09, 0x0A] 
# ---------------------

try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    print(f"[*] Verbindung zu {SERIAL_PORT} hergestellt.")
except Exception as e:
    print(f"[!] Fehler beim Öffnen des Ports: {e}")
    print("[?] Hinweis: Nutzen Sie 'ls /dev/ttyUSB*' um Ihren Port zu finden.")
    sys.exit()

print("[*] Bruteforce gestartet.")
ignore_str = ", ".join(f"0x{k:02X}" for k in IGNORE_KEYS)
print(f"[*] Ignorierte Tasten-IDs: [{ignore_str}]")
print("[*] Ablauf pro ID: DRÜCKEN -> 200ms warten -> LOSLASSEN -> 800ms warten.")
print("[*] Steuerung: Drücken Sie [ENTER] im Terminal, um zu PAUSIEREN / FORTZUSETZEN.")
print("[*] Beenden: Drücken Sie [STRG] + [C]\n")

is_paused = False
current_key_id = 0x00

def check_interruption():
    """Prüft, ob der Nutzer im Terminal ENTER gedrückt hat (nicht blockierend)"""
    if select.select([sys.stdin], [], [], 0)[0]:
        sys.stdin.readline() # Puffer leeren
        return True
    return False

try:
    while current_key_id <= 0xFF:
        # Prüfen, ob der Benutzer ENTER gedrückt hat, um zu pausieren
        if check_interruption():
            is_paused = not is_paused
            if is_paused:
                print(f"\n[||] PAUSE bei Tasten-ID: 0x{current_key_id:02X} (Dezimal: {current_key_id})")
                print("[*] Drücken Sie erneut [ENTER] zum Weiterlaufen...\n")
            else:
                print("[>] RESTART...")

        if is_paused:
            time.sleep(0.2)
            continue

        # --- NEU: Prüfen, ob die aktuelle ID ignoriert werden soll ---
        if current_key_id in IGNORE_KEYS:
            print(f"[INFO] Überspringe fehlerhafte ID: 0x{current_key_id:02X}")
            current_key_id += 1
            continue
        # -------------------------------------------------------------

        # 1. SCHRITT: Taste DRÜCKEN (3. Byte = 01)
#        packet_press = bytearray([0x41, 0x00, 0x00, 0x00, current_key_id, 0x00, 0x00, 0x06])
        packet_press = bytearray([0x41, 0x00, 0x01, 0x00, current_key_id, 0x00, 0x00, 0x06])
        hex_press = " ".join(f"{b:02X}" for b in packet_press)
        print(f"[TX] ID 0x{current_key_id:02X} -> DRÜCKEN:   {hex_press}")
        
        ser.write(packet_press)
        time.sleep(0.2)
        
        # Antwort prüfen
        if ser.in_waiting > 0:
            res = ser.read(ser.in_waiting)
            print(f"    [RX Antwort (Gedrückt)] <- {' '.join(f'{b:02X}' for b in res)}")

        # 2. SCHRITT: Taste LOSLASSEN (3. Byte = 00)
        packet_release = bytearray([0x41, 0x00, 0x00, 0x00, current_key_id, 0x00, 0x00, 0x06])
        hex_release = " ".join(f"{b:02X}" for b in packet_release)
        print(f"                       -> LOSLASSEN: {hex_release}")
        
        ser.write(packet_release)
        
        # Antwort prüfen
        time.sleep(0.1)
        if ser.in_waiting > 0:
            res = ser.read(ser.in_waiting)
            print(f"    [RX Antwort (Losgelassen)] <- {' '.join(f'{b:02X}' for b in res)}")

        # Pause bis zur nächsten Sekunde
        time.sleep(0.7)
        current_key_id += 1

    print("\n[*] Alle Tasten-IDs (0x00 bis 0xFF) wurden simuliert.")

except KeyboardInterrupt:
    print("\n[!] Programm per STRG+C abgebrochen.")

finally:
    ser.close()
    print("[*] COM-Port geschlossen.")
