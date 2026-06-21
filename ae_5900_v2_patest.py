from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial
import serial.tools.list_ports
import threading
import time
import json
import os
import numpy as np
import pyaudio
import subprocess
import socket
import sys

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ae5900_super_secret'

socketio = SocketIO(app,
                    async_mode='threading',
                    ping_timeout=25,
                    ping_interval=5,
                    cors_allowed_origins="*",
                    manage_session=False, 
                    logger=False,
                    engineio_logger=False)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
PORT = '/dev/ttyUSB0'
MODES = ["PA", "CW", "FM", "AM", "USB", "LSB"]

# --- AUDIO CONFIG ---
CHUNK = 512
stream_rx = None
stream_tx = None

def setup_audio():
    global stream_rx, stream_tx
    try:
        os.environ['PULSE_PROP'] = 'node.description="AE_RX" node.name="AE_RX"'
        pa_rx = pyaudio.PyAudio()
        stream_rx = pa_rx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
        
        os.environ['PULSE_PROP'] = 'node.description="AE_TX" node.name="AE_TX"'
        pa_tx = pyaudio.PyAudio()
        stream_tx = pa_tx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
        
        os.environ.pop('PULSE_PROP', None)
        print("--- Audio-Streams AE_RX und AE_TX bereit ---")
    except Exception as e:
        print(f"Audio-Setup Fehler: {e}")

setup_audio()

def auto_patch_streams():
    time.sleep(6) 
    try:
        print("[AUTOMATISCHER PIPEWIRE-WEICHENSTELLER GESTARTET]")
        res = subprocess.run(["pactl", "list", "short"], capture_output=True, text=True).stdout
        lines = [l.strip() for l in res.split('\n') if l.strip()]
        
        stereo_target = None
        mono_target = None
        python_node_ids = []
        
        for line in lines:
            line_lower = line.lower()
            parts = line.split()
            if len(parts) >= 2:
                if "analog-stereo.monitor" in line_lower:
                    stereo_target = parts[0]
                elif "mono-fallback" in line_lower and "monitor" not in line_lower:
                    mono_target = parts[0]
                if "22050hz" in line_lower:
                    node_id = parts[0]
                    if node_id.isdigit() and node_id not in python_node_ids:
                        python_node_ids.append(node_id)

        if len(python_node_ids) >= 2 and stereo_target and mono_target:
            rx_node = str(python_node_ids[0])
            tx_node = str(python_node_ids[1])
            
            subprocess.run(["pactl", "move-source-output", rx_node, stereo_target], check=False)
            subprocess.run(["pactl", "move-source-output", tx_node, mono_target], check=False)
            
            mumble_source = "Mumble:output_FL"
            res_links = subprocess.run(["pw-link", "-i"], capture_output=True, text=True).stdout
            python_ports = [l.strip() for l in res_links.split('\n') if "python" in l.lower() or "alsa_capture" in l.lower()]
            if len(python_ports) >= 2:
                target = python_ports[1]
                subprocess.run(["pw-link", mumble_source, target], check=False)
            print("[SYSTEM-WEICHE PERFEKT REBOOT-SICHER EINGESTELLT]")
    except Exception as e:
        print(f"Patch-Fehler in auto_patch_streams: {e}")


class RadioInterface:
    def __init__(self):
        self.load_config()
        self.lock = threading.Lock()
        self.is_tx = False
        self.is_rx = False
        self.is_device_sending = False
        self.force_rx = False
        self.is_scanning = False
        self.sw_scan_active = False
        self.ptt_start_time = 0
        self.key_buffer = ""
        self.scan_dir = 1 
        self.ignore_until = 0 
        self.audio_mute = False
        self.macro_active = False
        self.current_ch = self.config.get("last_ch", 1)
        self.mode_idx = self.config.get("last_mode", 2)
        self.key_input_start_time = 0
        self.last_ptt_release_time = 0
        self.squelch_timeout_until = 0.0
        self.asq_timeout_until = 0.0
        self.mute_timeout_until = 0.0

        detected_port = None
        try:
            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                p_desc = str(p.description).upper()
                p_dev = str(p.device).upper()
                if "FT232" in p_desc or "FTDI" in p_desc or "USB" in p_dev:
                    print(f"-> TREFFER: Albrecht-Wandler auf Port {p.device} lokalisiert!")
                    detected_port = p.device
                    break
        except Exception as e:
            print(f"HARDWARE-CHECK FEHLER: {e}")

        if not detected_port:
            detected_port = PORT
            print(f"-> Fallback auf Standard-Port: {detected_port}")

        try:
            self.ser = serial.Serial(detected_port, 115200, timeout=0.01)
            print(f"--- AE5900 Master-Emulator ONLINE auf {detected_port} ---")
            threading.Thread(target=self.heartbeat_task, daemon=True).start()
            threading.Thread(target=self.listen_loop, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"--- SIMULATIONS-MODUS AKTIV: Kein Funkgeraet an {detected_port} ---")

    def load_config(self):
        default = {
            "ptt_timeout": 300, "last_ch": 1, "last_mode": 2, "skip_pa": False, "skip_cw": False,
            "p1_label": "(/)", "p2_label": "(/)", "p3_label": "(/)", "p4_label": "(/)",
            "scan_speed": 0.5, "fft_rx_gain": 25000, "fft_tx_gain": 55000,
            "vox_enabled": False, "mute_enabled": False, "asq_enabled": False, "asq_memory": False,
            "clar_step": "STEP", "clar_offsets": {str(ch).zfill(2): 0 for ch in range(1, 41)},
            "ptt_hotkey": "F6", "current_beep": "None", "roger_beep_enabled": True, "max_sq_steps": 80, 
            "max_asq_steps": 9, "current_sq_level": 0, "current_asq_level": 1, "full_sync_active": False,
            
            # --- UNSERE NEUEN VARIABLEN FÜR DIE LÄNDERCODES ---
            "current_band": "EU",
            "backup_mode_idx": 2,
            
            # --- BEREINIGT: SPEICHER FÜR DIE DYNAMISCHE TASTEN-UMSCHALTUNG ---
            "active_p_block": "standard",
            "cust_lbl_1": "CUST 1",
            "cust_lbl_2": "CUST 2",
            "cust_lbl_3": "CUST 3",
            "cust_lbl_4": "CUST 4",
            "cust_cmd_1": "",
            "cust_cmd_2": "",
            "cust_cmd_3": "", 
            "cust_cmd_4": ""
        }
        
        beep_dir = os.path.join(SCRIPT_DIR, "beeps")
        if not os.path.exists(beep_dir):
            try: os.makedirs(beep_dir)
            except: pass

        self.beeps_list = []
        if os.path.exists(beep_dir):
            try: self.beeps_list = [f for f in os.listdir(beep_dir) if f.lower().endswith('.wav')]
            except: pass

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                    disk_config = json.load(f)
                    if "clar_offset" in disk_config and "clar_offsets" not in disk_config:
                        old_val = disk_config["clar_offset"]
                        disk_config["clar_offsets"] = {str(ch).zfill(2): 0 for ch in range(1, 41)}
                        disk_config["clar_offsets"][str(disk_config.get("last_ch", 1)).zfill(2)] = int(old_val)
                    if "clar_offsets" not in disk_config: disk_config["clar_offsets"] = default["clar_offsets"]
                    self.config = {**default, **disk_config}
            except: self.config = default
        else: self.config = default

    def save_config(self):
        self.config["last_ch"] = self.current_ch
        self.config["last_mode"] = self.mode_idx
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
                json.dump(self.config, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e: print(f"Schreibfehler: {e}")

    def heartbeat_task(self):
        while self.ser:
            try:
                if self.ser.in_waiting == 0 and not self.is_tx and not self.force_rx:
                    with self.lock:
                        self.ser.write(bytes.fromhex("41 00 00 00 82 00 00 06"))
                        time.sleep(0.03)
                        status = bytes([0xAA, 0x53, 0, 0, 0, 0, 0, 0, 0, 0, self.current_ch + 15, 0, 0, 1, 0, 0, 0x06])
                        self.ser.write(status)
            except: break
            time.sleep(0.6)

    def listen_loop(self):
        """Erkennt Signal (RX) und VOX-Status (TX)"""
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
                        vox_detected = (packet[6] == 0x01)
                        
                        if (time.time() - getattr(self, 'last_ptt_release_time', 0)) < 5.0:
                            vox_detected = False

                        if vox_detected and not self.is_tx:
                            try:
                                if os.path.exists(CONFIG_FILE):
                                    with open(CONFIG_FILE, 'r') as f:
                                        disk_config = json.load(f)
                                        self.config["vox_enabled"] = disk_config.get("vox_enabled", False)
                            except Exception as e:
                                print(f"Fehler beim Live-Config-Read: {e}")

                            if not self.config.get("vox_enabled", False) and not getattr(self, 'is_vox_changing', False):
                                with self.lock:
                                    self.ser.write(bytes.fromhex("4100000000000006"))
                                print("VOX-VETO: Automatisches Senden unterdrueckt.")
                                vox_detected = False

                        if self.force_rx and not getattr(self, 'is_vox_changing', False):
                            with self.lock:
                                stop_cmd = bytes.fromhex("4100000000000006")
                                for _ in range(3):
                                    self.ser.write(stop_cmd)
                                    time.sleep(0.01) 
                            self.force_rx = False 
                            print("Manueller Abbruch ausgefuehrt.")

                        self.is_device_sending = vox_detected
                        raw_buffer = raw_buffer[idx+16:]
                except Exception as e:
                    print(f"Listen Loop Fehler: {e}")
                    pass
            time.sleep(0.02)

    def send_cmd(self, hex_press, hex_release):
        if not self.ser: return
        with self.lock:
            self.ser.write(bytes.fromhex(hex_press))
            time.sleep(0.08)
            self.ser.write(bytes.fromhex(hex_release))

    def sw_scan_loop(self):
        print("Software-Scan gestartet.")
        while self.sw_scan_active:
            if not self.is_rx and not self.is_tx:
                self.current_ch = (self.current_ch % 40) + 1
                self.send_cmd("4100010010000006", "4100000010000006")
                self.shadow_config = self.save_config() # Failsafe Fix
            time.sleep(self.config.get("scan_speed", 0.5))
            while self.is_rx and self.sw_scan_active:
                time.sleep(0.2)
                if self.is_tx:
                    self.sw_scan_active = False
                    break
        print("Software-Scan beendet.")

    def stop_sw_scan(self):
        self.sw_scan_active = False

    def super_sync(self):
        self.ignore_until = time.time() + 1.2
        self.send_cmd("4100010001000006", "4100000001000006")
        time.sleep(0.4)
        self.send_cmd("4100010002000006", "4100000002000006")
        time.sleep(0.4)
        if self.ser:
            with self.lock:
                self.ser.write(bytes.fromhex("410001001A000006"))
                time.sleep(2.2)
                self.ser.write(bytes.fromhex("410000001A000006"))
        self.current_ch = 1; self.mode_idx = 2; self.save_config()

def mw_scan_loop(radio):
    print("Multi-Watch (MW) gestartet.")
    while radio.mw_active:
        ch_string = radio.config.get("mw_label", "09, 19")
        try:
            channels = [c.strip().zfill(2) for c in ch_string.split(",") if c.strip()]
        except:
            radio.mw_active = False
            break
        if not channels:
            radio.mw_active = False
            break

        for ch in channels:
            if not radio.mw_active: break
            while radio.is_rx and radio.mw_active:
                time.sleep(0.2)
            if not radio.mw_active: break

            # --- KANAL PHYSISCH ANSTEUERN ---
            print(f"MW schaltet auf Kanal: {ch}")
            
            # Kanal im globalen Radio-Objekt fuer das Web-UI setzen
            radio.current_ch = int(ch)
            
            # KORREKTUR: Saubere Spaltung in Zehner- und Einerstelle!
            ziffer1 = ch[0]  # Erste Ziffer (z.B. bei "08" -> "0")
            ziffer2 = ch[1]  # Zweite Ziffer (z.B. bei "08" -> "8")
            
            key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
            
            # Erste Ziffer aus dem Keypad emulieren und senden
            if ziffer1 in key_codes:
                radio.send_cmd(f"41000100{key_codes[ziffer1]}000006", f"41000000{key_codes[ziffer1]}000006")
            time.sleep(0.120) # Sicherheits-Pause fuer den Albrecht-Prozessor
            
            # Zweite Ziffer aus dem Keypad emulieren und senden
            if ziffer2 in key_codes:
                radio.send_cmd(f"41000100{key_codes[ziffer2]}000006", f"41000000{key_codes[ziffer2]}000006")
            
            # 1 Sekunde auf diesem Kanal lauschen (Taktzeit)
            for _ in range(10):
                if not radio.mw_active or radio.is_rx:
                    break
                time.sleep(0.1)
    print("Multi-Watch (MW) beendet.")

radio = RadioInterface()

def play_roger_beep():
    try:
        chosen_beep = radio.config.get("current_beep", "None")
        if chosen_beep == "None": return
        beep_path = os.path.join(SCRIPT_DIR, "beeps", chosen_beep)
        
        if os.path.exists(beep_path):
            def run_paplay_beep():
                print(f"ROGERBEEP: Spiele {chosen_beep} starr auf dem Mono-TX-Kanal ab...")
                env = os.environ.copy()
                env['PULSE_SINK'] = 'mono-fallback' 
                subprocess.run(["paplay", "--latency-msec=1", beep_path], env=env, check=False)
                print("ROGERBEEP: Erfolgreich moduliert und abgeschlossen.")
                
            threading.Thread(target=run_paplay_beep, daemon=True).start()
    except Exception as e:
        print(f"Rogerbeep Fehler: {e}")

@app.route('/')
def index():
    browser_languages = request.accept_languages.values()
    erkannte_sprache = 'en'
    
    for lang_code in browser_languages:
        lang_lower = lang_code.lower()
        if lang_lower.startswith('de'):
            erkannte_sprache = 'de'
            break
        elif lang_lower.startswith('en'):
            erkannte_sprache = 'en'
            break
        elif lang_lower.startswith('fr'):
            erkannte_sprache = 'fr'
            break
        elif lang_lower.startswith('pl'):
            erkannte_sprache = 'pl'
            break
    print(f"SPRACHE: Browser-Erkennung ergab: '{erkannte_sprache}'")
    
    return render_template('index.html', 
                           config=radio.config, 
                           beeps_list=radio.beeps_list, 
                           lang=erkannte_sprache)

@app.route('/api/audio')
def get_audio():
    try:
        if getattr(radio, 'audio_mute', False): return jsonify([0] * 32)
        if radio.is_tx or radio.is_device_sending:
            raw_data = stream_rx.read(CHUNK, exception_on_overflow=False)
            gain = radio.config.get("fft_tx_gain", 55000)
            data = np.frombuffer(raw_data, dtype=np.int16)
            return jsonify((np.abs(np.fft.rfft(data))[:32] / gain).tolist())
        else:
            raw_data = stream_tx.read(CHUNK, exception_on_overflow=False)
            gain = radio.config.get("fft_rx_gain", 25000)
            data = np.frombuffer(raw_data, dtype=np.int16)
            fft = np.abs(np.fft.rfft(data))[:32]
            fft_clean = np.where(fft < 40000, 0, fft - 40000)
            return jsonify((fft_clean / gain).tolist())
    except: return jsonify([0] * 32)

@app.route('/api/rig/ptt/<int:state>')
def rig_ptt_control(state):
    try:
        if state == 1 and not radio.is_tx:
            radio.is_tx = True
            radio.ptt_start_time = time.time()
            if radio.ser:
                with radio.lock: radio.ser.write(bytes.fromhex("4101000000000006"))
        elif state == 0 and radio.is_tx:
            radio.is_tx = False
            if radio.ser:
                with radio.lock: radio.ser.write(bytes.fromhex("4100000000000006"))
            play_roger_beep()
        return f"PTT_STATE: {radio.is_tx}\n"
    except Exception as e: return f"ERROR: {str(e)}\n", 500

@app.route('/api/cmd/<cmd>')
def api_cmd(cmd):
    global MODES, LAST_BROWSER_HEARTBEAT  # HIER GANZ OBEN HINGESETZT
    LAST_BROWSER_HEARTBEAT = time.time()
    if cmd not in ['STATUS', 'MW_TOGGLE', 'SSCAN'] and not cmd.startswith('SETSPEED'):
        radio.stop_sw_scan()
        if hasattr(radio, 'mw_active') and radio.mw_active: 
            radio.mw_active = False 
    if cmd == 'SSCAN' and hasattr(radio, 'mw_active') and radio.mw_active: 
        radio.mw_active = False

    key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
    p_codes = {'P1':'1A', 'P2':'1B', 'P3':'1C', 'P4':'1D'}
    
    # KORREKTUR: Das vergessene Wörterbuch ist wieder an Bord!
    superkey_codes = {
        'FUNC_KEY':'0x31', 'ACTION':'0x1E', 'LOCKDEV':'0x1E:2', 'CLARUP':'0x26', 'CLARHZ':'0x1E', 'CLARDN':'0x27',
        'VOX_TOGGLE':'28', 'VOX_SETTING':'0x28:2', 'EMG_TOGGLE':'0x25', 'DEVBUTTONUP':'0x10', 'DEVBUTTONDOWN':'0x11',
        'DEVROTATEUP':'0x12', 'DEVROTATEDOWN':'0x13', 'DEVXUP':'0x26', 'DEVXDOWN':'0x27',
        'SQUELCHUP':'0x24, 0x26, 0x24', 'SQUELCHMAXUP':'0x24, 0x26:17, 0x24', 'SQUELCHDOWN':'0x24, 0x27, 0x24', 'SQUELCHMAXDOWN':'0x24, 0x27:17, 0x24',
        'MODE':'0x0D', 'MODELONG':'0x0D:2', 'MODEALT':'0x23', 'MUTECOMBBTN':'0x31, 0x1E', 'MUTESINGLEBTN':'0x34', 'DEVDW':'0x31, 0x27', 'DEVSCAN':'0x31, 0x26', 'ASQ_ON_OFF':'24:2'
    }

    with radio.lock:
        if cmd in ['VOLUP', 'VOLDOWN']:
            control_name = "Master"
            step = "5%+" if cmd == 'VOLUP' else "5%-"
            os.system(f"amixer set '{control_name}' {step}")
            current_vol = radio.config.get("vol", 85)
            if cmd == 'VOLUP': 
                radio.config["vol"] = min(100, current_vol + 5)
            else: 
                radio.config["vol"] = max(0, current_vol - 5)
            radio.save_config()

        elif cmd in ['U', 'D']:
            band = radio.config.get("current_band", "EU")
            current_hardware_mode = MODES[radio.mode_idx].upper()

            # --- HARDWARE-PROFI-WEICHE: CH UP/DOWN sendet im PA-Modus die Lautstärke-Hex-Codes ---
            if current_hardware_mode == "PA":
                print(f"[PA-MODUS] Sende physische Lautstaerke-CAT-Befehle an die Hardware...")
                if radio.ser:
                    # Nutzt deine vorgegebenen Keycodes (26 für UP / 27 für DOWN)
                    hex_cmd = "26" if cmd == 'U' else "27"
                    radio.ser.write(bytes.fromhex(f"41000100{hex_cmd}000006"))
                    time.sleep(0.08)
                    radio.ser.write(bytes.fromhex(f"41000000{hex_cmd}000006"))
                
                # FLASK-ZÜNDER: Wir müssen ein gültiges Status-JSON zurückgeben!
                # Wir rufen einfach deine existierende Status-Funktion auf, damit das UI weiterlebt
                return jsonify(get_current_status_dict())

            # --- AB HIER FOLGT DEINE NORMALE KANAL-LOGIK FÜR DIE ANDEREN MODI ---
            max_ch = 40
            if band == "DE": max_ch = 80
            elif band == "IN": max_ch = 27

            alter_kanal = radio.current_ch
            
            if cmd == 'U':
                radio.current_ch = (radio.current_ch % max_ch) + 1
            else:
                radio.current_ch = max_ch if radio.current_ch == 1 else radio.current_ch - 1

            # --- DEUTSCHLAND LOGIK (Kanal 41-80) ---
            if band == "DE":
                alter_modus = MODES[radio.mode_idx].upper()
                
                if alter_kanal <= 40 and radio.current_ch > 40:
                    # BATTLES-PROOF: Sichert jeden Modus (inkl. FM) vor dem Sprung nach oben
                    radio.config["backup_mode_idx"] = radio.mode_idx
                    radio.save_config()
                    
                    if alter_modus != "FM":
                        radio.mode_idx = MODES.index("FM")
                        print(f"[BAND DE] Kanal > 40 betreten: Erzwinge FM (Merke {alter_modus})")
                    else:
                        print(f"[BAND DE] Kanal > 40 betreten: War bereits auf FM (Im Gedaechtnis gesichert)")
                        
                elif (alter_kanal > 40 and radio.current_ch <= 40) or (alter_kanal == 80 and radio.current_ch == 1):
                    radio.mode_idx = radio.config.get("backup_mode_idx", 2)
                    print(f"[BAND DE] Zurueck auf Kanal 1-40: Stelle Modus {MODES[radio.mode_idx]} wieder her")

            # --- DER VERMISSTE HARDWARE-ZÜNDER (Wieder da!) ---
            if radio.ser:
                hex_cmd = "10" if cmd == 'U' else "11"
                radio.ser.write(bytes.fromhex(f"41000100{hex_cmd}000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex(f"41000000{hex_cmd}000006"))

        elif cmd == 'M':
            band = radio.config.get("current_band", "EU")
            vorheriger_mode = MODES[radio.mode_idx].upper()
            
            if vorheriger_mode in ["AM", "FM", "UK"]:
                radio.config["asq_memory"] = radio.config.get("asq_enabled", False)
                radio.save_config()

            # --- DYNAMISCHE ROTATION JE NACH BAND (PA-TEST FÜR FW 1.12) ---
            if band == "DE" and radio.current_ch > 40:
                # Auf deutschen Kanälen 41-80: Wenn der User PA ausgeblendet hat, bleibt nur FM!
                if radio.config.get("skip_pa", False):
                    radio.mode_idx = MODES.index("FM")
                    print("[FW 1.12 Failsafe] Band DE (>40): PA ist im Setup gesperrt. Bleibe fest auf FM.")
                else:
                    if vorheriger_mode == "FM":
                        radio.mode_idx = MODES.index("PA")
                    else:
                        radio.mode_idx = MODES.index("FM")
                print(f"[BAND DE] Kanal {radio.current_ch} > 40: Mode-Wechsel durchgefuehrt. Aktuell: {MODES[radio.mode_idx]}")
            
            elif band == "EC":
                # EC erlaubt laut Norm nur FM und PA. Auch hier greift der User-Filter:
                if radio.config.get("skip_pa", False):
                    radio.mode_idx = MODES.index("FM")
                    print("[FW 1.12 Failsafe] Band EC: PA ist im Setup gesperrt. Bleibe fest auf FM.")
                else:
                    if vorheriger_mode == "FM":
                        radio.mode_idx = MODES.index("PA")
                    else:
                        radio.mode_idx = MODES.index("FM")
            
            else:
                # Standard-Rotation für alle anderen Bänder (Nutzt das dynamische MODES-Array)
                radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
                while True:
                    current_mode = MODES[radio.mode_idx].upper()
                    
                    if radio.config.get("skip_pa", False) and current_mode == "PA": 
                        radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
                        continue  
                    if radio.config.get("skip_cw", False) and current_mode == "CW": 
                        radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
                        continue  
                    break
            
            neuer_mode = MODES[radio.mode_idx].upper()
            
            if neuer_mode in ["AM", "FM", "UK"]:
                radio.config["asq_enabled"] = radio.config.get("asq_memory", False)
            else:
                radio.config["asq_enabled"] = False
                
            radio.save_config()

            if radio.ser:
                radio.ser.write(bytes.fromhex("410001000D000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex("410000000D000006"))

        elif cmd == 'P':
            was_transmitting = radio.is_tx
            radio.is_tx = not radio.is_tx
            radio.force_rx = False 
            if was_transmitting:
                print("PTT-RELEASE: Sende Rogerbeep aktiv ueber den Aether...")
                chosen_beep = radio.config.get("current_beep", "None")
                if chosen_beep != "None" and radio.config.get("roger_beep_enabled", True):
                    beep_path = os.path.join(SCRIPT_DIR, "beeps", chosen_beep)
                    if os.path.exists(beep_path):
                        env = os.environ.copy()
                        env['PULSE_SINK'] = 'mono-fallback'
                        subprocess.run(["paplay", beep_path], env=env, check=False)
                        print("PTT-RELEASE: Beep-Modulation abgeschlossen.")
                time.sleep(0.050)             
            code = "4101000000000006" if radio.is_tx else "4100000000000006"
            if radio.ser: 
                radio.ser.write(bytes.fromhex(code))
            radio.ptt_start_time = time.time()
            radio.save_config()
        elif cmd == 'TOGGLE_RB':
            radio.config["roger_beep_enabled"] = not radio.config.get("roger_beep_enabled", True)
            print(f"ROGERBEEP-SCHALTER: Neuer Status ist {radio.config['roger_beep_enabled']}")
            radio.save_config()
        elif cmd == 'SSCAN':
            radio.sw_scan_active = not radio.sw_scan_active
            if radio.sw_scan_active: 
                threading.Thread(target=radio.sw_scan_loop, daemon=True).start()
        elif cmd.startswith('SETSPEED_'):
            radio.config["scan_speed"] = float(cmd.split('_')[1]) / 1000.0
            radio.save_config()
        elif cmd == 'S':
            radio.ignore_until = time.time() + 1.2
            if radio.ser:
                radio.ser.write(bytes.fromhex("4100010001000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex("4100000001000006"))
                time.sleep(0.4)
                radio.ser.write(bytes.fromhex("4100010002000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex("4100000002000006"))
                time.sleep(0.4)
                radio.ser.write(bytes.fromhex("410001001A000006"))
                time.sleep(2.2)
                radio.ser.write(bytes.fromhex("410000001A000006"))
            radio.current_ch = 1
            radio.mode_idx = 2
            radio.save_config()
        elif cmd.startswith('K'):
            digit = cmd[1:]
            if digit in key_codes:
                if radio.ser:
                    radio.ser.write(bytes.fromhex(f"41000100{key_codes[digit]}000006"))
                    time.sleep(0.08)
                    radio.ser.write(bytes.fromhex(f"41000000{key_codes[digit]}000006"))
                else: 
                    print(f"SIMULATION: Keypad {digit} emuliert.")
                if len(radio.key_buffer) == 0: 
                    radio.key_input_start_time = time.time()
                radio.key_buffer += digit
                if len(radio.key_buffer) == 2:
                    val = int(radio.key_buffer)
                    if 1 <= val <= 40: 
                        radio.current_ch = val
                    radio.key_buffer = ""
        elif cmd in p_codes:
            label_key = f"{cmd.lower()}_label"
            current_label = radio.config.get(label_key, "").upper()
            if "VOX" in current_label:
                if radio.config.get("vox_enabled", False):
                    old_vol = radio.config.get("vol", 85)
                    os.system("amixer set Master 0%") 
                    radio.audio_mute = True
                    
                    def delayed_vox_off():
                        radio.send_cmd(f"41000100{p_codes[cmd]}000006", f"41000000{p_codes[cmd]}000006")
                        radio.config["vox_enabled"] = False
                        radio.force_rx = True 
                        radio.save_config()
                        # REPARATUR: Diese Zeilen gehoeren bündig IN den Thread!
                        time.sleep(2.5)
                        os.system(f"amixer set Master {old_vol}%")
                        radio.audio_mute = False
                        
                    threading.Thread(target=delayed_vox_off, daemon=True).start()
                else:
                    if radio.ser:
                        radio.ser.write(bytes.fromhex(f"41000100{p_codes[cmd]}000006"))
                        time.sleep(0.08)
                        radio.ser.write(bytes.fromhex(f"41000000{p_codes[cmd]}000006"))
                    radio.config["vox_enabled"] = True
                    radio.save_config()
            else:
                if radio.ser:
                    radio.ser.write(bytes.fromhex(f"41000100{p_codes[cmd]}000006"))
                    time.sleep(0.08)
                    radio.ser.write(bytes.fromhex(f"41000000{p_codes[cmd]}000006"))

                    
        # =========================================================================
        # 1. HARDWARE-INTELLIGENTER PEGEL-TRACKER (DREIFACH-MAKRO AKTIVIERТ)
        # =========================================================================
        elif cmd == "SQUELCHUP":
            if not radio.config.get("full_sync_active", False):
                if radio.config.get("asq_enabled", False):
                    radio.config["current_asq_level"] = min(radio.config.get("max_asq_steps", 9), radio.config.get("current_asq_level", 1) + 1)
                else:
                    radio.config["current_sq_level"] = min(radio.config.get("max_sq_steps", 80), radio.config.get("current_sq_level", 0) + 1)
                radio.save_config()
            
            # KORREKTUR: Das vollständige Dreier-Makro für SQUELCHUP ('0x24, 0x26, 0x24')
            if radio.ser:
                # 1. SQL-Menü öffnen (0x24)
                radio.ser.write(bytes.fromhex("4100010024000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000024000006"))
                time.sleep(0.080)
                # 2. Eine Stufe nach oben schalten (0x26)
                radio.ser.write(bytes.fromhex("4100010026000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000026000006"))
                time.sleep(0.080)
                # 3. SQL-Menü schliessen und sichern (0x24)
                radio.ser.write(bytes.fromhex("4100010024000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000024000006"))

        elif cmd == "SQUELCHDOWN":
            if not radio.config.get("full_sync_active", False):
                if radio.config.get("asq_enabled", False):
                    radio.config["current_asq_level"] = max(1, radio.config.get("current_asq_level", 1) - 1)
                else:
                    radio.config["current_sq_level"] = max(0, radio.config.get("current_sq_level", 0) - 1)
                radio.save_config()
                
            # KORREKTUR: Das vollständige Dreier-Makro für SQUELCHDOWN ('0x24, 0x27, 0x24')
            if radio.ser:
                # 1. SQL-Menü öffnen (0x24)
                radio.ser.write(bytes.fromhex("4100010024000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000024000006"))
                time.sleep(0.080)
                # 2. Eine Stufe nach unten schalten (0x27)
                radio.ser.write(bytes.fromhex("4100010027000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000027000006"))
                time.sleep(0.080)
                # 3. SQL-Menü schliessen und sichern (0x24)
                radio.ser.write(bytes.fromhex("4100010024000006"))
                time.sleep(0.080)
                radio.ser.write(bytes.fromhex("4100000024000006"))

        # =========================================================================
        # 2. DER ULTIMATIVE REPARIERTE SUPER-SYNC THREAD (MASTER-REZEPT)
        # =========================================================================
        elif cmd == 'FULL_ASQ_SQ_SYNC':
            radio.squelch_timeout_until = time.time() + 25.0
            radio.config["full_sync_active"] = True
            radio.save_config()
            
            gemerkter_kanal = radio.current_ch
            gemerkter_mode_idx = radio.mode_idx
            old_vol = radio.config.get("vol", 85)
            
            print("SUPER-SYNC: Starte exakte Eichung nach Master-Rezept...")
            os.system("amixer set Master 0%") # 1. MUTE SOFORT AKTIVIEREN

            def run_super_sync_process():
                # 2. WECHSEL STUR AUF FM
                while MODES[radio.mode_idx].upper() != "FM":
                    radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
                    current_mode = MODES[radio.mode_idx].upper()
                    if radio.config.get("skip_pa", False) and current_mode == "PA": continue
                    if radio.config.get("skip_cw", False) and current_mode == "CW": continue
                    if radio.ser:
                        radio.ser.write(bytes.fromhex("410001000D000006"))
                        time.sleep(0.08)
                        radio.ser.write(bytes.fromhex("410000000D000006"))
                        time.sleep(0.3)

                # 3. ASQ-CHECK: WENN ASQ AKTIV IST, SCHALTEN WIR IHN JETZT AUS
                if radio.config.get("asq_enabled", False) and radio.ser:
                    print("SUPER-SYNC: ASQ ist aktiv. Schalte ASQ temporaer aus...")
                    radio.ser.write(bytes.fromhex("4100010024000006")) # 2s halten fuer Toggle
                    time.sleep(2.0)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.5)

                # 4. MANUELLEN SQUELCH AUF NULL JAGEN (Deine 80 Express-Klicks)
                print("SUPER-SYNC: Jage manuellen Squelch im Express-Takt auf 0...")
                if radio.ser:
                    radio.ser.write(bytes.fromhex("4100010024000006")) # Menü auf
                    time.sleep(0.15)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.15)
                
                for _ in range(80):
                    if radio.ser:
                        radio.ser.write(bytes.fromhex("4100010027000006")) # DOWN Taste
                        time.sleep(0.060)
                        radio.ser.write(bytes.fromhex("4100000027000006"))
                        time.sleep(0.140)
                
                if radio.ser:
                    radio.ser.write(bytes.fromhex("4100010024000006")) # Menü zu
                    time.sleep(0.15)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.5)

                # 5. ASQ RE-AKTIVIEREN & AUF STUFE 1 ZWINGEN
                print("SUPER-SYNC: Schalte ASQ wieder ein und fahre auf Level 1...")
                if radio.ser:
                    radio.ser.write(bytes.fromhex("4100010024000006")) # ASQ wieder ein (2s halten)
                    time.sleep(2.0)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.5)
                    radio.ser.write(bytes.fromhex("4100010024000006")) # ASQ-Menü oeffnen
                    time.sleep(0.15)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.15)
                    
                    for _ in range(15): # 15 Klicks nach unten fuer Level 1
                        radio.ser.write(bytes.fromhex("4100010027000006"))
                        time.sleep(0.060)
                        radio.ser.write(bytes.fromhex("4100000027000006"))
                        time.sleep(0.140)
                        
                    radio.ser.write(bytes.fromhex("4100010024000006")) # ASQ-Menü schliessen
                    time.sleep(0.15)
                    radio.ser.write(bytes.fromhex("4100000024000006"))
                    time.sleep(0.5)
                # 6. REFERENZ-WERTE IM RAM ABSPEICHERN
                with radio.lock:
                    radio.config["current_sq_level"] = 0
                    radio.config["current_asq_level"] = 1
                    
                    ziel_mode = MODES[gemerkter_mode_idx].upper()
                    if ziel_mode in ["AM", "FM"]:
                        radio.config["asq_enabled"] = True
                        radio.config["asq_memory"] = True  
                    else:
                        radio.config["asq_enabled"] = False
                        radio.config["asq_memory"] = True  
                    
                    radio.config["full_sync_active"] = False
                    radio.save_config()
                    
                    # 7. ZURÜCKBEAMEN AUF URSPRUNGSMODULATION
                    print("SUPER-SYNC: Restauriere Modulation...")
                    while radio.mode_idx != gemerkter_mode_idx:
                        radio.mode_idx = (radio.mode_idx + 1) % len(MODES)
                        if radio.ser:
                            radio.ser.write(bytes.fromhex("410001000D000006"))
                            time.sleep(0.08)
                            radio.ser.write(bytes.fromhex("410000000D000006"))
                            time.sleep(0.3)
                    
                    # 8. KANAL ÜBER KEYPAD RE-SYNCHRONISIEREN
                    print(f"SUPER-SYNC: Re-Synchronisiere Kanal {gemerkter_kanal}...")
                    ch_str = str(gemerkter_kanal).zfill(2)
                    for digit in ch_str:
                        if digit in key_codes and radio.ser:
                            radio.ser.write(bytes.fromhex(f"41000100{key_codes[digit]}000006"))
                            time.sleep(0.08)
                            radio.ser.write(bytes.fromhex(f"41000000{key_codes[digit]}000006"))
                            time.sleep(0.15)
                    
                    radio.current_ch = gemerkter_kanal
                    radio.config["full_sync_active"] = False
                    radio.save_config()
                
                # Audio reaktivieren
                os.system(f"amixer set Master {old_vol}%")
                print("SUPER-SYNC: Eichungs-Prozess erfolgreich abgeschlossen!")

            threading.Thread(target=run_super_sync_process, daemon=True).start()

        # =========================================================================
        # PARAGEI-MODUL: COUTEST VOICE KEYER & SIGNAL REPORT (BÜNDIG GEITTET)
        # =========================================================================
        elif cmd == 'VOICE_REC':
            # 1. Wenn wir schon aufnehmen, stoppen wir es sofort im RAM und im System
            if getattr(radio, 'is_recording_live', False):
                print("PAPAGEI: Partner-Aufnahme vorzeitig gestoppt.")
                radio.is_recording_live = False
                subprocess.run(["pkill", "-x", "arecord"], check=False)
            else:
                # 2. Startet die Aufnahme und zündet sofort die RAM-Flagge fürs UI
                print("PAPAGEI: Nehme QSO-Partner vom Albrecht-Empfang auf...")
                radio.is_recording_live = True
                rec_path = os.path.join(SCRIPT_DIR, "ARC", "qso_rx.wav")
                
                env = os.environ.copy()
                env['PULSE_SOURCE'] = '@DEFAULT_AUDIO_SINK@.monitor'
                subprocess.Popen(["arecord", "-d", "10", "-f", "cd", rec_path, "-V", "none"], env=env)

        elif cmd == 'VOICE_PLAY':
            def run_voice_play():
                play_path = os.path.join(SCRIPT_DIR, "ARC", "qso_rx.wav")
                if os.path.exists(play_path):
                    print("PAPAGEI: Taste PTT und spiele Signal-Report mit intelligentem Mumble-Holzhammer ab...")
                    
                    mumble_client_id = None
                    mumble_sink_input_ids = []
                    
                    try:
                        # --- SCHRITT 1: DIE CLIENT-ID VON MUMBLE DYNAMISCH ERMITTELN ---
                        res_clients = subprocess.run(["pactl", "list", "short", "clients"], capture_output=True, text=True).stdout
                        for line in res_clients.split('\n'):
                            if "mumble" in line.lower():
                                parts = line.split()
                                # REPARATUR: Wir prüfen das ERSTE ELEMENT der Liste auf eine Zahl!
                                if parts and parts[0].isdigit():
                                    mumble_client_id = parts[0] # Extrahiert die reine ID (z.B. "106")
                                    print(f"[HOLZHAMMER-RPLAY] Mumble-Client-ID lokalisiert: {mumble_client_id}")
                                    break
                        
                        # --- SCHRITT 2: DEN DAZUGEHÖRIGEN SINK-INPUT ISOLIEREN ---
                        if mumble_client_id:
                            res_sinks = subprocess.run(["pactl", "list", "short", "sink-inputs"], capture_output=True, text=True).stdout
                            for line in res_sinks.split('\n'):
                                parts = line.split()
                                if len(parts) >= 3:
                                    # Spalte 3 (Index 2) hält die Client-ID. Wir vergleichen sie!
                                    if parts[2] == mumble_client_id:
                                        mumble_sink_input_ids.append(parts[0]) # Speichert die Sink-Input-ID (z.B. "107")
                            
                        # --- SCHRITT 3: RADIKALER MUTE VOR DEM SENDEN ---
                        for stream_id in mumble_sink_input_ids:
                            subprocess.run(["pactl", "set-sink-input-mute", stream_id, "1"], check=False)
                        print(f"[HOLZHAMMER-RPLAY] {len(mumble_sink_input_ids)} Mumble-Sink-Inputs (IDs: {mumble_sink_input_ids}) stummgeschaltet.")
                    except Exception as e:
                        print(f"Holzhammer-RPLAY Mute fehlgeschlagen: {e}")
                    
                    # --- SENDER SCHARF SCHALTEN (PTT via CAT) ---
                    with radio.lock:
                        radio.is_tx = True
                        radio.ptt_start_time = time.time()
                        if radio.ser: radio.ser.write(bytes.fromhex("4101000000000006"))
                    
                    # --- SIGNAL-REPORT VOM PAPAGEI ABSPIELEN ---
                    env = os.environ.copy()
                    env['PULSE_SINK'] = 'mono-fallback'
                    subprocess.run(["paplay", "--latency-msec=1", play_path], env=env, check=False)
                    
                    # --- ROGERBEEP ANKOPPELN ---
                    chosen_beep = radio.config.get("current_beep", "None")
                    if chosen_beep != "None" and radio.config.get("roger_beep_enabled", True):
                        beep_path = os.path.join(SCRIPT_DIR, "beeps", chosen_beep)
                        if os.path.exists(beep_path):
                            subprocess.run(["paplay", "--latency-msec=1", beep_path], env=env, check=False)
                    
                    # --- SENDER ZURÜCK AUF EMPFANG (RX via CAT) ---
                    with radio.lock:
                        radio.is_tx = False
                        if radio.ser: radio.ser.write(bytes.fromhex("4100000000000006"))
                    
                    # --- SCHRITT 4: UNMUTE ---
                    try:
                        for stream_id in mumble_sink_input_ids:
                            subprocess.run(["pactl", "set-sink-input-mute", stream_id, "0"], check=False)
                        print("[HOLZHAMMER-RPLAY] Mumble-Sink-Inputs wieder geoeffnet.")
                    except Exception as e:
                        print(f"Holzhammer-RPLAY Unmute fehlgeschlagen: {e}")
                        
                    print("PAPAGEI: Wiedergabe beendet.")
            threading.Thread(target=run_voice_play, daemon=True).start()


        elif cmd == 'CQ_REC':
            if getattr(radio, 'is_recording_live', False):
                print("PAPAGEI: CQ-Aufnahme vorzeitig gestoppt.")
                radio.is_recording_live = False 
                subprocess.run(["pkill", "-x", "pw-record"], check=False)
                subprocess.run(["pkill", "-x", "arecord"], check=False)
            else:
                print("PAPAGEI: Starte ungelinkten PipeWire-Recorder...")
                radio.is_recording_live = True
                cq_path = os.path.join(SCRIPT_DIR, "ARC", "cq_loop.wav")
                
                proc = subprocess.Popen([
                    "pw-record",
                    "--target", "0",
                    "--format", "s16",
                    "--rate", "22050",
                    "--channels", "1",
                    str(cq_path)
                ])
                
                time.sleep(0.060)
                
                try:
                    res_links = subprocess.run(["pw-link", "-i"], capture_output=True, text=True).stdout
                    record_ports = [l.strip() for l in res_links.split('\n') if "pw-record" in l.lower() or "record" in l.lower()]
                    if record_ports:
                        target_port = record_ports[-1]
                        subprocess.run(["pw-link", "Mumble:output_FL", target_port], check=False)
                        print("[PAPAGEI-WEICHE GEKOPPELT]")
                except Exception as e:
                    print(f"Fehler beim dynamischen PipeWire-Link: {e}")

                def auto_stop_cq_rec():
                    if proc.poll() is None:
                        print("PAPAGEI: 12s Limit erreicht. Beende CQ-Aufnahme.")
                        radio.is_recording_live = False
                        subprocess.run(["pkill", "-x", "pw-record"], check=False)
                threading.Timer(12.0, auto_stop_cq_rec).start()

        elif cmd == 'CQ_CALL':
            def run_cq_call():
                play_path = os.path.join(SCRIPT_DIR, "ARC", "cq_loop.wav")
                if os.path.exists(play_path):
                    print("PAPAGEI: Starte CQ-Ruf mit intelligentem Mumble-Holzhammer...")
                    
                    mumble_client_id = None
                    mumble_sink_input_ids = []
                    
                    try:
                        # --- SCHRITT 1: DIE CLIENT-ID VON MUMBLE FINDEN ---
                        res_clients = subprocess.run(["pactl", "list", "short", "clients"], capture_output=True, text=True).stdout
                        for line in res_clients.split('\n'):
                            if "mumble" in line.lower():
                                parts = line.split()
                                if parts and parts[0].isdigit():
                                    mumble_client_id = parts[0] # Findet z.B. "106"
                                    print(f"[HOLZHAMMER] Mumble-Client-ID lokalisiert: {mumble_client_id}")
                                    break
                        
                        # --- SCHRITT 2: DEN DAZUGEHÖRIGEN SINK-INPUT FINDEN ---
                        if mumble_client_id:
                            res_sinks = subprocess.run(["pactl", "list", "short", "sink-inputs"], capture_output=True, text=True).stdout
                            for line in res_sinks.split('\n'):
                                parts = line.split()
                                # Ein regulärer PipeWire Sink-Input hat mindestens 5 Spalten (ID, Sink, Client, ...)
                                if len(parts) >= 5:
                                    # Spalte 3 (Index 2) ist die Client-ID im Sink-Input
                                    if parts[2] == mumble_client_id:
                                        mumble_sink_input_ids.append(parts[0]) # Speichert die "107"
                            
                        # --- SCHRITT 3: RADIKALER MUTE ---
                        for stream_id in mumble_sink_input_ids:
                            subprocess.run(["pactl", "set-sink-input-mute", stream_id, "1"], check=False)
                        print(f"[HOLZHAMMER] {len(mumble_sink_input_ids)} Mumble-Sink-Inputs (IDs: {mumble_sink_input_ids}) stummgeschaltet.")
                    except Exception as e:
                        print(f"Holzhammer-Mute fehlgeschlagen: {e}")
                    
                    # --- SENDER SCHARF SCHALTEN (PTT via CAT) ---
                    with radio.lock:
                        radio.is_tx = True
                        radio.ptt_start_time = time.time()
                        if radio.ser: radio.ser.write(bytes.fromhex("4101000000000006"))
                    
                    # --- CQ-KONSERVE ABSPIELEN ---
                    env = os.environ.copy()
                    env['PULSE_SINK'] = 'mono-fallback' 
                    subprocess.run(["paplay", "--latency-msec=1", play_path], env=env, check=False)
                    
                    # --- ROGERBEEP ANKOPPELN ---
                    chosen_beep = radio.config.get("current_beep", "None")
                    if chosen_beep != "None" and radio.config.get("roger_beep_enabled", True):
                        beep_path = os.path.join(SCRIPT_DIR, "beeps", chosen_beep)
                        if os.path.exists(beep_path):
                            subprocess.run(["paplay", "--latency-msec=1", beep_path], env=env, check=False)
                    
                    # --- SENDER ZURÜCK AUF EMPFANG (RX via CAT) ---
                    with radio.lock:
                        radio.is_tx = False
                        if radio.ser: radio.ser.write(bytes.fromhex("4100000000000006"))
                    
                    # --- SCHRITT 4: UNMUTE ---
                    try:
                        for stream_id in mumble_sink_input_ids:
                            subprocess.run(["pactl", "set-sink-input-mute", stream_id, "0"], check=False)
                        print("[HOLZHAMMER] Mumble-Sink-Inputs wieder geoeffnet.")
                    except Exception as e:
                        print(f"Holzhammer-Unmute fehlgeschlagen: {e}")
                        
                    print("PAPAGEI: CQ-Ruf abgeschlossen.")
            threading.Thread(target=run_cq_call, daemon=True).start()


        # =========================================================================
        # CUSTOM MODUL: TERMINAL BEFEHLE FÜR ANTENNENSWITCH, REBOOTS ETC.
        # =========================================================================
        elif cmd.startswith('CUST_') and not cmd.endswith('LBL'):
            try:
                taste_nr = cmd.split('_')[1]
                cmd_key = f"cust_cmd_{taste_nr}"
                terminal_befehl = radio.config.get(cmd_key, "").strip()
                if terminal_befehl:
                    print(f"CUSTOM-CMD: Taste {taste_nr} -> '{terminal_befehl}'")
                    os.system(f"{terminal_befehl} &")
            except Exception as e:
                print(f"Fehler bei Custom-Terminal-Befehl: {e}")
        # --- SONDERFALL 1: MUTE COMBINATION BUTTON (AUTARK VOR DER SCHLEIFE) ---
        elif cmd == "MUTECOMBBTN":
            current_mode = MODES[radio.mode_idx].upper()
            if current_mode in ["AM", "FM", "USB", "LSB", "CW"]:
                radio.mute_timeout_until = time.time() + 2.0
                print("TIMEOUT: MUTE-Toggle aktiv. UI für 2s blockiert.")
                radio.config["mute_enabled"] = not radio.config.get("mute_enabled", False)
                radio.save_config()
                
                def run_mute_macro_fixed():
                    radio.macro_active = True
                    for h_cl in ["31", "1E"]:
                        if radio.ser:
                            radio.ser.write(bytes.fromhex(f"41000100{h_cl}000006"))
                            time.sleep(0.150)
                            radio.ser.write(bytes.fromhex(f"41000000{h_cl}000006"))
                        time.sleep(0.050)
                    radio.macro_active = False

                threading.Thread(target=run_mute_macro_fixed, daemon=True).start()

        # --- NUN DER REST DER SUPERKEY-MAKROS (Komplett ohne Dopplungen) ---
        elif cmd in superkey_codes:
            label_key = f"{cmd.lower()}_label"
            current_label = radio.config.get(label_key, "").upper()
            macro_string = superkey_codes[cmd]
            commands = [c.strip() for c in macro_string.split(",")]
            
            for single_cmd in commands:
                if not single_cmd: 
                    continue
                if ":" in single_cmd: 
                    hex_part, duration_part = single_cmd.split(":")
                    duration = float(duration_part)
                else: 
                    hex_part = single_cmd
                    duration = 0.150
                hex_clean = hex_part.replace("0x", "").zfill(2)

                # --- SCHLEIFEN-SONDERFALL 1: VOX TOGGLE ---
                if "VOX_TOGGLE" in current_label or cmd == "VOX_TOGGLE":
                    if radio.config.get("vox_enabled", False):
                        old_vol = radio.config.get("vol", 85)
                        os.system("amixer set Master 0%") 
                        radio.audio_mute = True
                        radio.config["vox_enabled"] = False
                        radio.save_config()
                        def delayed_vox_superkey_off_backup(dur, vol_back):
                            time.sleep(2.5)
                            print("VOX-FAILSAFE: Sende physischen HEX-Befehl...")
                            if radio.ser:
                                with radio.lock:
                                    radio.ser.write(bytes.fromhex("4100010028000006"))
                                    time.sleep(dur)
                                    radio.ser.write(bytes.fromhex("4100000028000006"))
                                    radio.force_rx = True
                            os.system(f"amixer set Master {vol_back}%")
                            radio.audio_mute = False
                        threading.Thread(target=delayed_vox_superkey_off_backup, args=(duration, old_vol), daemon=True).start()
                    else:
                        if radio.ser:
                            radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                            time.sleep(duration)
                            radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                        radio.config["vox_enabled"] = True
                        radio.save_config()

                # --- SCHLEIFEN-SONDERFALL 2: ASQ TOGGLE (STILLE 2-SEKUNDEN SPERRE) ---
                elif cmd == "ASQ_ON_OFF":
                    current_mode = MODES[radio.mode_idx].upper()
                    if current_mode in ["AM", "FM"]:
                        radio.asq_timeout_until = time.time() + 2.0
                        print("TIMEOUT: ASQ-Toggle aktiv. UI für 2s blockiert.")
                        
                        if radio.config.get("asq_enabled", False):
                            def delayed_asq_off(h_clean, dur_val):
                                radio.send_cmd(f"41000100{h_clean}000006", "00")
                                time.sleep(dur_val)
                                radio.send_cmd(f"41000000{h_clean}000006", "00")
                                time.sleep(0.5)
                                
                                with radio.lock:
                                    radio.config["asq_enabled"] = False
                                    radio.config["asq_memory"] = False  
                                    radio.save_config()
                            threading.Thread(target=delayed_asq_off, args=(hex_clean, duration), daemon=True).start()
                        else:
                            if radio.ser:
                                radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                                time.sleep(duration)
                                radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                            radio.config["asq_enabled"] = True
                            radio.config["asq_memory"] = True   
                            radio.save_config()

                # --- SCHLEIFEN-SONDERFALL 3: HARDWARE LOCK / UNLOCK ---

                elif cmd == "LOCKDEV":
                    is_locked = radio.config.get("lock_enabled", False)
                    radio.config["lock_enabled"] = not is_locked
                    radio.save_config()
                    if radio.ser:
                        radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                        time.sleep(duration)
                        radio.ser.write(bytes.fromhex(f"41000000{hex_clean}000006"))
                    else: 
                        print("SIMULATION: Lock emuliert.")

                # --- STANDARD EMULATION FÜR ALLE ANDEREN NORMALEN MACRO-TASTEN ---
                else:
                    if radio.ser:
                        radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                        time.sleep(duration)
                        radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                    time.sleep(0.050)

        # --- CONFIG- & INTERNE ROUTEN (ABSOLUT BÜNDIG & STRUCT-SAVE) ---
        elif cmd.startswith('SET_'):
            val = request.args.get('val')

            if cmd == "SET_CURRENT_BAND":
                radio.config["current_band"] = val
                
                # --- DYNAMISCHE STRUKTURIERUNG DER HARDWARE-MODI ---
                #global MODES
                if val == "UK":
                    # Exakte Albrecht-Reihenfolge für das U-Band:
                    MODES = ["PA", "CW", "FM", "UK", "AM", "USB", "LSB"]
                    print("[HARDWARE] Modus-Reihenfolge auf UK-Norm umgestellt.")
                else:
                    # Standard-Reihenfolge für alle anderen Länder:
                    MODES = ["PA", "CW", "FM", "AM", "USB", "LSB"]
                    print("[HARDWARE] Modus-Reihenfolge auf EU-Standard zurückgesetzt.")

                # Failsafe: Wenn wir Kanäle verlassen, die es im neuen Band nicht gibt
                if val == "IN" and radio.current_ch > 27:
                    radio.current_ch = 1
                elif val != "DE" and radio.current_ch > 40:
                    radio.current_ch = 1
                
                # Sicherstellen, dass der mode_idx nach dem Umbau nicht außerhalb des Arrays liegt
                if radio.mode_idx >= len(MODES):
                    radio.mode_idx = 2 # Fallback auf FM (Index 2)
                    
                radio.save_config()
                print(f"BAND-UMSCHALTUNG: Aktiviertes Band: {val}, Aktueller Modus-Index: {radio.mode_idx}")
            
            if cmd == "SET_ACTIVE_P_BLOCK":
                radio.config["active_p_block"] = val
                radio.save_config()
                print(f"API-SETTER: active_p_block erfolgreich auf '{val}' umgestellt.")
            
            elif "VOX" in cmd: radio.config["vox_enabled"] = (val.lower() == 'true')
            elif "MUTE" in cmd: radio.config["mute_enabled"] = (val.lower() == 'true')
            elif "ASQ" in cmd: radio.config["asq_enabled"] = (val.lower() == 'true')
            elif "LOCK" in cmd: radio.config["lock_enabled"] = (val.lower() == 'true')
            elif "BEEP" in cmd: radio.config["current_beep"] = val
            elif "PTTHOTKEY" in cmd: radio.config["ptt_hotkey"] = val
            elif "MW_LABEL" in cmd: radio.config["mw_label"] = val
                
            elif "SKIP" in cmd: 
                key_name = "skip_pa" if "PA" in cmd else "skip_cw"
                radio.config[key_name] = (val.lower() == 'true')
            elif "CLAR" in cmd:
                if "OFFSET" in cmd: radio.config["clar_offsets"][str(radio.current_ch).zfill(2)] = int(val)
                else: radio.config["clar_step"] = val
            else: 
                parts = cmd.split('_')
                if len(parts) >= 2:
                    if "CUST" in cmd:
                        label_name = cmd.lower().replace("set_", "").replace("_label", "")
                        radio.config[label_name] = val
                        print(f"API-SICKERUNG: Custom-Variable '{label_name}' felsenfest auf '{val}' gesetzt.")
                    else:
                        radio.config[f"{parts[1].lower()}_label"] = val
            radio.save_config()

        elif cmd.startswith('T'): 
            radio.config["ptt_timeout"] = int(cmd[1:])
            radio.save_config()

        elif cmd.startswith('SETGAIN_'):
            parts = cmd.split('_')
            if len(parts) == 3: 
                radio.config[f"fft_{parts[1].lower()}_gain"] = int(parts[2])
                radio.save_config() 

        elif cmd == 'MW_TOGGLE':
            radio.mw_active = not getattr(radio, 'mw_active', False)
            if radio.mw_active: 
                radio.stop_sw_scan()
                threading.Thread(target=mw_scan_loop, args=(radio,), daemon=True).start()

        if radio.is_tx and (time.time() - radio.ptt_start_time >= radio.config["ptt_timeout"]):
            radio.is_tx = False
            radio.save_config()
            if radio.ser: 
                radio.ser.write(bytes.fromhex("4100000000000006"))
            if 'play_roger_beep' in locals() or 'play_roger_beep' in globals():
                play_roger_beep()

    # --- STATUS RÜCKGABE (GANZ UNTEN IN DER ROUTE, AUSSERHALB LOCK!) ---
    if len(radio.key_buffer) == 1 and (time.time() - getattr(radio, 'key_input_start_time', 0) >= 10.0):
        radio.key_buffer = ""
        print("KEYPAD-TIMEOUT: Puffer geloescht.")

    current_ch_str = str(radio.current_ch).zfill(2)
    current_channel_offset = radio.config["clar_offsets"].get(current_ch_str, 0)
    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    
    now = time.time()
    sq_remains = max(0, int(radio.squelch_timeout_until - now))
    asq_remains = max(0, int(radio.asq_timeout_until - now))
    mute_remains = max(0, int(radio.mute_timeout_until - now))

    return jsonify({
        "CH": current_ch_str, 
        "MODE": MODES[radio.mode_idx], 
        "PTT": "ON" if radio.is_tx else "OFF", 
        "VOX_TX": radio.is_device_sending,
        "VOX_ENABLED": radio.config.get("vox_enabled", False), 
        "MUTE_ENABLED": radio.config.get("mute_enabled", False), 
        "ASQ_ENABLED": radio.config.get("asq_enabled", False),
        "REMAINING": max(0, rem), 
        "BUSY": radio.is_rx, 
        "SW_SCAN": radio.sw_scan_active, 
        "VOL": radio.config.get("vol", 50),
        "SKIP_PA": radio.config.get("skip_pa", False), 
        "SKIP_CW": radio.config.get("skip_cw", False), 
        "CLAR_STEP": radio.config.get("clar_step", "STEP"), 
        "CLAR_OFFSET": current_channel_offset,
        "LOCK_ENABLED": radio.config.get("lock_enabled", False), 
        "MW_SCAN": getattr(radio, 'mw_active', False), 
        "KEY_BUF": radio.key_buffer,
        "PTT_HOTKEY": radio.config.get("ptt_hotkey", "F6"), 
        "CURRENT_BEEP": radio.config.get("current_beep", "None"),
        "SIMULATION": True if radio.ser is None else False,
        "ROGER_BEEP_ENABLED": radio.config.get("roger_beep_enabled", True),
        "SQ_TIMEOUT": sq_remains,
        "ASQ_TIMEOUT": asq_remains,
        "MUTE_TIMEOUT": mute_remains,
        "SQ_LEVEL": radio.config.get("current_sq_level", 0),
        "AS_LEVEL": radio.config.get("current_asq_level", 1),
        "MAX_SQ": radio.config.get("max_sq_steps", 80),
        "MAX_ASQ": radio.config.get("max_asq_steps", 9),
        "ACTIVE_P_BLOCK": radio.config.get("active_p_block", "standard"),
        "AUDIO_RECORDING": getattr(radio, 'is_recording_live', False),
        "CURRENT_BAND": radio.config.get("current_band", "EU")
    })
@app.route('/api/config/override', methods=['POST'])
def api_config_override():
    try:
        data = request.get_json()
        if not data: 
            return jsonify({"status": "error", "message": "Keine Daten"}), 400
        mapping = {"toggle_vox": "vox_enabled", "toggle_mute": "mute_enabled", "toggle_asq": "asq_enabled", "toggle_lock": "lock_enabled"}
        with radio.lock:
            for json_key, config_key in mapping.items():
                if data.get(json_key) is True: 
                    radio.config[config_key] = not radio.config.get(config_key, False)
            radio.save_config()
            current_ch_str = str(radio.current_ch).zfill(2)
            rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
            
            # KORREKTUR: Timeouts auch hier für die Rückgabe berechnen!
            now = time.time()
            sq_remains = max(0, int(radio.squelch_timeout_until - now))
            asq_remains = max(0, int(radio.asq_timeout_until - now))
            mute_remains = max(0, int(radio.mute_timeout_until - now))
            
            # KORREKTUR: Das JSON-Paket komplett synchron mit den neuen Variablen beladen!
            return jsonify({
                "CH": current_ch_str, 
                "MODE": MODES[radio.mode_idx], 
                "PTT": "ON" if radio.is_tx else "OFF", 
                "VOX_TX": radio.is_device_sending, 
                "VOX_ENABLED": radio.config.get("vox_enabled", False), 
                "ASQ_ENABLED": radio.config.get("asq_enabled", False), 
                "MUTE_ENABLED": radio.config.get("mute_enabled", False), 
                "REMAINING": max(0, rem), 
                "BUSY": radio.is_rx, 
                "SW_SCAN": radio.sw_scan_active, 
                "VOL": radio.config.get("vol", 50), 
                "SKIP_PA": radio.config.get("skip_pa", False), 
                "SKIP_CW": radio.config.get("skip_cw", False), 
                "CLAR_STEP": radio.config.get("clar_step", "STEP"), 
                "CLAR_OFFSET": radio.config["clar_offsets"].get(current_ch_str, 0), 
                "LOCK_ENABLED": radio.config.get("lock_enabled", False), 
                "MW_SCAN": getattr(radio, 'mw_active', False), 
                "KEY_BUF": radio.key_buffer, 
                "PTT_HOTKEY": radio.config.get("ptt_hotkey", "F6"), 
                "CURRENT_BEEP": radio.config.get("current_beep", "None"),
                "ROGER_BEEP_ENABLED": radio.config.get("roger_beep_enabled", True),
                "SQ_TIMEOUT": sq_remains,
                "ASQ_TIMEOUT": asq_remains,
                "MUTE_TIMEOUT": mute_remains,
                "SQ_LEVEL": radio.config.get("current_sq_level", 0),
                "AS_LEVEL": radio.config.get("current_asq_level", 1),
                "MAX_SQ": radio.config.get("max_sq_steps", 80),
                "MAX_ASQ": radio.config.get("max_asq_steps", 9),
                "ACTIVE_P_BLOCK": radio.config.get("active_p_block", "standard"),
                "AUDIO_RECORDING": getattr(radio, 'is_recording_live', False),
                "CURRENT_BAND": radio.config.get("current_band", "EU")
            })
    except Exception as e: 
        return jsonify({"status": "error", "message": str(e)}), 500


def ptt_heartbeat_watchdog(radio):
    global LAST_BROWSER_HEARTBEAT
    print("PTT Heartbeat-Waechter (30 Sek.) aktiv und synchronisiert.")
    while True:
        try:
            if radio.is_tx:
                heartbeat = LAST_BROWSER_HEARTBEAT if LAST_BROWSER_HEARTBEAT is not None else time.time()
                silent_duration = time.time() - heartbeat
                
                if silent_duration >= 30.0:
                    print("PTT VERBINDUNGSABBRUCH! Trenne TX.")
                    with radio.lock:
                        radio.is_tx = False
                        radio.save_config()
                        if radio.ser: 
                            radio.ser.write(bytes.fromhex("4100000000000006"))
                    if 'play_roger_beep' in locals() or 'play_roger_beep' in globals():
                        play_roger_beep()
            time.sleep(0.5)
        except Exception as e:
            print(f"Fehler im Heartbeat-Waechter: {e}")
            time.sleep(2.0)


threading.Thread(target=ptt_heartbeat_watchdog, args=(radio,), daemon=True).start()


def audio_broadcast_task():
    while True:
        try:
            with app.app_context():
                audio_response = get_audio()
                audio_data = audio_response.get_json()
                socketio.emit('audio', {'type': 'audio', 'data': audio_data})
            socketio.sleep(0.085)
        except: 
            socketio.sleep(0.5)

socketio.start_background_task(audio_broadcast_task)


@socketio.on('connect')
def handle_connect():
    print("WebSocket Client verbunden")
    try: 
        emit('status', get_current_status_dict())
    except: 
        pass


def get_current_status_dict():
    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    current_ch_str = str(radio.current_ch).zfill(2)
    
    # NEU: Timeouts für den WebSocket-Status berechnen
    now = time.time()
    sq_remains = max(0, int(radio.squelch_timeout_until - now))
    asq_remains = max(0, int(radio.asq_timeout_until - now))
    mute_remains = max(0, int(radio.mute_timeout_until - now))
    
    return {
        "CH": current_ch_str, 
        "MODE": MODES[radio.mode_idx], 
        "PTT": "ON" if radio.is_tx else "OFF", 
        "VOX_TX": radio.is_device_sending,
        "VOX_ENABLED": radio.config.get("vox_enabled", False), 
        "ASQ_ENABLED": radio.config.get("asq_enabled", False), 
        "MUTE_ENABLED": radio.config.get("mute_enabled", False),
        "REMAINING": max(0, rem), 
        "BUSY": radio.is_rx, 
        "SW_SCAN": radio.sw_scan_active, 
        "VOL": radio.config.get("vol", 50), 
        "LOCK_ENABLED": radio.config.get("lock_enabled", False), 
        "MW_SCAN": getattr(radio, 'mw_active', False), 
        "CLAR_STEP": radio.config.get("clar_step", "STEP"), 
        "CLAR_OFFSET": radio.config["clar_offsets"].get(current_ch_str, 0),
        "PTT_HOTKEY": radio.config.get("ptt_hotkey", "F6"), 
        "CURRENT_BEEP": radio.config.get("current_beep", "None"),
        "ROGER_BEEP_ENABLED": radio.config.get("roger_beep_enabled", True),
        "SQ_TIMEOUT": sq_remains,
        "ASQ_TIMEOUT": asq_remains,
        "MUTE_TIMEOUT": mute_remains,
        "SQ_LEVEL": radio.config.get("current_sq_level", 0),
        "AS_LEVEL": radio.config.get("current_asq_level", 1),
        "MAX_SQ": radio.config.get("max_sq_steps", 80),
        "MAX_ASQ": radio.config.get("max_asq_steps", 9),
        "ACTIVE_P_BLOCK": radio.config.get("active_p_block", "standard"),
        "AUDIO_RECORDING": getattr(radio, 'is_recording_live', False),
        "CURRENT_BAND": radio.config.get("current_band", "EU")
    }

threading.Thread(target=auto_patch_streams, daemon=True).start()

if __name__ == '__main__':
    # Modus-Reihenfolge beim Starten basierend auf dem gespeicherten Band korrigieren
    startup_band = radio.config.get("current_band", "EU")
    if startup_band == "UK":
        MODES = ["PA", "CW", "FM", "UK", "AM", "USB", "LSB"]
        print("[STARTUP] UK-Modus-Matrix erfolgreich geladen.")
        
    print("AE5900 Remote V2 mit WebSocket gestartet")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
