import eventlet
eventlet.monkey_patch()


import warnings
warnings.filterwarnings("ignore", message=".*RLock.*were not greened.*")

import time
import struct
from flask import Flask, render_template_string
from flask_socketio import SocketIO, emit, join_room
import pymumble_py3 as pymumble


from flask.ctx import RequestContext
if not hasattr(RequestContext, "session") or not hasattr(RequestContext.session, "fset") or RequestContext.session.fset is None:
    RequestContext.session = property(
        lambda self: getattr(self, "_session", None),
        lambda self, value: setattr(self, "_session", value)
    )

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# --- CONFIG FOR MUMBLE ---
MUMBLE_HOST = "127.0.0.1"
MUMBLE_PORT = 64738
BOT_NAME = "WebUI-Audio-Bridge"

mumble = None

def audio_receiver_loop():
    """ Holt das Audio aus Mumble, daempft den Pegel und streamt es in den Browser """
    global mumble
    
    # --- LAUTSTAERKE-REDUZIERUNG ---
    # 1.0 = Original, 0.5 = stark reduziert. etc.
    GAIN_FACTOR = 0.8 
    
    while True:
        if mumble and mumble.is_alive():
            for user in list(mumble.users.values()):
                if user['name'] == BOT_NAME:
                    continue
                
                while user.sound.is_sound():
                    sound_packet = user.sound.get_sound()
                    if sound_packet and sound_packet.pcm:
                        # Extrahiere die 16-Bit Samples
                        fmt = f"{len(sound_packet.pcm) // 2}h"
                        samples = struct.unpack(fmt, sound_packet.pcm)
                        
                        # Daempfen und mathematisch begrenzen (Clippingschutz)
                        mod_samples = []
                        for s in samples:
                            val = int(s * GAIN_FACTOR)
                            val = max(-32768, min(32767, val))
                            mod_samples.append(val)
                            
                        # Zurueck in Bytes packen
                        reduced_pcm = struct.pack(fmt, *mod_samples)
                        socketio.emit('audio_out', reduced_pcm, room='audio_room')
        time.sleep(0.02)

# Starte den Mumble-Hintergrund-Thread
eventlet.spawn(audio_receiver_loop)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AE5900 Remote - Audio Bridge</title>
        <script src="https://cdn.socket.io/4.7.5/socket.io.min.js"></script>
        <style>
            body { background: #111; color: #fff; font-family: sans-serif; text-align: center; padding-top: 50px; }
            .btn { background: #00ff00; color: black; border: none; padding: 15px 30px; font-size: 18px; cursor: pointer; border-radius: 5px; font-weight: bold; }
            .btn.off { background: #ff3333; color: white; }
            #status { margin-top: 20px; color: #888; }
        </style>
    </head>
    <body>
        <h1>Albrecht AE 5900 - Mumble Audio Tab</h1>
        <hr style="width: 300px; border-color: #333;">
        <br>
        <button id="audioBtn" class="btn off" onclick="toggleAudio()">AUDIO RECV: OFF</button>
        <div id="status">Warte auf Verbindung...</div>

        <script>
            const socket = io();
            let audioContext = null;
            let isAudioOn = false;
            
            let nextStartTime = 0;
            const BUFFER_DELAY = 0.08; 

            socket.on('connect', () => {
                document.getElementById('status').innerText = "Verbunden mit Audio-Gateway";
                socket.emit('join_audio');
            });

            socket.on('audio_out', (pcmData) => {
                if (!isAudioOn || !audioContext) return;
                
                // Konvertierung des Binaer-Pakets
                const int16Array = new Int16Array(
                    pcmData instanceof ArrayBuffer ? pcmData : pcmData.buffer || pcmData
                );
                
                if (int16Array.length === 0) return;
                
                const float32Array = new Float32Array(int16Array.length);
                for (let i = 0; i < int16Array.length; i++) {
                    float32Array[i] = int16Array[i] / 32768.0;
                }

                const buffer = audioContext.createBuffer(1, float32Array.length, 48000);
                buffer.getChannelData(0).set(float32Array);
                
                const source = audioContext.createBufferSource();
                source.buffer = buffer;
                source.connect(audioContext.destination);

                const currentTime = audioContext.currentTime;
                if (nextStartTime < currentTime) {
                    nextStartTime = currentTime + BUFFER_DELAY;
                }

                source.start(nextStartTime);
                nextStartTime += buffer.duration;
            });

            function toggleAudio() {
                const btn = document.getElementById('audioBtn');
                if (!isAudioOn) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 48000 });
                    nextStartTime = 0; 
                    isAudioOn = true;
                    btn.innerText = "AUDIO RECV: ON";
                    btn.classList.remove('off');
                    
                    navigator.mediaDevices.getUserMedia({
                        audio: {
                            echoCancellation: false,
                            noiseSuppression: false,
                            autoGainControl: false,
                            channelCount: 1,
                            sampleRate: 48000
                        }
                    }).then(stream => {
                        document.getElementById('status').innerText = "Audio aktiv (Sende & Empfange)";
                        
                        const sourceMic = audioContext.createMediaStreamSource(stream);
                        const processor = audioContext.createScriptProcessor(2048, 1, 1);
                        
                        sourceMic.connect(processor);
                        processor.connect(audioContext.destination);
                        
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
                        
                        window.micStream = stream;
                        window.micProcessor = processor;

                    }).catch(err => {
                        document.getElementById('status').innerText = "Mikrofon-Fehler: " + err;
                    });

                } else {
                    isAudioOn = false;
                    btn.innerText = "AUDIO RECV: OFF";
                    btn.classList.add('off');
                    document.getElementById('status').innerText = "Audio gestoppt.";
                    
                    if (window.micStream) {
                        window.micStream.getTracks().forEach(track => track.stop());
                    }
                    if (window.micProcessor) {
                        window.micProcessor.disconnect();
                    }
                }
            }
        </script>
    </body>
    </html>
    """)

@socketio.on('join_audio')
def on_join_audio():
    join_room('audio_room')
    print("[WEBSOCKET] Browser-Tab ist dem Audio-Raum beigetreten.")

@socketio.on('audio_in')
def handle_audio_in(pcm_data):
    """ Empfaengt PCM-Audio vom Browser und reicht es an Mumble weiter """
    global mumble
    if mumble and mumble.is_alive():
        try:
            # PYMUMBLE-SYNTAX FIX: Der Bot sendet ueber 'sound_output'
            mumble.sound_output.add_sound(bytes(pcm_data))
        except Exception as e:
            print(f"[MIC ERROR] Fehler beim Senden an Mumble: {e}")

@socketio.on('connect')
def handle_connect():
    print("Browser-Tab hat sich mit dem Audio-Server verbunden.")
    global mumble
    if mumble is None or not mumble.is_alive():
        try:
            mumble = pymumble.Mumble(MUMBLE_HOST, BOT_NAME, port=MUMBLE_PORT)
            mumble.set_receive_sound(1) 
            mumble.start()
            mumble.is_ready()
            
            if len(mumble.channels) > 1:
                target_channel = list(mumble.channels.values())[1]
                target_channel.move_in()
                print(f"[MUMBLE] Bot in Kanal '{target_channel['name']}' verschoben.")
            else:
                print("[MUMBLE] Nur Root-Kanal vorhanden. Bleibe dort.")
                
            print("[MUMBLE] Bot erfolgreich einsatzbereit mit PCM-Decoder.")
        except Exception as e:
            print(f"[MUMBLE] Verbindung fehlgeschlagen: {e}")

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
        print("Mumble-Audio-Gateway LAEUFT SICHER UEBER HTTPS auf Port 5001...")
    else:
        print("[WARNUNG] Keine SSL-Zertifikate gefunden! Audio laeuft ueber unsicheres HTTP (Port 5001).")

    socketio.run(app, host='0.0.0.0', port=5001, debug=False, **ssl_args)
