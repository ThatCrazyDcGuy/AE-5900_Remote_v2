import serial
import threading
import time
import json
import os

class RadioInterface:
    def __init__(self, port='/dev/ttyUSB0', config_file='config.json'):
        self.config_file = config_file
        self.port = port
        self.modes = ["PA", "CW", "FM", "AM", "USB", "LSB"]
        self.load_config()
        
        self.lock = threading.Lock()
        self.is_tx = False
        self.is_rx = False
        self.is_device_sending = False
        self.is_scanning = False
        self.sw_scan_active = False
        self.force_rx = False
        self.audio_mute = False
        self.ptt_start_time = 0
        self.key_buffer = ""
        
        self.current_ch = self.config.get("last_ch", 1)
        self.mode_idx = self.config.get("last_mode", 2)
        self.scan_dir = 1 
        self.ignore_until = 0 
        
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=0.01)
            print(f"--- AE5900 Master-Emulator Hardware-Anbindung AKTIV ---")
            threading.Thread(target=self.heartbeat_task, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"Serial Verbindungsfehler: {e}")

    def load_config(self):
        default = {
            "ptt_timeout": 300, "last_ch": 1, "last_mode": 2, "skip_pa": False,
            "skip_cw": False,  # <--- NEU!
            "p1_label": "Not set", "p2_label": "Not set", "p3_label": "Not set", "p4_label": "Not set",
            "scan_speed": 0.5, "vol": 85, "fft_rx_gain": 25000, "fft_tx_gain": 55000,
            "vox_enabled": False
        }

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f: self.config = {**default, **json.load(f)}
            except: self.config = default
        else: self.config = default

    def save_config(self):
        self.config["last_ch"] = self.current_ch
        self.config["last_mode"] = self.mode_idx
        with open(self.config_file, 'w') as f: json.dump(self.config, f, indent=4)

    def send_cmd(self, hex_press, hex_release):
        if not self.ser: return
        with self.lock:
            self.ser.write(bytes.fromhex(hex_press))
            time.sleep(0.08)
            self.ser.write(bytes.fromhex(hex_release))

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

    # --- HIER DEINE NEUEN ENTSCHLÜSSELTEN HARDWARE-GEWINNE ---
    def change_hardware_volume(self, direction):
        """Regelt die native Gerätelautstärke über 0x12 (Up) und 0x13 (Down)"""
        code = "12" if direction == "up" else "13"
        self.send_cmd(f"41000100{code}000006", f"41000000{code}000006")

    def toggle_hardware_lock(self):
        """Schaltet die Tastensperre via Long-Press 0x1E am Gerät um"""
        self.send_cmd("410001001E000006", "410000001E000006") # Simuliert langen Druck intern

    def toggle_hardware_vox(self, long_press=False):
        """Schaltet native VOX (Short 0x28) oder VOX-Menü (Long 0x28)"""
        # Wir nutzen deine Entdeckung für die echte Geräte-VOX!
        self.send_cmd("4100010028000006", "4100000028000006")

    def trigger_func_menu(self):
        """Öffnet das FUNC-Erweiterungsmenü über Long-Press 0x31"""
        self.send_cmd("4100010031000006", "4100000031000006")

    def adjust_squelch(self, direction, points=1):
        """Öffnet das SQ-Menü (0x24) und regelt das Level über die nativen Vol-Codes"""
        step_code = "12" if direction == "up" else "13"
        with self.lock:
            # 1. Squelch-Menü am Funkgerät triggern
            self.ser.write(bytes.fromhex("4100010024000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("4100000024000006"))
            time.sleep(0.06)
            # 2. Die Regel-Schritte hinterhersenden
            for _ in range(points):
                self.ser.write(bytes.fromhex(f"41000100{step_code}000006"))
                time.sleep(0.06)
                self.ser.write(bytes.fromhex(f"41000000{step_code}000006"))
                time.sleep(0.06)


    def step_clarifier(self, mode_clicks, direction_up=True):
        """Regelt den Clarifier in Stufen (1Hz, 10Hz, 100Hz) via 0x1E und 0x10/0x11"""
        step_code = "10" if direction_up else "11"
        with self.lock:
            # Klicke 0x1E so oft wie für die Stufe benötigt
            for _ in range(mode_clicks):
                self.ser.write(bytes.fromhex("410001001E000006"))
                time.sleep(0.05)
                self.ser.write(bytes.fromhex("410000001E000006"))
                time.sleep(0.05)
            # Frequenzschritt ausführen
            self.ser.write(bytes.fromhex(f"41000100{step_code}000006"))
            time.sleep(0.05)
            self.ser.write(bytes.fromhex(f"41000000{step_code}000006"))
