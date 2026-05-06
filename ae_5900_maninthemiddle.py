import serial
import time


port_funk = '/dev/ttyUSB0' 
port_mikro = '/dev/ttyUSB1'
baudrate = 115200 

def log_and_relay():
    try:

        ser_f = serial.Serial(port_funk, baudrate, timeout=0)
        ser_m = serial.Serial(port_mikro, baudrate, timeout=0)
        
        print(f"Relay aktiv: {port_funk} <--> {port_mikro}")
        
        with open("protocol_capture.hex", "a") as f:
            while True:

                if ser_f.in_waiting:
                    data = ser_f.read(ser_f.in_waiting)
                    ser_m.write(data) 
                    log_entry = f"F->M: {data.hex(' ').upper()}\n"
                    print(log_entry, end='')
                    f.write(log_entry)


                if ser_m.in_waiting:
                    data = ser_m.read(ser_m.in_waiting)
                    ser_f.write(data) 
                    log_entry = f"M->F: {data.hex(' ').upper()}\n"
                    print(log_entry, end='')
                    f.write(log_entry)
                
                time.sleep(0.001) 
                
    except KeyboardInterrupt:
        print("\nCapture gestoppt.")
    finally:
        ser_f.close()
        ser_m.close()

if __name__ == "__main__":
    log_and_relay()
