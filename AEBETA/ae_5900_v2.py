import threading
import time
import numpy as np
from flask import Flask, render_template, jsonify, request
from modules.radio import RadioInterface
from modules.audio import setup_audio_streams, auto_patch_streams, CHUNK

app = Flask(__name__)
radio = RadioInterface()
stream_rx, stream_tx = setup_audio_streams()

# Starte Mumble-Patching im Hintergrund
threading.Thread(target=auto_patch_streams, daemon=True).start()

# --- DEIN GEWOHNTER LISTEN LOOP ALS THREAD ---
def run_listen_loop():
    raw_buffer = b""
    while radio.ser:
        if radio.ser.in_waiting > 0:
            try:
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
                            for _ in range(3):
                                radio.ser.write(bytes.fromhex("4100000000000006"))
                                time.sleep(0.01)
                        radio.force_rx = False

                    radio.is_device_sending = vox_detected
                    raw_buffer = raw_buffer[idx+16:]
            except: pass
        time.sleep(0.02)

threading.Thread(target=run_listen_loop, daemon=True).start()

# --- WEB ROUTES ---
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
        radio.stop_sw_scan()

    key_codes = {'0':'01','1':'02','2':'03','3':'04','4':'05','5':'06','6':'07','7':'08','8':'09','9':'0A'}
    p_codes = {'P1':'1A', 'P2':'1B', 'P3':'1C', 'P4':'1D'}
    
    # 1. Native Lautstärkeregelung & Squelch über deine neuen Hex-Befehle
    # 1. DEIN ESSENTIELLES MUMBLE / MIC-GAIN (Unverändert zurückgeholt!)
    if cmd in ['VOLUP', 'VOLDOWN']:
        import os
        control_name = "Master" 
        step = "5%+" if cmd == 'VOLUP' else "5%-"
        os.system(f"amixer set '{control_name}' {step}")
        
        current_vol = radio.config.get("vol", 85)
        if cmd == 'VOLUP': radio.config["vol"] = min(100, current_vol + 5)
        else: radio.config["vol"] = max(0, current_vol - 5)
        radio.save_config() 

    # 2. NEU: NATIVE GERÄTELAUTSTÄRKE (Auf eigenen Befehlen!)
    elif cmd == 'HWVOLUP':
        radio.send_cmd("4100010012000006", "4100000012000006")
    elif cmd == 'HWVOLDOWN':
        radio.send_cmd("4100010013000006", "4100000013000006")

    # 3. NEU: NATIVER SQUELCH
    elif cmd == 'SQUP':
        radio.adjust_squelch("up")
    elif cmd == 'SQDOWN':
        radio.adjust_squelch("down")

    
    # NEU: Der direkte Hardware-VOX Button aus der UI
    elif cmd == 'HWVOX': radio.toggle_hardware_vox()
    elif cmd == 'HWFUNC': radio.trigger_func_menu()
    elif cmd == 'HWLOCK': radio.toggle_hardware_lock()

    elif cmd == 'U':
        radio.current_ch = (radio.current_ch % 40) + 1
        radio.send_cmd("4100010010000006", "4100000010000006")
    elif cmd == 'D':
        radio.current_ch = 40 if radio.current_ch == 1 else radio.current_ch - 1
        radio.send_cmd("4100010011000006", "4100000011000006")
    elif cmd == 'M':
        # Einmal weiterschalten
        radio.mode_idx = (radio.mode_idx + 1) % len(radio.modes)
        
        # Schleife läuft so lange, bis wir auf einem erlaubten Modus landen
        while True:
            if radio.config.get("skip_pa") and radio.modes[radio.mode_idx] == "PA":
                radio.mode_idx = (radio.mode_idx + 1) % len(radio.modes)
                continue
            if radio.config.get("skip_cw") and radio.modes[radio.mode_idx] == "CW":
                radio.mode_idx = (radio.mode_idx + 1) % len(radio.modes)
                continue
            break # Erlaubter Modus gefunden, Schleife beenden
            
        # Den finalen Befehl an das Funkgerät senden
        radio.send_cmd("410001000D000006", "410000000D000006")
    elif cmd == 'P':
        radio.is_tx = not radio.is_tx
        radio.force_rx = False
        code = "4101000000000006" if radio.is_tx else "4100000000000006"
        with radio.lock: radio.ser.write(bytes.fromhex(code))
        radio.ptt_start_time = time.time()
    elif cmd == 'SSCAN':
        radio.sw_scan_active = not radio.sw_scan_active
        if radio.sw_scan_active: threading.Thread(target=radio.sw_scan_loop, daemon=True).start()
    elif cmd.startswith('SETSPEED_'):
        radio.config["scan_speed"] = float(cmd.split('_')[1]) / 1000.0
    elif cmd == 'S': radio.super_sync()
    elif cmd.startswith('K'):
        digit = cmd[1:]
        if digit in key_codes:
            radio.send_cmd(f"41000100{key_codes[digit]}000006", f"41000000{key_codes[digit]}000006")
            radio.key_buffer += digit
            if len(radio.key_buffer) == 2:
                try:
                    val = int(radio.key_buffer)
                    if 1 <= val <= 40: radio.current_ch = val
                except: pass
                radio.key_buffer = ""
    elif cmd in p_codes:
        radio.send_cmd(f"41000100{p_codes[cmd]}000006", f"41000000{p_codes[cmd]}000006")
    elif cmd.startswith('SET_'):
        parts = cmd.split('_'); val = request.args.get('val')
        if "SKIP_PA" in cmd: radio.config["skip_pa"] = (val.lower() == 'true')
        elif "SKIP_CW" in cmd: radio.config["skip_cw"] = (val.lower() == 'true') # <--- NEU!
        else: radio.config[f"{parts[1].lower()}_label"] = val
    # Timeout Schutz
    rem = radio.config["ptt_timeout"]
    if radio.is_tx:
        elapsed = time.time() - radio.ptt_start_time
        if elapsed >= radio.config["ptt_timeout"]:
            radio.is_tx = False
            radio.send_cmd("4100000000000006", "4100000000000006")
        rem = int(radio.config["ptt_timeout"] - elapsed)

    radio.save_config()
    return jsonify({
        "CH": str(radio.current_ch).zfill(2), "MODE": radio.modes[radio.mode_idx], 
        "PTT": "ON" if radio.is_tx else "OFF", "VOX_TX": radio.is_device_sending,
        "VOX_ENABLED": radio.config.get("vox_enabled", False), "REMAINING": max(0, rem), 
        "BUSY": radio.is_rx, "SW_SCAN": radio.sw_scan_active, "SKIP_PA": radio.config.get("skip_pa", False),
        "SKIP_CW": radio.config.get("skip_cw", False)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
