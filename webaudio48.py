import eventlet
eventlet.monkey_patch()

import warnings
warnings.filterwarnings("ignore", message=".*RLock.*were not greened.*")

import time
import struct
import pyaudio
import queue
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit, join_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', transports=['websocket'])

tx_queue = queue.Queue(maxsize=30)
p = pyaudio.PyAudio()

def tx_callback(in_data, frame_count, time_info, status):
    try:
        if tx_queue.empty():
            return (b'\x00' * (frame_count * 2), pyaudio.paContinue)
        data = tx_queue.get_nowait()
        expected_bytes = frame_count * 2
        if len(data) < expected_bytes:
            data = data + (b'\x00' * (expected_bytes - len(data)))
        elif len(data) > expected_bytes:
            data = data[:expected_bytes]
        return (data, pyaudio.paContinue)
    except Exception:
        return (b'\x00' * (frame_count * 2), pyaudio.paContinue)

tx_stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=48000,
    output=True,
    frames_per_buffer=2048, 
    stream_callback=tx_callback
)

rx_stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=48000,
    input=True,
    frames_per_buffer=2048
)

print("[AUDIO] FULL-48k Hardware-Schnittstellen erfolgreich geöffnet.")

def audio_receiver_loop():
    while True:
        try:
            raw_data = rx_stream.read(2048, exception_on_overflow=False) 
            if raw_data:
                # REINES PASS-THROUGH: Keine Manipulation, volle 48kHz ins Netz!
                socketio.emit('audio_out', raw_data, room='audio_room')
        except Exception as e:
            print(f"[RX ERROR] {e}")
        eventlet.sleep(0.005)

eventlet.spawn(audio_receiver_loop)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AE5900 Remote - Pure 48kHz</title>
        <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
        <style>
            body { background: #111; color: #fff; font-family: sans-serif; margin: 0; padding: 0; overflow: hidden; }
            .audio-bar { background: #222; padding: 10px; text-align: center; border-bottom: 2px solid #333; display: flex; justify-content: center; align-items: center; gap: 15px; height: 40px; }
            .btn { background: #00ff00; color: black; border: none; padding: 8px 20px; font-size: 14px; cursor: pointer; border-radius: 5px; font-weight: bold; }
            .btn.off { background: #ff3333; color: white; }
            #status { color: #888; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="audio-bar">
            <button id="audioBtn" class="btn off" onclick="toggleAudio()">AUDIO RECV: OFF</button>
            <div id="status">Warte auf Verbindung...</div>
            <button class="btn" style="background:#00bcff; color:white;" onclick="openControl()">Funkgerät Steuerung öffnen ↗</button>
        </div>
        <div style="margin-top: 100px; color: #555; text-align:center;">
            <h2>48 kHz High-Fidelity Modus aktiv</h2>
        </div>
        <script>
            function openControl() { window.open("http://" + window.location.hostname + ":5000", "_blank"); }
            const socket = io({ transports: ['websocket'], upgrade: false });
            let audioContext = null; let isAudioOn = false; let nextStartTime = 0; const BUFFER_DELAY = 0.08; 

            socket.on('connect', () => { document.getElementById('status').innerText = "Verbunden (48kHz)"; socket.emit('join_audio'); });

            socket.on('audio_out', (pcmData) => {
                if (!isAudioOn || !audioContext) return;
                const int16Array = new Int16Array(pcmData instanceof ArrayBuffer ? pcmData : pcmData.buffer || pcmData);
                if (int16Array.length === 0) return;
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) { float32Array[i] = int16Array[i] / 32768.0; }
                const buffer = audioContext.createBuffer(1, float32Array.length, 48000); // <--- Abspielen auf 48000Hz!
                buffer.getChannelData(0).set(float32Array);
                const source = audioContext.createBufferSource(); source.buffer = buffer; source.connect(audioContext.destination);
                const currentTime = audioContext.currentTime;
                if (nextStartTime < currentTime) { nextStartTime = currentTime + BUFFER_DELAY; }
                source.start(nextStartTime); nextStartTime += buffer.duration;
            });

            function toggleAudio() {
                const btn = document.getElementById('audioBtn');
                if (!isAudioOn) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
                    isAudioOn = true; btn.innerText = "AUDIO RECV: ON"; btn.classList.remove('off');
                    navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false, channelCount: 1, sampleRate: 48000 } }).then(stream => {
                        const sourceMic = audioContext.createMediaStreamSource(stream);
                        const processor = audioContext.createScriptProcessor(2048, 1, 1);
                        sourceMic.connect(processor); processor.connect(audioContext.destination);
                        processor.onaudioprocess = (e) => {
                            if (!isAudioOn) return;
                            const inputData = e.inputBuffer.getChannelData(0);
                            const int16Buffer = new Int16Array(inputData.length);
                            for (let i = 0; i < inputData.length; i++) {
                                let s = Math.max(-1, Math.min(1, inputData[i]));
                                int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                            }
                            socket.emit('audio_in', int16Buffer.buffer);
                        };
                        window.micStream = stream; window.micProcessor = processor;
                    });
                } else {
                    isAudioOn = false; btn.innerText = "AUDIO RECV: OFF"; btn.classList.add('off');
                    if (window.micStream) window.micStream.getTracks().forEach(track => track.stop());
                    if (window.micProcessor) window.micProcessor.disconnect();
                }
            }
        </script>
    </body>
    </html>
    """)

@socketio.on('join_audio')
def on_join_audio():
    join_room('audio_room')

@socketio.on('audio_in')
def handle_audio_in(pcm_data):
    if isinstance(pcm_data, str):
        return
    try:

        if tx_queue.full():
            try:
                tx_queue.get_nowait()
            except queue.Empty:
                pass
        
        tx_queue.put_nowait(bytes(pcm_data))
    except Exception as e:
        print(f"[TX ERROR] Pufferfehler: {e}")

if __name__ == '__main__':
    import os
    import subprocess

    ssl_args = {}
    cert_found = False

    try:
        ts_status = subprocess.check_output(["tailscale", "status"], text=True)
        for line in ts_status.split('\n'):
            if ".ts.net" in line:
                parts = line.split()
                for part in parts:
                    if part.endswith(".ts.net"):
                        ts_domain = part
                        possible_paths = [
                            (f"{ts_domain}.crt", f"{ts_domain}.key"),
                            (f"/var/lib/tailscale/certs/{ts_domain}.crt", f"/var/lib/tailscale/certs/{ts_domain}.key")
                        ]
                        for cert_p, key_p in possible_paths:
                            if os.path.exists(cert_p) and os.path.exists(key_p):
                                ssl_args = {'certfile': cert_p, 'keyfile': key_p}
                                cert_found = True
                                break
                if cert_found:
                    break
    except Exception:
        pass

    if not cert_found:
        local_files = os.listdir('.')
        crts = [f for f in local_files if f.endswith('.crt')]
        keys = [f for f in local_files if f.endswith('.key')]
        if crts and keys:
            ssl_args = {'certfile': crts[0], 'keyfile': keys[0]}
            cert_found = True

    if cert_found:
        print("Direkt-Audio-Gateway RX 16 / TX 48 LAEUFT auf Port 5002...")
    else:
        print("[WARNUNG] Keine SSL-Zertifikate gefunden!")

    socketio.run(app, host='0.0.0.0', port=5002, debug=False, **ssl_args)
