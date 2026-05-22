import pyaudio
import os
import time
import subprocess

CHUNK = 512
stream_rx = None
stream_tx = None

def setup_audio_streams():
    global stream_rx, stream_tx
    
    # Client 1: RX (Funkgerät)
    os.environ['PULSE_PROP'] = 'node.description="AE_RX" node.name="AE_RX"'
    pa_rx = pyaudio.PyAudio()
    stream_rx = pa_rx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
    
    # Client 2: TX (Mumble-Monitor)
    os.environ['PULSE_PROP'] = 'node.description="AE_TX" node.name="AE_TX"'
    pa_tx = pyaudio.PyAudio()
    stream_tx = pa_tx.open(format=pyaudio.paInt16, channels=1, rate=22050, input=True, frames_per_buffer=CHUNK)
    
    os.environ.pop('PULSE_PROP', None)
    print("--- Audio-Streams AE_RX und AE_TX bereit ---")
    return stream_rx, stream_tx

def auto_patch_streams():
    time.sleep(5)
    try:
        source = "Mumble:output_FL"
        res_in = subprocess.run(["pw-link", "-i"], capture_output=True, text=True).stdout
        python_ports = [l.strip() for l in res_in.split('\n') if "python" in l.lower() or "alsa_capture" in l.lower()]
        
        if len(python_ports) >= 2:
            target = python_ports[0]
            subprocess.run(["pw-link", source, target], check=False)
            print(f"--- Mumble-Patch erfolgreich: {source} -> {target} ---")
    except Exception as e:
        print(f"Audio Patch-Fehler: {e}")
