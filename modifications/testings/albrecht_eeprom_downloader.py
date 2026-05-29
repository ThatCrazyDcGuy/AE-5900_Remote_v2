import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.5)

def get_block(addr_h, addr_l):
    # Befehl: STX + 'R' + ADDR_H + ADDR_L + LEN (10h = 16 Bytes) + ETX
    cmd = bytes([0x02, 0x52, addr_h, addr_l, 0x10, 0x03])
    ser.write(cmd)
    time.sleep(0.1)
    if ser.in_waiting:
        return ser.read(ser.in_waiting)
    return None

try:
    print("--- AE-5900 Full Dump Mode ---")
    # Wake up
    ser.write(bytes.fromhex("02 50 52 4f 47 52 41 4d 03")) # for PC-MODE # ("02 50 52 4f 47 52 41 4d 03"))
    time.sleep(0.2)
    ser.read(ser.in_waiting) # Buffer leeren

    with open("ae5900_eeprom.bin", "wb") as f:
        for i in range(0, 16): # Wir lesen die ersten 16 Blöcke à 16 Bytes
            addr_l = (i * 16) & 0xFF
            addr_h = (i * 16) >> 8
            print(f"Lese Adresse {hex(i*16)}...")
            block = get_block(addr_h, addr_l)
            if block:
                # Wir schneiden STX/ETX und Header-Infos ab, falls nötig
                # (Meistens sendet das Gerät: 02 [DATEN] 03)
                f.write(block)
    
    print("Dump fertig! Datei 'ae5900_eeprom.bin' wurde erstellt.")

finally:
    ser.close()
