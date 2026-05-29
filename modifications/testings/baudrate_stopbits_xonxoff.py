import serial
import time

PORT = '/dev/ttyUSB0'
# Erweiterte Liste: 9600 (Standard), 19200, 38400 (Dein Favorit), 57600
BAUDRATES = [9600, 19200, 38400, 57600, 115200]
# Kombinationen aus Flow-Control-Modi
MODI = [
    {'xonxoff': False, 'rtscts': False, 'name': 'None'},
    {'xonxoff': True, 'rtscts': False, 'name': 'XON/XOFF'},
    {'xonxoff': False, 'rtscts': True, 'name': 'RTS/CTS'}
]

# Deine bisherigen "Trigger"-Pakete
TEST_PACKETS = [bytes.fromhex("fa0100fb"), bytes.fromhex("fa0000fa"), bytes.fromhex("042021e0")]

def advanced_brute_force():
    with open("serial_scan_extended_log.txt", "a") as log:
        log.write(f"\n--- Scan Start: {time.ctime()} ---\n")
        
        for baud in BAUDRATES:
            for mode in MODI:
                print(f"Test: {baud} Baud | Mode: {mode['name']}...")
                
                try:
                    # Initialisierung mit spezifischem Modus
                    ser = serial.Serial(
                        PORT, 
                        baudrate=baud, 
                        timeout=0.5,
                        xonxoff=mode['xonxoff'],
                        rtscts=mode['rtscts'],
                        dsrdtr=False
                    )
                    
                    # Kleiner "Wake-up" für den Bus
                    ser.reset_input_buffer()
                    
                    for pkt in TEST_PACKETS:
                        ser.write(pkt)
                        # Wir warten 2 Sekunden pro Versuch, um dem Gerät Zeit für den Modus-Wechsel zu geben
                        time.sleep(2) 
                        
                        if ser.in_waiting:
                            ans = ser.read(ser.in_waiting).hex(' ')
                            res = f"HIT! {baud} | {mode['name']} | Send: {pkt.hex(' ')} | Recv: {ans}"
                            print(f" >>> {res}")
                            log.write(res + "\n")
                    
                    ser.close()
                except Exception as e:
                    print(f"Fehler bei {baud}: {e}")

if __name__ == "__main__":
    print("Starte erweiterten Scan...")
    print("PROBIERE JETZT: Gerät mit gedrückter FUNC-Taste einschalten!")
    advanced_brute_force()
