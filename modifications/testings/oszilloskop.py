import serial

# Teste nacheinander 38400, 57600 und 115200
#BAUD = 9600
#BAUD = 19200
#BAUD = 38400
#BAUD = 57600
BAUD = 115200
#BAUD = 921600

ser = serial.Serial('/dev/ttyUSB0', BAUD, timeout=0.05)

print(f"Lese Rohdaten bei {BAUD} Baud... Drücke Tasten am Gerät!")

try:
    while True:
        if ser.in_waiting:
            # Wir lesen alles, was kommt, und schauen uns die Struktur an
            raw = ser.read(ser.in_waiting)
            print(f"RAW: {raw.hex(' ')}")
except KeyboardInterrupt:
    ser.close()
