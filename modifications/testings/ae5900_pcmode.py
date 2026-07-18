import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=0.5)

try:
    print("Sende PC-MODE Befehl an AE-5900...")
    

    ser.write(bytes.fromhex("02 50 52 4f 47 52 41 4d 03"))
    time.sleep(0.2)
    
    print("Befehl gesendet.")

finally:
    ser.close()
