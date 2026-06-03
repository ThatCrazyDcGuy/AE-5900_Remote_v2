from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial
import threading
import time
import json
import os
import numpy as np
import pyaudio
import subprocess
import socket
import sys
import logging
from logging.handlers import RotatingFileHandler


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
        # Client 1 (RX / Später Funk-Eingang)
        os.environ['PULSE_PROP'] = 'node.description="AE_RX" node.name="AE_RX"'
        pa_rx = pyaudio.PyAudio()
        stream_rx = pa_rx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
        
        # Client 2 (TX / Später Mumble-Monitor)
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
        
        # 1. pactl list short im Hintergrund einlesen
        res = subprocess.run(["pactl", "list", "short"], capture_output=True, text=True).stdout
        lines = [l.strip() for l in res.split('\n') if l.strip()]
        
        stereo_target = None
        mono_target = None
        python_node_ids = []
        
        # 2. Den System-Output nach den exakten IDs scannen
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

        print(f"[Wächter] Stereo Monitor ID: {stereo_target}")
        print(f"[Wächter] Mono Mikrofon ID:  {mono_target}")
        print(f"[Wächter] Python Mischer IDs: {python_node_ids}")
        

        if len(python_node_ids) >= 2 and stereo_target and mono_target:
            rx_node = python_node_ids[0] # Der obere Stream (Balken)
            tx_node = python_node_ids[1] # Der untere Stream (TX)
            
            # Wir verschieben die Mischer-Eingänge hart an ihren Platz
            print(f"Zwinge RX-Mischer ({rx_node}) -> Stereo Monitor ({stereo_target})")
            subprocess.run(["pactl", "move-source-output", rx_node, stereo_target], check=False)
            
            print(f"Zwinge TX-Mischer ({tx_node}) -> Mono-Mikrofon ({mono_target})")
            subprocess.run(["pactl", "move-source-output", tx_node, mono_target], check=False)
            
            # 4. MUMBLE VERDRAHTUNG VIA PW-LINK
            mumble_source = "Mumble:output_FL"
            res_links = subprocess.run(["pw-link", "-i"], capture_output=True, text=True).stdout
            python_ports = [l.strip() for l in res_links.split('\n') if "python" in l.lower() or "alsa_capture" in l.lower()]
            
            if len(python_ports) >= 2:
                target = python_ports[1] # Zweiter Port gehört Mumble/TX
                subprocess.run(["pw-link", mumble_source, target], check=False)
                print(f"Mumble-Kabel erfolgreich an Port {target} gelötet.")
                
            print("[SYSTEM-WEICHE PERFEKT REBOOT-SICHER EINGESTELLT]")
        else:
            print("Wächter-Fehler: Konnte die Audio-Knotenpunkte nicht eindeutig isolieren.")
            
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
        self.current_ch = self.config.get("last_ch", 1)
        self.mode_idx = self.config.get("last_mode", 2)
        try:
            self.ser = serial.Serial(PORT, 115200, timeout=0.01)
            print(f"--- AE5900 Master-Emulator ONLINE (Full Feature) ---")
            threading.Thread(target=self.heartbeat_task, daemon=True).start()
            threading.Thread(target=self.listen_loop, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"Serial Fehler: {e}")

    def load_config(self):
        default = {
            "ptt_timeout": 300,
            "last_ch": 1,
            "last_mode": 2,
            "skip_pa": False,
            "skip_cw": False,
            "p1_label": "Not set", "p2_label": "Not set", 
            "p3_label": "Not set", "p4_label": "Not set",
            "scan_speed": 0.5,
            "fft_rx_gain": 25000, "fft_tx_gain": 55000,
            "vox_enabled": False,
            "mute_enabled": False,
            "asq_enabled": False
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                    # Direktes, ungepuffertes Einlesen von der Platte
                    self.config = {**default, **json.load(f)}
                    print("CONFIG: config.json erfolgreich von SD-Karte geladen.")
            except Exception as e: 
                print(f"CONFIG-FEHLER: Konnte config.json nicht parsen, nutze Defaults. Fehler: {e}")
                self.config = default
        else: 
            self.config = default

    def save_config(self):
        # Synchronisiere die aktuellen Werte vor dem Schreiben exakt im RAM
        self.config["last_ch"] = self.current_ch
        self.config["last_mode"] = self.mode_idx
        try:
            # Wir oeffnen die Datei im atomaren Schreibmodus ('w') mit explizitem UTF-8
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
                json.dump(self.config, f, indent=4)
                f.flush() # Erzwingt das sofortige physische Schreiben auf die SD-Karte!
                os.fsync(f.fileno()) # Verhindert, dass das Betriebssystem den Schreibvorgang verzögert
        except Exception as e:
            print(f"CONFIG-FEHLER: Konnte config.json nicht auf SD-Karte schreiben: {e}")


    def heartbeat_task(self):
        while self.ser:
            try:
                if self.ser.in_waiting == 0 and not self.is_tx and not self.force_rx:
                    with self.lock:
                        # Heartbeat-Anfrage
                        hb = bytes.fromhex("41 00 00 00 82 00 00 06")
                        self.ser.write(hb)
                        time.sleep(0.03)
                        
                        # Kanal-Status-Update
                        ch_hex = self.current_ch + 15
                        status = bytes([0xAA, 0x53, 0, 0, 0, 0, 0, 0, 0, 0, ch_hex, 0, 0, 1, 0, 0, 0x06])
                        self.ser.write(status)
            except Exception as e:
                print(f"Heartbeat Fehler: {e}")
                break
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
                        
                        # 1. SIGNAL-ERKENNUNG (S-Meter)
                        self.is_rx = (packet[1] > 0 or packet[2] > 0)

                        # 2. VOX-ERKENNUNG
                        vox_detected = (packet == 0x01)
                        
                        if vox_detected and not self.is_tx:
                            try:
                                if os.path.exists(CONFIG_FILE):
                                    with open(CONFIG_FILE, 'r') as f:
                                        disk_config = json.load(f)
                                        self.config["vox_enabled"] = disk_config.get("vox_enabled", False)
                            except Exception as e:
                                print(f"Fehler beim Live-Config-Read: {e}")

                            # KORREKTUR: Veto nur einlegen, wenn NICHT gerade umgeschaltet wird!
                            if not self.config.get("vox_enabled", False) and not getattr(self, 'is_vox_changing', False):
                                with self.lock:
                                    self.ser.write(bytes.fromhex("4100000000000006"))
                                print("VOX-VETO: Automatisches Senden unterdrueckt (Config-Sync).")
                                vox_detected = False

                        # KORREKTUR: Manueller Abbruch darf den Umschalt-Befehl NICHT blockieren!
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
                self.save_config()
            time.sleep(self.config.get("scan_speed", 0.5))
            while self.is_rx and self.sw_scan_active:
                time.sleep(0.2)
                if self.is_tx:
                    self.sw_scan_active = False
                    break
#            if self.sw_scan_active:
#                time.sleep(1.5) # S-Scan Haltezeit nach Signalverlust (Verzögerung)

        print("Software-Scan beendet.")

    def stop_sw_scan(self):
        self.sw_scan_active = False

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

def mw_scan_loop(radio):
    """
    Der Multi-Watch Loop: Wechselt die Kanäle aus der Config im Sekundentakt.
    Stoppt bei Signal (Busy) und pausiert dort.
    """
    print("Multi-Watch (MW) gestartet.")
    
    while radio.mw_active:
        # Kanäle live aus der Config auslesen und säubern
        ch_string = radio.config.get("mw_label", "09, 19")
        try:
            channels = [c.strip().zfill(2) for c in ch_string.split(",") if c.strip()]
        except Exception:
            print("Fehler beim Parsen der MW-Kanäle. Abbruch.")
            radio.mw_active = False
            break
            
        if not channels:
            print("Keine Kanäle für Multi-Watch definiert.")
            radio.mw_active = False
            break

        for ch in channels:

            if not radio.mw_active:
                break
                

            while radio.is_rx and radio.mw_active:
                time.sleep(0.2) # Schnelle Prüfung, ob Signal noch da ist
                

            if not radio.mw_active:
                break

            # --- KANAL UMSCHALTEN ---
            print(f"MW schaltet auf Kanal: {ch}")
            
            # Kanal im Radio-Objekt setzen
            radio.current_ch = int(ch)
            
            ziffer1 = ch[0]  # Erste Ziffer (z.B. bei "28" -> "2")
            ziffer2 = ch[1]  # Zweite Ziffer (z.B. bei "28" -> "8")
            
            key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
            
            # Erste Ziffer aus dem Keypad emulieren und senden
            if ziffer1 in key_codes:
                radio.send_cmd(f"41000100{key_codes[ziffer1]}000006", f"41000000{key_codes[ziffer1]}000006")
            time.sleep(0.120) # Etwas mehr Zeit lassen, damit die serielle Schnittstelle mitkommt
            
            # Zweite Ziffer aus dem Keypad emulieren und senden
            if ziffer2 in key_codes:
                radio.send_cmd(f"41000100{key_codes[ziffer2]}000006", f"41000000{key_codes[ziffer2]}000006")
            
            # 1 Sekunde auf diesem Kanal lauschen (Taktzeit)
            for _ in range(10):
                if not radio.mw_active or radio.is_rx:
                    break
                time.sleep(0.1)

    print("Multi-Watch (MW) beendet.")



# --- INSTANZ & STARTUP ---
radio = RadioInterface()


# --- FLASK ROUTES ---
@app.route('/')
def index(): return render_template('index.html', config=radio.config)




@app.route('/api/audio')
def get_audio():
    try:
        # Falls Mute aktiv ist, sofort Stille (32 Nullen) zurückgeben
        if getattr(radio, 'audio_mute', False):
            return jsonify([0] * 32)

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
    except Exception as e:
        # Im Fehlerfall leeres Spektrum senden
        return jsonify([0] * 32)

@app.route('/api/rig/ptt/<int:state>')
def rig_ptt_control(state):
    """
    HTTP-Schnittstelle für externe Digimodes (JS8Call, FLdigi etc.)
    state = 1: Senden (TX), state = 0: Empfangen (RX)
    """
    try:
        if state == 1 and not radio.is_tx:
            print("JS8Call (HTTP): Schalte TX ein")
            radio.is_tx = True
            radio.ptt_start_time = time.time()
            with radio.lock:
                radio.ser.write(bytes.fromhex("4101000000000006"))
        elif state == 0 and radio.is_tx:
            print("JS8Call (HTTP): Zurück zu RX")
            radio.is_tx = False
            with radio.lock:
                radio.ser.write(bytes.fromhex("4100000000000006"))
        return f"PTT_STATE: {radio.is_tx}\n"
    except Exception as e:
        return f"ERROR: {str(e)}\n", 500

@app.route('/api/cmd/<cmd>')
def api_cmd(cmd):
    global LAST_BROWSER_HEARTBEAT
    
    # JEDER API-Aufruf gilt als Lebenszeichen des Browsers
    LAST_BROWSER_HEARTBEAT = time.time()

    # Originale Scan- und Multiwatch-Stopper (unveraendert)
    if cmd not in ['STATUS', 'MW_TOGGLE', 'SSCAN'] and not cmd.startswith('SETSPEED'):
        radio.stop_sw_scan()
        if hasattr(radio, 'mw_active') and radio.mw_active:
            radio.mw_active = False 
            
    if cmd == 'SSCAN' and hasattr(radio, 'mw_active') and radio.mw_active:
        radio.mw_active = False

    key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
    p_codes = {'P1':'1A', 'P2':'1B', 'P3':'1C', 'P4':'1D'}
    superkey_codes = {
        'FUNC_KEY':'0x31',  
        'ACTION':'0x1E',
        'LOCKDEV':'0x1E:2',
        'CLARUP':'0x26',
        'CLARHZ':'0x1E', 
        'CLARDN':'0x27', 
        'VOX_TOGGLE':'28', 
        'VOX_SETTING':'0x28:2',
        'EMG_TOGGLE':'0x25',
        'DEVBUTTONUP':'0x10', 
        'DEVBUTTONDOWN':'0x11', 
        'DEVROTATEUP':'0x12', 
        'DEVROTATEDOWN':'0x13', 
        'DEVXUP':'0x26', 
        'DEVXDOWN':'0x27', 
        'SQUELCHUP':'0x24, 0x26, 0x24',  
        'SQUELCHMAXUP':'0x24, 0x26:17, 0x24',
        'SQUELCHDOWN':'0x24, 0x27, 0x24',  
        'SQUELCHMAXDOWN':'0x24, 0x27:17, 0x24', 
        'MODE':'0x0D',    
        'MODELONG':'0x0D:2',
        'MODEALT':'0x23',       
        'MUTECOMBBTN':'0x31, 0x1E',
        'MUTESINGLEBTN':'0x34',
        'DEVDW':'0x31, 0x27', 
        'DEVSCAN':'0x31, 0x26',        
        'ASQ_ON_OFF':'24:2' 
    }

    # =========================================================================
    # BACKUP-LOCK-STRUKTUR: Exklusiver sequenzieller Hardware-Schutz
    # =========================================================================
    with radio.lock:
        
        if cmd in ['VOLUP', 'VOLDOWN']:
            import os
            control_name = "Master" 
            step = "5%+" if cmd == 'VOLUP' else "5%-"
            os.system(f"amixer set '{control_name}' {step}")
            
            current_vol = radio.config.get("vol", 85)
            if cmd == 'VOLUP':
                radio.config["vol"] = min(100, current_vol + 5)
            else:
                radio.config["vol"] = max(0, current_vol - 5)
            radio.save_config() 
            
        elif cmd == 'U':
            radio.current_ch = (radio.current_ch % 40) + 1
            radio.ser.write(bytes.fromhex("4100010010000006"))
            time.sleep(0.08)
            radio.ser.write(bytes.fromhex("4100000010000006"))
            
        elif cmd == 'D':
            radio.current_ch = 40 if radio.current_ch == 1 else radio.current_ch - 1
            radio.ser.write(bytes.fromhex("4100010011000006"))
            time.sleep(0.08)
            radio.ser.write(bytes.fromhex("4100000011000006"))
            
        elif cmd == 'M':
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
            radio.ser.write(bytes.fromhex("410001000D000006"))
            time.sleep(0.08)
            radio.ser.write(bytes.fromhex("410000000D000006"))

        elif cmd == 'P':
            radio.is_tx = not radio.is_tx
            radio.force_rx = False 
            code = "4101000000000006" if radio.is_tx else "4100000000000006"
            radio.ser.write(bytes.fromhex(code))
            radio.ptt_start_time = time.time()
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
            radio.ser.write(bytes.fromhex("4100010001000006"))
            time.sleep(0.08); radio.ser.write(bytes.fromhex("4100000001000006"))
            time.sleep(0.4)
            radio.ser.write(bytes.fromhex("4100010002000006"))
            time.sleep(0.08); radio.ser.write(bytes.fromhex("4100000002000006"))
            time.sleep(0.4)
            radio.ser.write(bytes.fromhex("410001001A000006"))
            time.sleep(2.2)
            radio.ser.write(bytes.fromhex("410000001A000006"))
            radio.current_ch = 1; radio.mode_idx = 2; radio.save_config()
            
        elif cmd.startswith('K'):
            digit = cmd[1:]
            if digit in key_codes:
                radio.ser.write(bytes.fromhex(f"41000100{key_codes[digit]}000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex(f"41000000{key_codes[digit]}000006"))
                radio.key_buffer += digit
                if len(radio.key_buffer) == 2:
                    val = int(radio.key_buffer)
                    if 1 <= val <= 40: radio.current_ch = val
                    radio.key_buffer = ""

        elif cmd in p_codes:
            label_key = f"{cmd.lower()}_label"
            current_label = radio.config.get(label_key, "").upper()
            if "VOX" in current_label:
                if radio.config.get("vox_enabled", False):
                    import os
                    old_vol = radio.config.get("vol", 85)
                    os.system("amixer set Master 0%") 
                    radio.audio_mute = True
                    def delayed_vox_off():
                        radio.send_cmd(f"41000100{p_codes[cmd]}000006", f"41000000{p_codes[cmd]}000006")
                        radio.config["vox_enabled"] = False
                        radio.force_rx = True 
                        radio.save_config()
                        time.sleep(2.5)
                        os.system(f"amixer set Master {old_vol}%")
                        radio.audio_mute = False
                    threading.Thread(target=delayed_vox_off, daemon=True).start()
                else:
                    radio.ser.write(bytes.fromhex(f"41000100{p_codes[cmd]}000006"))
                    time.sleep(0.08)
                    radio.ser.write(bytes.fromhex(f"41000000{p_codes[cmd]}000006"))
                    radio.config["vox_enabled"] = True
                    radio.save_config()
            else:
                radio.ser.write(bytes.fromhex(f"41000100{p_codes[cmd]}000006"))
                time.sleep(0.08)
                radio.ser.write(bytes.fromhex(f"41000000{p_codes[cmd]}000006"))

        elif cmd in superkey_codes:
            label_key = f"{cmd.lower()}_label"
            current_label = radio.config.get(label_key, "").upper()
            macro_string = superkey_codes[cmd]
            commands = [c.strip() for c in macro_string.split(",")]
            
            for single_cmd in commands:
                if not single_cmd: continue
                if ":" in single_cmd:
                    hex_part, duration_part = single_cmd.split(":")
                    duration = float(duration_part)
                else:
                    hex_part = single_cmd
                    duration = 0.150
                    
                hex_clean = hex_part.replace("0x", "").zfill(2)
                
                if "VOX_TOGGLE" in current_label or cmd == "VOX_TOGGLE":
                    if radio.config.get("vox_enabled", False):
                        import os
                        old_vol = radio.config.get("vol", 85)
                        
                        # 1. Sound auf 0 schalten
                        os.system("amixer set Master 0%") 
                        radio.audio_mute = True
                        
                        # 2. Config oeffnen, False beschreiben
                        radio.config["vox_enabled"] = False
                        radio.save_config()
                        print("VOX-FAILSAFE: Sound auf 0%, Config auf False gesetzt.")
                        
                        # Der Hintergrund-Thread wartet die 2.5 Sekunden Stille ab
                        def delayed_vox_superkey_off_backup(dur, vol_back):
                            time.sleep(2.5) # 3. Das Timeout fuer absolute Stille
                            
                            print("VOX-FAILSAFE: 2.5s vorbei, sende jetzt den physischen HEX-Befehl...")
                            with radio.lock:
                                # STARR CODIERT: Wir nutzen das feste "28" fuer die VOX-Taste!
                                # Key-Down Impuls (Taste druecken)
                                radio.ser.write(bytes.fromhex("4100010028000006"))
                                time.sleep(dur)
                                # Key-Up Impuls (Taste loslassen)
                                radio.ser.write(bytes.fromhex("4100000028000006"))
                                radio.force_rx = True
                            
                            # 5. Sound zurueck zum vorherigen Status bringen
                            os.system(f"amixer set Master {vol_back}%")
                            radio.audio_mute = False
                            print("VOX-FAILSAFE: Soundkarte wieder geoeffnet. Vorgang abgeschlossen.")
                            
                        # WICHTIG: Wir uebergeben nur noch duration und old_vol an den Thread!
                        threading.Thread(target=delayed_vox_superkey_off_backup, args=(duration, old_vol), daemon=True).start()
                    else:
                        radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                        time.sleep(duration)
                        radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                        radio.config["vox_enabled"] = True
                        radio.save_config()

                        
                elif "ASQ_ON_OFF" in current_label or cmd == "ASQ_ON_OFF":
                    current_mode = MODES[radio.mode_idx].upper()
                    if current_mode not in ["AM", "FM"]: continue  
                    if radio.config.get("asq_enabled", False):
                        def delayed_asq_off(h_clean, dur):
                            radio.send_cmd(f"41000100{h_clean}000006", "00")
                            time.sleep(dur)
                            radio.send_cmd(f"41000000{h_clean}000006", "00")
                            time.sleep(0.5) 
                            radio.config["asq_enabled"] = False
                            radio.save_config()
                        threading.Thread(target=delayed_asq_off, args=(hex_clean, duration), daemon=True).start()
                    else:
                        radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                        time.sleep(duration)
                        radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                        radio.config["asq_enabled"] = True
                        radio.save_config()

                elif "MUTECOMBBTN" in current_label or cmd == "MUTECOMBBTN":
                    current_mode = MODES[radio.mode_idx].upper()
                    if current_mode not in ["AM", "FM", "USB", "LSB", "CW"]: continue
                    radio.config["mute_enabled"] = not radio.config.get("mute_enabled", False)
                    radio.save_config()
                    for m_cmd in commands:
                        if not m_cmd: continue
                        h_part = m_cmd.split(":") if ":" in m_cmd else m_cmd
                        dur = float(m_cmd.split(":")) if ":" in m_cmd else 0.150
                        h_str = h_part if isinstance(h_part, list) else h_part
                        h_cl = h_str.replace("0x", "").zfill(2)
                        radio.ser.write(bytes.fromhex(f"41000100{h_cl}000006"))
                        time.sleep(dur)
                        radio.ser.write(bytes.fromhex(f"41000000{h_cl}000006"))
                        time.sleep(0.050)
                    break 

                elif "LOCKDEV" in current_label or cmd == "LOCKDEV":
                    is_locked = radio.config.get("lock_enabled", False)
                    radio.config["lock_enabled"] = not is_locked
                    radio.save_config()
                    radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                    time.sleep(duration)
                    radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                else:
                    radio.ser.write(bytes.fromhex(f"41000100{hex_clean}000006"))
                    time.sleep(duration)
                    radio.ser.write(bytes.fromhex("41000000" + hex_clean + "000006"))
                time.sleep(0.050)

        elif cmd.startswith('SET_'):
            parts = cmd.split('_')
            val = request.args.get('val')
            if "SKIP" in cmd: 
                key_name = "skip_pa" if "PA" in cmd else "skip_cw"
                radio.config[key_name] = (val.lower() == 'true')
            elif "CLAR" in cmd:
                if "OFFSET" in cmd: radio.config["clar_offset"] = int(val)
                else: radio.config["clar_step"] = val
            else: 
                key_name = f"{parts[1].lower()}_label"
                radio.config[key_name] = val
            radio.save_config() 
            
        elif cmd.startswith('T'): 
            radio.config["ptt_timeout"] = int(cmd[1:])
            radio.save_config()
            
        elif cmd.startswith('SETGAIN_'):
            parts = cmd.split('_')
            if len(parts) == 3:
                key = f"fft_{parts[1].lower()}_gain"
                radio.config[key] = int(parts[2])
                radio.save_config() 

        elif cmd == 'MW_TOGGLE':
            radio.mw_active = not getattr(radio, 'mw_active', False)
            if radio.mw_active:
                radio.stop_sw_scan() 
                threading.Thread(target=mw_scan_loop, args=(radio,), daemon=True).start()

        if radio.is_tx and (time.time() - radio.ptt_start_time >= radio.config["ptt_timeout"]):
            radio.is_tx = False
            radio.save_config() 
            radio.ser.write(bytes.fromhex("4100000000000006"))

    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    return jsonify({
        "CH": str(radio.current_ch).zfill(2), 
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
        "CLAR_OFFSET": radio.config.get("clar_offset", 0),
        "LOCK_ENABLED": radio.config.get("lock_enabled", False),
        "MW_SCAN": getattr(radio, 'mw_active', False)
    })




@app.route('/api/config/override', methods=['POST'])
def api_config_override():
    """
    Invertiert die ausgewaehlten config.json Zustaende, falls das 
    Albrecht AE 5900 asynchron zur Software-Anzeige laeuft.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "Keine Daten empfangen"}), 400
            
        mapping = {
            "toggle_vox": "vox_enabled",
            "toggle_mute": "mute_enabled",
            "toggle_asq": "asq_enabled",
            "toggle_lock": "lock_enabled"
        }
        
        with radio.lock:
            for json_key, config_key in mapping.items():
                if data.get(json_key) is True:
                    current_state = radio.config.get(config_key, False)
                    radio.config[config_key] = not current_state
                    print(f"INVERTATION: '{config_key}' wurde manuell von {current_state} auf {not current_state} gedreht.")
                    
            radio.save_config()
            
            rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
            
            return jsonify({
                "CH": str(radio.current_ch).zfill(2), 
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
                "CLAR_OFFSET": radio.config.get("clar_offset", 0),
                "LOCK_ENABLED": radio.config.get("lock_enabled", False),
                "MW_SCAN": getattr(radio, 'mw_active', False)
            })
        
    except Exception as e:
        print(f"Fehler beim Config-Invert-Override: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def ptt_heartbeat_watchdog(radio):
    """
    Prueft im Hintergrund, ob der Browser noch lebt.
    Bleibt das Lebenszeichen (STATUS-Poll) bei TX fuer 30 Sekunden aus,
    wird das Senden sofort abgebrochen.
    """
    global LAST_BROWSER_HEARTBEAT
    print("PTT Heartbeat-Waechter (30 Sek.) aktiv.")
    
    while True:
        try:
            if radio.is_tx:
                silent_duration = time.time() - LAST_BROWSER_HEARTBEAT
                
                if silent_duration >= 30.0:
                    print(f"PTT VERBINDUNGSABBRUCH: Browser sendet seit {int(silent_duration)}s keine Daten mehr! Trenne TX.")
                    
                    with radio.lock:
                        radio.is_tx = False
                        radio.save_config()
                        radio.ser.write(bytes.fromhex("4100000000000006"))
            
            time.sleep(1.0)
        except Exception as e:
            print(f"Fehler im Heartbeat-Waechter: {e}")
            time.sleep(2.0)

threading.Thread(target=ptt_heartbeat_watchdog, args=(radio,), daemon=True).start()


# ====================== WEBSOCKET AUDIO BROADCAST ======================
def audio_broadcast_task():
    while True:
        try:
            with app.app_context():
                audio_response = get_audio()
                audio_data = audio_response.get_json()
                socketio.emit('audio', {'type': 'audio', 'data': audio_data})
            socketio.sleep(0.085)
        except Exception as e:
            socketio.sleep(0.5)

socketio.start_background_task(audio_broadcast_task)


# ====================== SOCKETIO EVENTS ======================
@socketio.on('connect')
def handle_connect():
    print("WebSocket Client verbunden")
    try:
        emit('status', get_current_status_dict())
    except:
        pass


def get_current_status_dict():
    """Status fuer WebSocket"""
    rem = int(radio.config["ptt_timeout"] - (time.time() - radio.ptt_start_time)) if radio.is_tx else radio.config["ptt_timeout"]
    return {
        "CH": str(radio.current_ch).zfill(2),
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
        "CLAR_OFFSET": radio.config.get("clar_offset", 0)
    }


# ====================== START ======================
threading.Thread(target=auto_patch_streams, daemon=True).start()
if __name__ == '__main__':
    print("AE5900 Remote V2 mit WebSocket gestartet")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

