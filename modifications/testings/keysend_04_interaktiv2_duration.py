import time
import serial
import sys

# --- KONFIGURATION ---
SERIAL_PORT = '/dev/ttyUSB0'  
BAUDRATE = 115200       
TIMEOUT = 0.5  
PAUSE_BETWEEN_KEYS = 0.3  # Pause zwischen den Tasten einer Kette
DEFAULT_SHORT_PRESS = 0.15 # Haltedauer für Short-Press (150ms)
DEFAULT_LONG_PRESS = 2.0   # Haltedauer bei ":L" (2 Sekunden)
# ---------------------

try:
    ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=TIMEOUT)
    print(f"[*] Verbindung zu {SERIAL_PORT} hergestellt.")
except Exception as e:
    print(f"[!] Fehler beim Öffnen des Ports: {e}")
    sys.exit()

print("\n=== INTERAKTIVER TIMING-TESTER ===")
print("[*] Normal (Short):  '31, 1A, 12'")
print("[*] Standard Long:   '31, 1A:L, 12'  (Hält 1A für 2 Sekunden)")
print("[*] Eigene Dauer:    '31, 1A:3.5, 12' (Hält 1A für 3.5 Sekunden)")
print("[*] Tippen Sie 'exit' oder 'q' zum Beenden.\n")

try:
    while True:
        user_input = input("Sequenz eingeben > ").strip()

        if user_input.lower() in ['exit', 'q']:
            print("[*] Programm wird beendet.")
            break
        
        if not user_input:
            continue

        raw_parts = [part.strip() for part in user_input.split(',')]
        key_sequence = [] # Speichert Paare aus (key_id, duration)
        valid = True

        for part in raw_parts:
            if not part:
                continue
            
            # Prüfen, ob ein Doppelpunkt für das Timing existiert
            duration = DEFAULT_SHORT_PRESS
            if ':' in part:
                id_part, time_part = part.split(':', 1)
                id_part = id_part.strip()
                time_part = time_part.strip().upper()
                
                if time_part == 'L':
                    duration = DEFAULT_LONG_PRESS
                else:
                    try:
                        duration = float(time_part)
                    except ValueError:
                        print(f"[!] Fehler: Ungültige Zeitangabe '{time_part}'")
                        valid = False
                        break
            else:
                id_part = part

            # ID parsen
            try:
                if id_part.lower().startswith('0x'):
                    key_id = int(id_part, 16)
                elif len(id_part) == 2 and all(c in '0123456789abcdefABCDEF' for c in id_part):
                    key_id = int(id_part, 16)
                else:
                    key_id = int(id_part)

                if 0 <= key_id <= 255:
                    key_sequence.append((key_id, duration))
                else:
                    print(f"[!] Fehler: Wert '{id_part}' ausserhalb des Bereichs.")
                    valid = False
                    break
            except ValueError:
                print(f"[!] Fehler: Ungültiges Format bei '{id_part}'.")
                valid = False
                break

        if not valid or not key_sequence:
            continue

        print(f"--> Starte Sequenz mit {len(key_sequence)} Tasten...")

        # Abarbeiten der Kette mit dynamischem Timing
        for idx, (key_id, duration) in enumerate(key_sequence):
            type_str = f"LONG ({duration}s)" if duration > DEFAULT_SHORT_PRESS else "SHORT"
            print(f"   [{idx+1}/{len(key_sequence)}] Taste 0x{key_id:02X} -> Modus: {type_str}")

            # 1. SCHRITT: Taste DRÜCKEN (3. Byte = 01)
            packet_press = bytearray([0x41, 0x00, 0x01, 0x00, key_id, 0x00, 0x00, 0x06])
            ser.write(packet_press)
            
            # Hier greift die dynamische Haltedauer!
            time.sleep(duration) 

            # Antwort beim Halten prüfen
            if ser.in_waiting > 0:
                res = ser.read(ser.in_waiting)
                print(f"       [RX Während Druck] <- {' '.join(f'{b:02X}' for b in res)}")

            # 2. SCHRITT: Taste LOSLASSEN (3. Byte = 00)
            packet_release = bytearray([0x41, 0x00, 0x00, 0x00, key_id, 0x00, 0x00, 0x06])
            ser.write(packet_release)
            time.sleep(0.05)

            # Antwort nach dem Loslassen prüfen
            if ser.in_waiting > 0:
                res = ser.read(ser.in_waiting)
                print(f"       [RX Nach Loslassen] <- {' '.join(f'{b:02X}' for b in res)}")

            # Pause zur nächsten Taste
            if idx < len(key_sequence) - 1:
                time.sleep(PAUSE_BETWEEN_KEYS)
        
        print("[*] Sequenz abgeschlossen.\n")

except KeyboardInterrupt:
    print("\n[!] Programm abgebrochen.")

finally:
    ser.close()
    print("[*] COM-Port geschlossen.")
