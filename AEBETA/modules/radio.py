import serial
import threading
import time
import json
import os
import sys
import select

class RadioInterface:
    def __init__(self, port='/dev/ttyUSB1', config_file='config.json'):
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
        
        # Clarifier-Klick-Zähler (0 = Aus, 1 = 1Hz, 2 = 10Hz, 3 = 100Hz)
        self.clarifier_step = 0 
        
        try:
            self.ser = serial.Serial(self.port, 115200, timeout=0.01)
            print(f"--- AE5900 Hardware-Anbindung AKTIV ---")
            threading.Thread(target=self.heartbeat_task, daemon=True).start()
        except Exception as e:
            self.ser = None
            print(f"Serial Verbindungsfehler: {e}")

    def load_config(self):
        default = {
            "ptt_timeout": 300, "last_ch": 1, "last_mode": 2, "skip_pa": False, "skip_cw": False,
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
        self.send_cmd("4100010001000006", "4100000001000006")
        time.sleep(0.4)
        self.send_cmd("4100010002000006", "4100000002000006")
        time.sleep(0.4)
        with self.lock:
            self.ser.write(bytes.fromhex("410001001A000006"))
            time.sleep(2.2)
            self.ser.write(bytes.fromhex("410000001A000006"))
        self.current_ch = 1; self.mode_idx = 2; self.save_config()

    # --- DEINE ENTSCHLÜSSELTEN HARDWARE-BEFEHLE ---
    def change_hardware_volume(self, direction):
        code = "12" if direction == "up" else "13"
        self.send_cmd(f"41000100{code}000006", f"41000000{code}000006")

    def toggle_hardware_lock(self):
        self.send_cmd("410001001E000006", "410000001E000006")

    def toggle_hardware_vox(self):
        self.send_cmd("4100010028000006", "4100000028000006")

    def trigger_func_menu(self):
        self.send_cmd("4100010031000006", "4100000031000006")

    def adjust_squelch(self, direction):
        """
        Sicherer Squelch-Schritt (Dreier-Kombination):
        1. Menü öffnen (0x24)
        2. Schritt ausführen (0x12 oder 0x13)
        3. Menü per ACTION-Taste schliessen (0x1E)
        """
        step_code = "12" if direction == "up" else "13"
        with self.lock:
            # Schritt 1: Squelch-Menü am Funkgerät öffnen (0x24)
            self.ser.write(bytes.fromhex("4100010024000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("4100000024000006"))
            time.sleep(0.06)
            
            # Schritt 2: Den Regel-Schritt senden (0x12 / 0x13)
            self.ser.write(bytes.fromhex(f"41000100{step_code}000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex(f"41000000{step_code}000006"))
            time.sleep(0.06)
            
            # Schritt 3: Menü per ACTION-Taste (0x1E) zwingend bestätigen/schliessen
            self.ser.write(bytes.fromhex("410001001E000006"))
            time.sleep(0.06)
            self.ser.write(bytes.fromhex("410000001E000006"))
            
        print(f"--- Squelch {direction.upper()} Dreier-Kombination ausgeführt ---")


    def trigger_clarifier_action(self):
        """Der neue ACTION Knopf schaltet die Clarifier-Stufen 1Hz -> 10Hz -> 100Hz -> Aus"""
        self.clarifier_step = (self.clarifier_step + 1) % 4
        # Physischen Klick an die Hardware senden (0x1E)
        self.send_cmd("410001001E000006", "410000001E000006")
        stages = ["AUS", "1 Hz (FEIN)", "10 Hz", "100 Hz (GROB)"]
        print(f"--- Clarifier-Modus: {stages[self.clarifier_step]} ---")

