import time
import serial
import sys

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'  
BAUDRATE = 115200       
TIMEOUT = 0.5  
PAUSE_BETWEEN_KEYS = 0.3  # Pause in Sekunden zwischen den einzelnen Tasten einer Kette
# ---------------------

try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    print(f"[*] Verbindung zu {SERIAL_PORT} hergestellt.")
except Exception as e:
    print(f"[!] Fehler beim Öffnen des Ports: {e}")
    sys.exit()

print("\n=== INTERAKTIVER SEQUENZ-TESTER ===")
print("[*] Einzeltaste eingeben (z. B. '24') ODER eine Kette mit Kommas (z. B. '24, 12, 12, 13').")
print("[*] Hex (mit/ohne 0x) und Dezimal sind gemischt erlaubt.")
print("[*] Tippen Sie 'exit' oder 'q' zum Beenden.\n")

try:
    while True:
        user_input = input("Sequenz eingeben > ").strip()

        if user_input.lower() in ['exit', 'q']:
            print("[*] Programm wird beendet.")
            break
        
        if not user_input:
            continue

        # Eingabe bei Kommas aufteilen und Leerzeichen entfernen
        raw_parts = [part.strip() for part in user_input.split(',')]
        key_sequence = []
        valid = True

        # Alle Teile der Kette parsen
        for part in raw_parts:
            if not part:
                continue
            try:
                if part.lower().startswith('0x'):
                    key_id = int(part, 16)
                elif len(part) == 2 and all(c in '0123456789abcdefABCDEF' for c in part):
                    key_id = int(part, 16)
                else:
                    key_id = int(part)

                if 0 <= key_id <= 255:
                    key_sequence.append(key_id)
                else:
                    print(f"[!] Fehler: Wert '{part}' liegt ausserhalb von 0x00 - 0xFF.")
                    valid = False
                    break
            except ValueError:
                print(f"[!] Fehler: Ungültiges Format bei '{part}'.")
                valid = False
                break

        if not valid or not key_sequence:
            continue

        print(f"--> Starte Sequenz mit {len(key_sequence)} Tasten...")

        # Die Kette Taste für Taste abarbeiten
        for idx, key_id in enumerate(key_sequence):
            print(f"   [{idx+1}/{len(key_sequence)}] Taste 0x{key_id:02X} (Dezimal: {key_id})")

            # 1. SCHRITT: Taste DRÜCKEN
#            packet_press = bytearray([0x41, 0x00, 0x00, 0x00, key_id, 0x00, 0x00, 0x06])
            packet_press = bytearray([0x41, 0x00, 0x01, 0x00, key_id, 0x00, 0x00, 0x06])
            ser.write(packet_press)
            time.sleep(0.15)  # Kurze Haltezeit der Taste

            # Antwort beim Drücken prüfen
            if ser.in_waiting > 0:
                res = ser.read(ser.in_waiting)
                print(f"       [RX Gedrückt] <- {' '.join(f'{b:02X}' for b in res)}")

            # 2. SCHRITT: Taste LOSLASSEN
            packet_release = bytearray([0x41, 0x00, 0x00, 0x00, key_id, 0x00, 0x00, 0x06])
            ser.write(packet_release)
            time.sleep(0.05)

            # Antwort beim Loslassen prüfen
            if ser.in_waiting > 0:
                res = ser.read(ser.in_waiting)
                print(f"       [RX Losgelassen] <- {' '.join(f'{b:02X}' for b in res)}")

            # Pause vor der nächsten Taste in der Kette (ausser es war die letzte)
            if idx < len(key_sequence) - 1:
                time.sleep(PAUSE_BETWEEN_KEYS)
        
        print("[*] Sequenz abgeschlossen.\n")

except KeyboardInterrupt:
    print("\n[!] Programm abgebrochen.")

finally:
    ser.close()
    print("[*] COM-Port geschlossen.")
