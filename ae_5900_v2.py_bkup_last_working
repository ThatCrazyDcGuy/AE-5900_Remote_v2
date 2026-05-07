import serial
import threading
import time
import json
import os
import numpy as np
import pyaudio
import subprocess
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
PORT = '/dev/ttyUSB0'
MODES = ["PA", "CW", "FM", "AM", "USB", "LSB"]

CHUNK = 512
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)


class RadioInterface:
    def __init__(self):
        self.load_config()
        
        self.lock = threading.Lock()
        self.is_tx = False
        self.is_rx = False
        self.is_device_sending = False
        self.is_scanning = False
        self.sw_scan_active = False
        self.ptt_start_time = 0
        self.key_buffer = ""
        
        self.current_ch = self.config.get("last_ch", 1)
        self.mode_idx = self.config.get("last_mode", 2)
        self.scan_dir = 1 
        self.ignore_until = 0 
        
        try:
            self.ser = serial.Serial(PORT, 115200, timeout=0.01)
            print(f"--- AE5900 Master-Emulator ONLINE (Full Feature) ---")
            threading.Thread(target=self.heartbeat_task, daemon=True).start()
            threading.Thread(target=self.listen_loop, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"Serial Fehler: {e}")

    def load_config(self):
        default = {"ptt_timeout": 300, "last_ch": 1, "last_mode": 2, "skip_pa": False,
                   "p1_label": "ASQ", "p2_label": "VOX", "p3_label": "SCAN", "p4_label": "DW",
                   "scan_speed": 0.5}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config = {**default, **json.load(f)}
            except: self.config = default
        else: self.config = default

    def save_config(self):
        self.config["last_ch"] = self.current_ch
        self.config["last_mode"] = self.mode_idx
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f, indent=4)

    def heartbeat_task(self):
        while self.ser:
            try:
                if self.ser.in_waiting == 0 and not self.is_tx:
                    with self.lock:
                        hb = bytes.fromhex("41 00 00 00 82 00 00 06")
                        self.ser.write(hb)
                        time.sleep(0.03)
                        ch_hex = self.current_ch + 15
                        status = bytes([0xAA, 0x53, 0, 0, 0, 0, 0, 0, 0, 0, ch_hex, 0, 0, 1, 0, 0, 0x06])
                        self.ser.write(status)
            except: break
            time.sleep(0.6)

    def listen_loop(self):
        raw_buffer = b""
        while self.ser:
            if self.ser.in_waiting > 0:
                try:
                    raw_buffer += self.ser.read(self.ser.in_waiting)
                    while b'\x53' in raw_buffer:
                        idx = raw_buffer.find(b'\x53')
                        if len(raw_buffer[idx:]) < 16: break 
                        
                        packet = raw_buffer[idx:idx+16]
                        
                        self.is_rx = (packet[1] > 0 or packet[2] > 0)

                        self.is_device_sending = (packet[6] == 0x01)

                        raw_buffer = raw_buffer[idx+16:]
                except: pass
            time.sleep(0.02)



    def send_cmd(self, hex_press, hex_release):
        if not self.ser: return
        with self.lock:
            self.ser.write(bytes.fromhex(hex_press))
            time.sleep(0.08)
            self.ser.write(bytes.fromhex(hex_release))

    def super_sync(self):
        self.ignore_until = time.time() + 1.2
        self.send_cmd("4100010001000006", "4100000001000006")
        time.sleep(0.4)
        self.send_cmd("4100010002000006", "4100000002000006")
        time.sleep(0.4)
        with self.lock:
            self.ser.write(bytes.fromhex("410001001A000006"))
            time.sleep(2.2)
            self.ser.write(bytes.fromhex("410000001A000006"))
        self.current_ch = 1; self.mode_idx = 2; self.save_config()

    def sw_scan_loop(self):
        print("Software-Scan gestartet.")
        while self.sw_scan_active:
            if not self.is_rx and not self.is_tx:
                self.current_ch = (self.current_ch % 40) + 1
                self.send_cmd("4100010010000006", "4100000010000006")
                self.save_config()
            
            speed = self.config.get("scan_speed", 0.5)
            time.sleep(speed)
            
            while self.is_rx and self.sw_scan_active:
                time.sleep(0.2)
                if self.is_tx:
                    self.sw_scan_active = False
                    break

        print("Software-Scan beendet.")

    def stop_sw_scan(self):
        if self.sw_scan_active:
            self.sw_scan_active = False
            print("Software-Scan gestoppt.")

radio = RadioInterface()


@app.route('/')
def index(): return render_template('index.html', config=radio.config)


@app.route('/api/audio')
def get_audio():
    try:
        data = np.frombuffer(stream.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
        fft = np.abs(np.fft.rfft(data))[:32]

        fft = np.where(fft < 40000, 0, fft - 40000)
        fft_scaled = (fft / 25000) 
        
        return jsonify(fft_scaled.tolist())
    except:
        return jsonify([0]*32)

@app.route('/api/volume/<action>')
def volume_api(action):
    try:
        # 1. Aktuelle Lautstärke holen
        res = subprocess.run(["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"], capture_output=True, text=True)
        # Ausgabe ist oft "Volume: 0.50" (oder mit [MUTED])
        parts = res.stdout.split()
        current_vol = float(parts[1])

        # 2. Aktion berechnen (5% Schritte sind meistens spürbarer als 1%)
        step = 0.05 
        if action == 'up':
            new_vol = min(1.5, current_vol + step)
        elif action == 'down':
            new_vol = max(0.0, current_vol - step)
        elif action.replace('.','',1).isdigit(): # Falls direkter Wert übergeben wird
            new_vol = max(0.0, min(1.5, float(action)))
        else:
            return jsonify({"volume": current_vol})

        # 3. Setzen
        subprocess.run(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{new_vol:.2f}"])
        return jsonify({"volume": int(new_vol * 100)}) # Rückgabe in Prozent für die UI
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/cmd/<cmd>')
def api_cmd(cmd):
    if cmd not in ['STATUS', 'SSCAN'] and not cmd.startswith('SETSPEED'):
        radio.stop_sw_scan()

    key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
    p_codes = {'P1':'1A', 'P2':'1B', 'P3':'1C', 'P4':'1D'}
    
    if cmd == 'STATUS': 
        pass
        
    elif cmd == 'U': 
        radio.ignore_until = time.time() + 0.5
        radio.current_ch = (radio.current_ch % 40) + 1; radio.scan_dir = 1
        radio.send_cmd("4100010010000006", "4100000010000006")
        
    elif cmd == 'D': 
        radio.ignore_until = time.time() + 0.5
        radio.current_ch = 40 if radio.current_ch == 1 else radio.current_ch - 1; radio.scan_dir = -1
        radio.send_cmd("4100010011000006", "4100000011000006")
        
    elif cmd == 'M':
        radio.send_cmd("410001000D000006", "410000000D000006")
        radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
        if radio.config.get("skip_pa") and MODES[radio.mode_idx] == "PA":
            radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
            
    elif cmd == 'P':
        radio.is_tx = not radio.is_tx
        code = "4101000000000006" if radio.is_tx else "4100000000000006"
        with radio.lock:
            radio.ser.write(bytes.fromhex(code))
        radio.ptt_start_time = time.time()
        radio.ignore_until = time.time() + 0.5

    elif cmd == 'SSCAN':
        radio.sw_scan_active = not radio.sw_scan_active
        if radio.sw_scan_active:
            threading.Thread(target=radio.sw_scan_loop, daemon=True).start()

    elif cmd.startswith('SETSPEED_'):
        try:
            parts = cmd.split('_')
            if len(parts) > 1:
                speed_ms = float(parts[1]) 
                radio.config["scan_speed"] = speed_ms / 1000.0
                radio.save_config()
                print(f"--- SCAN SPEED NEU: {radio.config['scan_speed']}s ---")
        except Exception as e:
            print(f"Fehler bei SETSPEED: {e}")


    elif cmd == 'S': 
        radio.super_sync()
        
    elif cmd.startswith('K'):
        digit = cmd[1:]
        if digit in key_codes:
            radio.send_cmd(f"41000100{key_codes[digit]}000006", f"41000000{key_codes[digit]}000006")
            radio.key_buffer += digit
            if len(radio.key_buffer) == 2:
                radio.ignore_until = time.time() + 0.8
                try:
                    val = int(radio.key_buffer)
                    if 1 <= val <= 40: radio.current_ch = val
                except: pass
                radio.key_buffer = ""
                
    elif cmd in p_codes: 
        radio.send_cmd(f"41000100{p_codes[cmd]}000006", f"41000000{p_codes[cmd]}000006")
        
    elif cmd.startswith('SET_'):
        parts = cmd.split('_'); val = request.args.get('val')
        if "SKIP" in cmd: radio.config["skip_pa"] = (val.lower() == 'true')
        else: radio.config[f"{parts[1].lower()}_label"] = val
        
    elif cmd.startswith('T'):
        try: radio.config["ptt_timeout"] = int(cmd[1:])
        except: pass

    if radio.is_tx and (time.time() - radio.ptt_start_time >= radio.config["ptt_timeout"]):
        radio.is_tx = False
        radio.send_cmd("4100000000000006", "4100000000000006")

    radio.save_config()
    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    
    return jsonify({
        "CH": str(radio.current_ch).zfill(2), 
        "MODE": MODES[radio.mode_idx], 
        "PTT": "ON" if radio.is_tx else "OFF", 
        "VOX_TX": radio.is_device_sending,
        "REMAINING": max(0, rem), 
        "BUSY": radio.is_rx, 
        "SCAN": radio.is_scanning,
        "SW_SCAN": radio.sw_scan_active
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
