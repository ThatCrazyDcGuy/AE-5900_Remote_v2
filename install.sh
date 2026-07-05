#!/bin/bash
# =========================================================================
# AE5900 REMOTE CONTROLLER - ALL-IN-ONE SYSTEM INSTALLER
# Unterstützt: Raspberry Pi OS (Trixie), Debian, Ubuntu
# =========================================================================

GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}   AE5900 System-Installer & Audio-Bridge-Setup     ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. System aktualisieren & Basis-Tools installieren
echo -e "\n${GREEN}[1/7] Aktualisiere System-Paketquellen...${NC}"
sudo apt update && sudo apt full-upgrade -y

echo -e "\n${GREEN}[2/7] Install system dependencies and audio components...${NC}"
sudo apt install git curl openssh-server python3-flask-socketio python3-socketio \
python3-eventlet python3-pyaudio python3-numpy python3-serial python3-flask \
python3-build portaudio19-dev libopus0 pipewire pipewire-audio pipewire-alsa \
pipewire-pulse pipewire-audio-client-libraries pulseaudio-utils pavucontrol \
wireplumber libpipewire-0.3-modules ladspa-sdk swh-plugins dbus-user-session \
mc htop python3-pip libhamlib-utils mumble mumble-server jq -y

# PyMumble via PIP (mit PEP 668 Override für Trixie/Ubuntu)
echo -e "\n${GREEN}[3/7] Install Python packages for the audio bridge...${NC}"
pip install pymumble --break-system-packages

# Altes Session-Modul entfernen
sudo apt remove pipewire-media-session -y

# Benutzer zu Gruppen hinzufügen
sudo usermod -a -G audio $USER
sudo usermod -a -G dialout $USER

# Verzeichnisse erstellen
mkdir -p ~/.config/pipewire/pipewire.conf.d/
mkdir -p ~/.config/pipewire/pipewire-pulse.conf.d/
mkdir -p ~/.config/Mumble/Mumble/
mkdir -p ~/.config/autostart/
mkdir -p ~/AE5900_Remote_V2/ARC/

# 2. PipeWire & Mumble Konfigurationen schreiben
echo -e "\n${GREEN}[4/7] Configure PipeWire and Mumble filters...${NC}"
echo 'context.properties = {
    default.clock.rate = 48000
    default.clock.allowed-rates = [ 44100 48000 88200 96000 ]
}' > ~/.config/pipewire/pipewire.conf.d/custom.conf

echo 'pulse.rules = [
    {
        matches = [
            { application.process.binary = "mumble" }
            { application.process.binary = "mumble-worker" }
        ]
        actions = { quirks = [ block-source-volume ] }
    }
]' > ~/.config/pipewire/pipewire-pulse.conf.d/99-disable-autogain.conf

echo 'pulse.rules = [
    {
        matches = [ { application.process.binary = "mumble" } ];
        actions = { quirks = [ block-source-volume ] }
    }
]' > ~/.config/pipewire/pipewire-pulse.conf.d/block-autoscale.conf

# Pavucontrol Voreinstellungen
echo '[window]
width=800
height=400
sinkInputType=1
sourceOutputType=1
sinkType=0
sourceType=1
showVolumeMeters=1
' > ~/.config/pavucontrol.ini

# 3. Mumble Settings JSON schreiben
echo "{
    \"audio\": {
        \"cue_volume\": 0.0009765625,
        \"echo_cancel_mode\": \"Disabled\",
        \"external_applications_volume\": 1.0,
        \"input_system\": \"PulseAudio\",
        \"loudness\": 20000,
        \"noise_cancel_mode\": \"Off\",
        \"notification_volume\": 0.0009765625,
        \"output_delay\": 1,
        \"output_system\": \"PulseAudio\",
        \"transmit_mode\": \"Continuous\",
        \"vad_max\": 0.9800103902816772,
        \"vad_min\": 0.8000122308731079
    },
    \"last_connection\": {
        \"server_name\": \"ae5900ctrl\",
        \"username\": \"ae5900\"
    },
    \"misc\": {
        \"audio_wizard_has_been_shown\": true,
        \"database_location\": \"$HOME/.local/share/Mumble/Mumble/mumble.sqlite\",
        \"viewed_server_ping_consent_message\": true
    },
    \"mumble_has_quit_normally\": true,
    \"network\": {
        \"auto_connect_to_last_server\": true,
        \"frames_per_packet\": 1
    },
    \"settings_version\": 1,
    \"tts\": { \"tts_volume\": 0 }

}" > ~/.config/Mumble/Mumble/mumble_settings.json

mkdir -p ~/.local/share/Mumble/Mumble/
touch ~/.local/share/Mumble/Mumble/mumble.sqlite 

# 4. Autostart & Starter-Skript einrichten (Dynamische Terminal-Erkennung)
echo -e "\n${GREEN}[5/7]Determine the system terminal and generate autostart macros...${NC}"

# Erkennung des installierten Standard-Terminals
DETECTED_TERM="x-terminal-emulator -e" # Standard-Fallback für alle X11-Systeme

if command -v lxterminal &> /dev/null; then
    DETECTED_TERM="lxterminal -e"
    echo -e "[i] lxterminal detected and configured for autostart."
elif command -v gnome-terminal &> /dev/null; then
    DETECTED_TERM="gnome-terminal --"
    echo -e "[i] gnome-terminal detected and configured for autostart."
elif command -v konsole &> /dev/null; then
    DETECTED_TERM="konsole -e"
    echo -e "[i] konsole (KDE) detected and configured for autostart."
else
    echo -e "[!] No standard terminal found. Using generic x-terminal-emulator."
fi


cat << EOF | sudo tee /usr/local/bin/ae5900starter > /dev/null
#!/bin/bash
killall pavucontrol 
killall mumble 
pkill -f ae_5900_v2.py
pkill -f mumble_webrtc_audiobridge.py

pavucontrol &
sleep 2
mumble "mumble://ae5900ADM@127.0.0.1:64738" &
sleep 2

$DETECTED_TERM python3 $HOME/AE5900_Remote_V2/ae_5900_v2.py &
sleep 3
$DETECTED_TERM python3 $HOME/AE5900_Remote_V2/mumble_webrtc_audiobridge.py &
EOF

sudo chmod +x /usr/local/bin/ae5900starter

# Die Desktop-Verknüpfung anpassen (Icon auf generisches Terminal setzen)
echo '[Desktop Entry]
Name=ae5900start
Exec=ae5900starter
Icon=utilities-terminal
Type=Application
' > ~/.config/autostart/ae5900start.desktop

# On-Board Audio deaktivieren für sauberes USB-Soundkarten-Routing (Nur Pi/Raspberry Pi OS)
if [ -f /boot/firmware/config.txt ]; then
    sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' /boot/firmware/config.txt
    if ! grep -q "dtparam=audio=off" /boot/firmware/config.txt; then
        echo 'dtparam=audio=off' | sudo tee -a /boot/firmware/config.txt
        echo 'dtoverlay=vc4-kms-v3d,noaudio' | sudo tee -a /boot/firmware/config.txt
    fi
fi

# 5. Tailscale installieren
echo -e "\n${GREEN}[6/7] Installing Tailscale...${NC}"
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up

# 6. DER AUTOMATISCHE TAILSCALE ZERTIFIKAT-MATCH
echo -e "\n${GREEN}[7/7] Generate SSL/TLS certificates for the WebAudio gateway...${NC}"
echo "Wait a moment for the Tailscale Demon..."
sleep 2

# Holt sich die Tailscale-Domain vollautomatisch, ohne jq zu benötigen!
TS_DOMAIN=$(tailscale ip -14 -dns)

if [ -z "$TS_DOMAIN" ] || [[ "$TS_DOMAIN" == *"error"* ]]; then
    # Alternativer Fallback-Versuch über den Hostnamen, falls DNS-Flag zickt
    TS_DOMAIN=$(tailscale status --self --json | grep -o '"DNSName": "[^"]*' | grep -o '[^"]*$')
fi

# Bereinigen (abschließenden Punkt entfernen falls vorhanden)
TS_DOMAIN=$(echo "$TS_DOMAIN" | sed 's/\.$//')

if [ ! -z "$TS_DOMAIN" ]; then
    echo -e "${GREEN}Success! Your tailscale domain is: ${BLUE}$TS_DOMAIN${NC}"
    cd ~/AE5900_Remote_V2/
    sudo tailscale cert "$TS_DOMAIN"
    sleep 2
    sudo chown $USER:$USER *.crt *.key
    chmod 644 *.crt
    chmod 600 *.key
    echo -e "${GREEN}SSL certificates successfully issued for $TS_DOMAIN !${NC}"
else
    echo -e "${RED}[WARNING] Could not automatically determine tailscale domain.${NC}"
    echo "Please execute the following command manually after logging into Tailscale.:"
    echo "sudo tailscale cert YOUR_TS_DOMAIN.ts.net"
fi

# 7. Mumble-Erststart zur Initialisierung mit interaktiver Sperre
echo -e "\n${BLUE}=========================================================================${NC}"
echo -e "${RED}❗ IMPORTANT INTERIM STEP FOR THE INITIAL START FOR THE OMs ❗${NC}"
echo -e "${BLUE}=========================================================================${NC}"
echo -e "Mumble is about to start for the initial setup."
echo -e ""
echo -e "1. After clicking, Mumble will ask for the SQL database and certificate."
echo -e "2. Please simply ${GREEN}confirm/accept ${NC}these requests.${NC}."
echo -e "3. Once Mumble is running, please close Mumble immediately.${NC},"
echo -e "   so that this installer can complete cleanly.."
echo -e "${BLUE}=========================================================================${NC}"
echo -e "${BLUE}Ready? Press [ENTER] to start Mumble and complete the setup...${NC}"
read -r # Wartet hier unendlich lange, bis der User ENTER drückt

# Startet Mumble im Vordergrund. Das Terminal blockiert hier, bis Mumble geschlossen wird.
echo -e "\n${BLUE}[i] Mumble is now running... Please close Mumble after confirmation!${NC}"
mumble "mumble://ae5900ADM@127.0.0.1:64738"

# Erst wenn Mumble beendet wurde, springt das Skript hierher:
echo -e "${GREEN} Mumble successfully initialized and closed!${NC}"

# Umbenennen als Installations-Flag
mv ~/AE5900_Remote_V2/install.sh ~/AE5900_Remote_V2/installation_done.sh
echo -e "\n${BLUE}=========================================================================${NC}"
echo -e "${GREEN}[DONE] Entire system ready for use! It's best to restart the system.${NC}"
echo -e "${BLUE}=========================================================================${NC}"
