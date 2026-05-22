
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
PORT = '/dev/ttyUSB1'  # Dein aktueller USB-Port!
MODES = ["PA", "CW", "FM", "AM", "USB", "LSB"]

# --- AUDIO CONFIG ---
CHUNK = 512
stream_rx = None
stream_tx = None

def setup_audio():
    global stream_rx, stream_tx
    try:
        pa_rx = pyaudio.PyAudio()
        stream_rx = pa_rx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
        pa_tx = pyaudio.PyAudio()
        stream_tx = pa_tx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
        print("--- Audio-Streams bereit ---")
    except Exception as e:
        print(f"Audio-Setup Fehler: {e}")

setup_audio()

class RadioInterface:
    def __init__(self):
        self.load_config()
        self.lock = threading.Lock()
        self.is_tx = False
        self.is_rx = False
        self.is_device_sending = False
        self.is_scanning = False
        self.sw_scan_active = False
        self.force_rx = False
        self.ignore_until = 0
        self.ptt_start_time = 0
        self.key_buffer = ""
        
        self.current_ch = self.config.get("last_ch", 1)
        self.mode_idx = self.config.get("last_mode", 2)
        
        try:
            # WICHTIG: write_timeout verhindert das Einfrieren, falls die Hardware blockiert!
            self.ser = serial.Serial(PORT, 115200, timeout=0.05, write_timeout=0.05)
            print(f"--- AE5900 Hardware-Anbindung AKTIV ---")
            
            # Den Heartbeat nur starten, wenn die Verbindung steht
            if self.ser.is_open:
                threading.Thread(target=self.heartbeat_task, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"Serial Fehler beim Starten abgefangen: {e}")

    def load_config(self):
        default = {
            "ptt_timeout": 300, "last_ch": 1, "last_mode": 2, "skip_pa": False, "skip_cw": False,
            "p1_label": "Not set", "p2_label": "Not set", "p3_label": "Not set", "p4_label": "Not set",
            "scan_speed": 0.5, "vol": 85, "fft_rx_gain": 25000, "fft_tx_gain": 55000, "vox_enabled": False
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f: self.config = {**default, **json.load(f)}
            except: self.config = default
        else: self.config = default

    def save_config(self):
        self.config["last_ch"] = self.current_ch
        self.config["last_mode"] = self.mode_idx
        with open(CONFIG_FILE, 'w') as f: json.dump(self.config, f, indent=4)

    def send_cmd(self, hex_press, hex_release):
        if not self.ser: return
        with self.lock:
            self.ser.write(bytes.fromhex(hex_press))
            time.sleep(0.08)
            self.ser.write(bytes.fromhex(hex_release))

    def heartbeat_task(self):
        while self.ser:
            try:
                if self.ser.in_waiting == 0 and not self.is_tx and not self.sw_scan_active:
                    with self.lock:
                        hb = bytes.fromhex("41 00 00 00 82 00 00 06")
                        self.ser.write(hb)
                        time.sleep(0.03)
                        ch_hex = self.current_ch + 15
                        status = bytes([0xAA, 0x53, 0, 0, 0, 0, 0, 0, 0, 0, ch_hex, 0, 0, 1, 0, 0, 0x06])
                        self.ser.write(status)
            except: break
            time.sleep(0.6)

    def sw_scan_loop(self):
        print("Software-Scan gestartet.")
        while self.sw_scan_active:
            if not self.is_rx and not self.is_tx:
                self.current_ch = (self.current_ch % 40) + 1
                self.send_cmd("4100010010000006", "4100000010000006")
                self.save_config()
            time.sleep(self.config.get("scan_speed", 0.5))
            while self.is_rx and self.sw_scan_active:
                time.sleep(0.2)
                if self.is_tx:
                    self.sw_scan_active = False
                    break
        print("Software-Scan beendet.")

    def super_sync(self):
        self.send_cmd("4100010001000006", "4100000001000006")
        time.sleep(0.4)
        self.send_cmd("4100010002000006", "4100000002000006")
        time.sleep(0.4)
        with self.lock:
            self.ser.write(bytes.fromhex("410001001A000006"))
            time.sleep(2.2)
            self.ser.write(bytes.fromhex("410000001A000006"))
        self.current_ch = 1; self.mode_idx = 2; self.save_config()

    def adjust_squelch(self, direction):
        step_code = "12" if direction == "up" else "13"
        with self.lock:
            self.ser.write(bytes.fromhex("4100010024000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("4100000024000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex(f"41000100{step_code}000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex(f"41000000{step_code}000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("410001001E000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("410000001E000006"))

radio = RadioInterface()

def run_listen_loop():
    raw_buffer = b""
    while radio.ser:
        try:
            if radio.ser.in_waiting > 0:
                with radio.lock:
                    raw_buffer += radio.ser.read(radio.ser.in_waiting)
                while b'\x53' in raw_buffer:
                    idx = raw_buffer.find(b'\x53')
                    if len(raw_buffer[idx:]) < 16: break 
                    packet = raw_buffer[idx:idx+16]
                    
                    radio.is_rx = (packet[1] > 0 or packet[2] > 0)
                    vox_detected = (packet[6] == 0x01)
                    
                    if vox_detected and not radio.config.get("vox_enabled", False) and not radio.is_tx:
                        with radio.lock: radio.ser.write(bytes.fromhex("4100000000000006"))
                        vox_detected = False

                    if radio.force_rx:
                        with radio.lock:
                            for _ in range(3): radio.ser.write(bytes.fromhex("4100000000000006"))
                        radio.force_rx = False

                    radio.is_device_sending = vox_detected
                    raw_buffer = raw_buffer[idx+16:]
            else:
                time.sleep(0.05)
        except:
            time.sleep(0.05)
    time.sleep(0.02)

threading.Thread(target=run_listen_loop, daemon=True).start()

# --- AUDIO AUTOMATIK ---
def auto_patch_streams():
    time.sleep(4)
    try:
        source = "Mumble:output_FL"
        res_in = subprocess.run(["pw-link", "-i"], capture_output=True, text=True).stdout
        python_ports = [l.strip() for l in res_in.split('\n') if "python" in l.lower() or "alsa_capture" in l.lower()]
        if len(python_ports) >= 2:
            subprocess.run(["pw-link", source, python_ports[0]], check=False)
            print("--- Audio-Patch erfolgreich ---")
    except: pass

threading.Thread(target=auto_patch_streams, daemon=True).start()

@app.route('/')
def index(): return render_template('index.html', config=radio.config)

@app.route('/api/audio')
def get_audio():
    try:
        if radio.is_tx or radio.is_device_sending:
            data = np.frombuffer(stream_rx.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            return jsonify((np.abs(np.fft.rfft(data))[:32] / radio.config.get("fft_tx_gain", 55000)).tolist())
        else:
            data = np.frombuffer(stream_tx.read(CHUNK, exception_on_overflow=False), dtype=np.int16)
            fft = np.abs(np.fft.rfft(data))[:32]
            fft_clean = np.where(fft < 40000, 0, fft - 40000)
            return jsonify((fft_clean / radio.config.get("fft_rx_gain", 25000)).tolist())
    except: return jsonify([0]*32)

@app.route('/api/cmd/<cmd>')
def api_cmd(cmd):
    if cmd not in ['STATUS', 'SSCAN'] and not cmd.startswith('SETSPEED'):
        radio.sw_scan_active = False

    key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
    p_codes = {'P1':'1A', 'P2':'1B', 'P3':'1C', 'P4':'1D'}
    
    if cmd in ['VOLUP', 'VOLDOWN']:
        step = "5%+" if cmd == 'VOLUP' else "5%-"
        subprocess.run(["amixer", "set", "Master", step], check=False)
        current_vol = radio.config.get("vol", 85)
        radio.config["vol"] = min(100, current_vol + 5) if cmd == 'VOLUP' else max(0, current_vol - 5)
    
    elif cmd == 'HWVOLUP': radio.send_cmd("4100010012000006", "4100000012000006")
    elif cmd == 'HWVOLDOWN': radio.send_cmd("4100010013000006", "4100000013000006")
    elif cmd == 'SQUP': radio.adjust_squelch("up")
    elif cmd == 'SQDOWN': radio.adjust_squelch("down")
    elif cmd == 'HWVOX': radio.send_cmd("4100010028000006", "4100000028000006")
    elif cmd == 'HWLOCK': radio.send_cmd("410001001E000006", "410000001E000006")
    elif cmd == 'HWFUNC': radio.send_cmd("4100010031000006", "4100000031000006")
    elif cmd == 'HWACTION': radio.send_cmd("410001001E000006", "410000001E000006")

    elif cmd == 'U' or cmd == 'KU':
        radio.current_ch = (radio.current_ch % 40) + 1
        radio.send_cmd("4100010010000006", "4100000010000006")
    elif cmd == 'D' or cmd == 'KD':
        radio.current_ch = 40 if radio.current_ch == 1 else radio.current_ch - 1
        radio.send_cmd("4100010011000006", "4100000011000006")
    elif cmd == 'M':
        radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
        while True:
            if radio.config.get("skip_pa") and MODES[radio.mode_idx] == "PA":
                radio.mode_idx = (radio.mode_idx + 1) % len(MODES); continue
            if radio.config.get("skip_cw") and MODES[radio.mode_idx] == "CW":
                radio.mode_idx = (radio.mode_idx + 1) % len(MODES); continue
            break
        radio.send_cmd("410001000D000006", "410000000D000006")
    elif cmd == 'P':
        radio.is_tx = not radio.is_tx
        code = "4101000000000006" if radio.is_tx else "4100000000000006"
        radio.send_cmd(code, code)
        radio.ptt_start_time = time.time()
        
    elif cmd == 'SSCAN':
        radio.sw_scan_active = not radio.sw_scan_active
        if radio.sw_scan_active: 
            threading.Thread(target=radio.sw_scan_loop, daemon=True).start()
            
    elif cmd.startswith('SETSPEED_'):
        radio.config["scan_speed"] = float(cmd.split('_')[1]) / 1000.0
        
    elif cmd == 'S': 
        radio.super_sync()
        
    elif cmd.startswith('K'):
        digit = cmd[1:]
        if digit in key_codes:
            radio.send_cmd(f"41000100{key_codes[digit]}000006", f"41000000{key_codes[digit]}000006")
            radio.key_buffer += digit
            if len(radio.key_buffer) == 2:
                try:
                    val = int(radio.key_buffer)
                    if 1 <= val <= 40: radio.current_ch = val
                except: 
                    pass
                radio.key_buffer = ""
                
    elif cmd in p_codes:
        radio.send_cmd(f"41000100{p_codes[cmd]}000006", f"41000000{p_codes[cmd]}000006")
        
    elif cmd.startswith('SET_'):
        parts = cmd.split('_')
        val = request.args.get('val')
        if "SKIP_PA" in cmd: 
            radio.config["skip_pa"] = (val.lower() == 'true')
        elif "SKIP_CW" in cmd: 
            radio.config["skip_cw"] = (val.lower() == 'true')
        else: 
            radio.config[f"{parts[1].lower()}_label"] = val
            
    elif cmd.startswith('SETGAIN_'):
        parts = cmd.split('_')
        radio.config[f"fft_{parts[1].lower()}_gain"] = int(parts[3])

    radio.save_config()
    is_syncing = time.time() < radio.ignore_until
    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    
    return jsonify({
        "CH": str(radio.current_ch).zfill(2), 
        "MODE": MODES[radio.mode_idx], 
        "PTT": "ON" if radio.is_tx else "OFF",
        "VOX_TX": radio.is_device_sending, 
        "VOX_ENABLED": radio.config.get("vox_enabled", False), 
        "REMAINING": max(0, rem),
        "BUSY": radio.is_rx, 
        "SW_SCAN": radio.sw_scan_active, 
        "SKIP_PA": radio.config.get("skip_pa", False),
        "SKIP_CW": radio.config.get("skip_cw", False), 
        "IS_SYNCING": is_syncing, 
        "SCAN_SPEED": radio.config.get("scan_speed", 0.5)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

