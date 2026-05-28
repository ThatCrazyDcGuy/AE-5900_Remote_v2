#!/bin/bash

# System aktualisieren
sudo apt update && sudo apt full-upgrade -y

# Pakete installieren
sudo apt install git curl openssh-server python3-flask-socketio python3-socketio python3-eventlet python3-pyaudio python3-numpy python3-serial python3-flask pipewire pipewire-audio pipewire-alsa pipewire-pulse pipewire pipewire-audio-client-libraries pulseaudio-utils pavucontrol wireplumber libpipewire-0.3-modules ladspa-sdk swh-plugins dbus-user-session mc htop mumble mumble-server -y

# Altes Session-Modul entfernen
sudo apt remove pipewire-media-session -y

# Benutzer zu Gruppen hinzufügen
sudo usermod -a -G audio $USER
sudo usermod -a -G dialout $USER

# Pipewire-Konfigurationsverzeichnisse erstellen
mkdir -p ~/.config/pipewire/pipewire.conf.d/
mkdir -p ~/.config/pipewire/pipewire-pulse.conf.d/
mkdir -p ~/.config/Mumble/Mumble/
mkdir -p ~/.config/autostart/

# clock-Rate und allowed-rates setzen
echo 'context.properties = {
    default.clock.rate = 48000
    default.clock.allowed-rates = [ 44100 48000 88200 96000 ]
}' > ~/.config/pipewire/pipewire.conf.d/custom.conf

# Regel: Autogain für Mumble deaktivieren
echo 'pulse.rules = [
    {
        matches = [
            { application.process.binary = "mumble" }
            { application.process.binary = "mumble-worker" }
        ]
        actions = { quirks = [ block-source-volume ] }
    }
]' > ~/.config/pipewire/pipewire-pulse.conf.d/99-disable-autogain.conf

# Zusätzliche Regel zur Blockierung von Autoscale
echo 'pulse.rules = [
    {
        matches = [ { application.process.binary = "mumble" } ];
        actions = { quirks = [ block-source-volume ] }
    }
]' > ~/.config/pipewire/pipewire-pulse.conf.d/block-autoscale.conf

# Mumble Setup // Generate config
echo '{
    "audio": {
        "cue_volume": 0.0009765625,
        "echo_cancel_mode": "Disabled",
        "external_applications_volume": 1.0,
        "input_system": "PulseAudio",
        "loudness": 20000,
        "noise_cancel_mode": "Off",
        "notification_volume": 0.0009765625,
        "output_delay": 1,
        "output_system": "PulseAudio",
        "transmit_mode": "Continuous",
        "vad_max": 0.9800103902816772,
        "vad_min": 0.8000122308731079
    },
    "last_connection": {
        "server_name": "ae5900ctrl",
        "username": "ae5900"
    },
    "misc": {
        "audio_wizard_has_been_shown": true,
        "database_location": "/home/ae5900/.local/share/Mumble/Mumble/mumble.sqlite",
        "viewed_server_ping_consent_message": true
    },
    "mumble_has_quit_normally": true,
    "network": {
        "auto_connect_to_last_server": true,
        "frames_per_packet": 1
    },
    "plugins": {
        "0333d2aac0f90a0722dda9ce9084a20d60c62adb": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libborderlands2.so",
            "positional_data_enabled": true
        },
        "09ebbec6492c8ae80a0be738d474be0d1b2daa15": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libffxiv_x64.so",
            "positional_data_enabled": true
        },
        "108a4f2b32f557de748f69f1e14654d355a10bfa": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libse.so",
            "positional_data_enabled": true
        },
        "12d034a6eacb3331e4cc441a9db0485ac55bbfbb": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libwow.so",
            "positional_data_enabled": true
        },
        "13706e814440b17f8dca09f2b537169e42ea489b": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf4.so",
            "positional_data_enabled": true
        },
        "1582fe4469a6c920546d7872a408cf5a5a5932f8": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbreach.so",
            "positional_data_enabled": true
        },
        "18f5710d62d8739040e28e0654077ace9e065c0b": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf1942.so",
            "positional_data_enabled": true
        },
        "1a018a611440873b1677db66ce23933596680fd4": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcs.so",
            "positional_data_enabled": true
        },
        "35c2605829856cdf7bfb5d515195ee6d175be3c5": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libql.so",
            "positional_data_enabled": true
        },
        "3735a75b257b6f5f2c58a709048490105010f3e2": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libgtaiv.so",
            "positional_data_enabled": true
        },
        "37eb880d8875d80e5f680f8e37ac4a9899366ef9": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libut2004.so",
            "positional_data_enabled": true
        },
        "3827c8d5859c2c7fba15578058919cf346dce3af": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcod4.so",
            "positional_data_enabled": true
        },
        "3b7fc9243a334bc008688b8cc68f912fa78a0a41": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf4_x86.so",
            "positional_data_enabled": true
        },
        "488216b5322fdc2068f0c26de0e35b29225ad21e": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libut99.so",
            "positional_data_enabled": true
        },
        "4905c7b989af0d1a71eca8a8cc259055c4355303": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libwow_x64.so",
            "positional_data_enabled": true
        },
        "4b566d58a68a9a67e7f91868fa6e32c6041a6dec": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/librl.so",
            "positional_data_enabled": true
        },
        "4d772742fcda4e552a86ef659bcee0b5cc48abf7": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libetqw.so",
            "positional_data_enabled": true
        },
        "54eae3a6d4008a43f7520a7077ced185b40b9f43": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libffxiv.so",
            "positional_data_enabled": true
        },
        "55eb88d99735d14df230310f63195a79b033cd1a": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf3.so",
            "positional_data_enabled": true
        },
        "59f9a72465d41a1acee71d5d513f4a6b9c5d5e02": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf1.so",
            "positional_data_enabled": true
        },
        "5fc0b527156cff5562c3e5f9ba5d45fca8adcb70": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf2.so",
            "positional_data_enabled": true
        },
        "6b20400c2f2f964b20156b6c49ff43d5b69f56b7": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libwolfet.so",
            "positional_data_enabled": true
        },
        "7936f8856b9487d21052d2394c734e49f67dab51": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/liblol.so",
            "positional_data_enabled": true
        },
        "9a964244b185a916491a167c5e2e9b212f5f29f9": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libgtasa.so",
            "positional_data_enabled": true
        },
        "9d8a1e067756e9f7b509a46f9421cab447186c24": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbfbc2.so",
            "positional_data_enabled": true
        },
        "9e660b56040fd9171240d2b52d26995699df0f2a": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "manual.builtin",
            "positional_data_enabled": true
        },
        "9f59b0b2e6bcfb55e9c7d33cc37a84b96dac0af4": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libamongus.so",
            "positional_data_enabled": true
        },
        "a1862862c555584bebcf297f4384062ee916b44e": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libgw.so",
            "positional_data_enabled": true
        },
        "a21c5826aa8c6ffd053187bebbc329fde31cea5b": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libsr.so",
            "positional_data_enabled": true
        },
        "a62644c9af27c268106d4d6076f9d73defef2364": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcodmw2so.so",
            "positional_data_enabled": true
        },
        "a90bf35d3a4c6dcb1377cd66561dc89ef187da9b": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libinsurgency.so",
            "positional_data_enabled": true
        },
        "b633569552047e17d533394a98bea49b8db8df88": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcod5.so",
            "positional_data_enabled": true
        },
        "bdf165b59c5d824c537fd0c4ef7f6b9422f71622": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libut3.so",
            "positional_data_enabled": true
        },
        "bee22b9b7ee166c3a49be516adea212616220af1": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libarma2.so",
            "positional_data_enabled": true
        },
        "c0e4f70c5eae8965fe50c10db3f31b4cb1a3090b": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libborderlands.so",
            "positional_data_enabled": true
        },
        "c370210abec25b5ab8302a5cd8ecec0c43c12d7f": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libdys.so",
            "positional_data_enabled": true
        },
        "cf4b5e8d5e9165bfa220a4b7c48cd16d71029f47": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/liblotro.so",
            "positional_data_enabled": true
        },
        "d1bf371aedc43509afa8647b5499e57e789639b5": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcod2.so",
            "positional_data_enabled": true
        },
        "d742cda3cee7725e3932e91e8d5d3faf367fcaa3": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbfheroes.so",
            "positional_data_enabled": true
        },
        "e36b4cf151900551e945f0de1fc9ab2d6b513bf5": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libblacklight.so",
            "positional_data_enabled": true
        },
        "eef244d90c582df4543c3cf534c9e7fded1d0a0e": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libjc2.so",
            "positional_data_enabled": true
        },
        "ef73da904fa277b10413b069cd1c27a34cc6dc94": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libgtav.so",
            "positional_data_enabled": true
        },
        "efa54329e7683aa5e631c97c6d8e93beb73e3cbb": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libaoc.so",
            "positional_data_enabled": true
        },
        "f3115d36ff96872a971cd2d773f03efec787f655": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libgmod.so",
            "positional_data_enabled": true
        },
        "f333c021065ac8ca8d516522a07db755619cf7ab": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/liblink.so",
            "positional_data_enabled": true
        },
        "f536d6329d0babec0e065433d286250c3cbab959": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libbf2142.so",
            "positional_data_enabled": true
        },
        "f6857b4caad10dc93742b0e4cbab3b4084d96ab6": {
            "enabled": false,
            "keyboard_monitoring_allowed": false,
            "path": "/usr/lib/aarch64-linux-gnu/mumble/plugins/libcodmw2.so",
            "positional_data_enabled": true
        }
    },
    "positional_audio": {
        "bloom": 0.0,
        "maximum_distance": 1.0,
        "minimum_distance": 0.0
    },
    "settings_version": 1,
    "tts": {
        "tts_volume": 0
    },
    "ui": {
        "config_geometry": "AdnQywADAAAAAAAAAAAAAAAAB38AAAP5AAAAAAAAAAAAAAVYAAADFQAAAAACAAAAB4AAAAAAAAAAAAAAB38AAAP5",
        "connect_dialog_geometry": "AdnQywADAAAAAAAAAAAAAAAAAj0AAAFtAAAAAAAAAAAAAAI9AAABbQAAAAAAAAAAB4AAAAAAAAAAAAAAAj0AAAFt",
        "connect_dialog_header_state": "AAAA/wAAAAAAAAABAAAAAAAAAAEBAAAAAAAAAAAAAAAAAAAAAAAAAiYAAAADAQEAAAAAAAABAAAAAgAAAGT/////AAAAgQAAAAAAAAADAAABWQAAAAEAAAABAAAAYgAAAAEAAAADAAAAawAAAAEAAAADAAAD6AAAAABk",
        "overlay_header_state": "AAAA/wAAAAAAAAABAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAdUAAAABAQAAAQAAAAAAAAAAAAAAAGT/////AAAAgQAAAAAAAAABAAAB1QAAAAEAAAAAAAAD6AAAAABk",
        "window_geometry": "AdnQywADAAAAAAAAAAAAAAAAAt4AAAGyAAAAAAAAAAAAAALeAAABsgAAAAAAAAAAB4AAAAAAAAAAAAAAAt4AAAGy",
        "window_state": "AAAA/wAAAAD9AAAAAgAAAAAAAAEAAAABdfwCAAAAAvsAAAAMAHEAZAB3AEwAbwBnAQAAAD4AAAFYAAAAegD////7AAAADgBxAGQAdwBDAGgAYQB0AQAAAZoAAAAZAAAAGQAAABkAAAACAAAAAAAAAAD8AQAAAAH7AAAAJABxAGQAdwBNAGkAbgBpAG0AYQBsAFYAaQBlAHcATgBvAHQAZQAAAAAA/////wAAAFcA////AAAB2wAAAXUAAAAEAAAABAAAAAgAAAAI/AAAAAEAAAACAAAAAQAAABoAcQB0AEkAYwBvAG4AVABvAG8AbABiAGEAcgEAAAAA/////wAAAAAAAAAA"
    }
}
' > ~/.config/Mumble/Mumble/mumble_settings.json

# Autostart
sudo touch /usr/local/bin/ae5900starter
sudo chmod 777 /usr/local/bin/ae5900starter
sudo echo '#!/bin/bash
pavucontrol &
sleep 10
mumble "mumble://ae5900ADM@127.0.0.1:64738" &
sleep 15
lxterminal -e  python3 ~/AE5900_Remote_V2/ae_5900_v2.py
' > /usr/local/bin/ae5900starter
sudo chmod +x /usr/local/bin/ae5900starter
touch ~/.config/autostart/ae5900LXterm.desktop
echo '[Desktop Entry]
Name=ae5900LXTerm
Exec=ae5900starter
Icon=lxterminal
Type=Application
' > ~/.config/autostart/ae5900LXterm.desktop

sudo sed -i 's/^dtparam=audio=on/#dtparam=audio=on/' /boot/firmware/config.txt && \
echo 'dtparam=audio=off' | sudo tee -a /boot/firmware/config.txt
echo 'dtparam=audio=off' | sudo tee -a /boot/firmware/config.txt   
echo 'dtoverlay=vc4-kms-v3d,noaudio' | sudo tee -a /boot/firmware/config.txt   

echo '[window]
width=800
height=400
sinkInputType=1
sourceOutputType=1
sinkType=0
sourceType=1
showVolumeMeters=1
' > ~/.config/pavucontrol.ini

echo "
#######################################################################################################

Mumble wird nun zum ersten mal gestartet und fragt nur nach dem Speicherort der SQL_Database und nach dem Zertifikat. Bitte bestätigen und danach Mumble beenden.

#######################################################################################################

Mumble is now starting for the first time and will only ask for the location of the SQL_Database and the certificate. Please confirm and then close Mumble.

#######################################################################################################
"
sleep 3
mumble "mumble://ae5900ADM@127.0.0.1:64738"

curl -fsSL https://tailscale.com/install.sh | sh   
mv ~/AE5900_Remote_V2/install.sh ~/AE5900_Remote_V2/installation_done.sh
