Eine komplexere LAN/Web-Fernsteuerung für das Albrecht AE-5900 Funkgerät, die das AMM-500 Mikrofon simuliert. Per Webbrowser bedienbar.
=======================================================

## Hauptziel des Projekts:

Entwicklung einer komplexeren LAN/Web-Fernsteuerung für das Albrecht AE-5900.
Es ist zwar nicht mit rigctl oder hamlib vergleichbar, aber es funktioniert.

Falls Du das Funkgerät nicht kennst: https://www.alan-electronics.de/product-details.aspx?WPParams=50C9D4C6C5D2E6BDA5A98494A895
Ich habe mein AE5900 von https://gmw-funktechnik.ch/, einem fantastischen Fachgeschäft für klassische CB- und Amateurfunkgeräte.

## Ein Bild erzählt dir mehr als deine Ehefrau

- Ein Screenshot vom aktuellen UI, im Browser, auf dem Smartphone

  1. visuelles Audiofeedback
  2. Lautsärke des Mikrofons regelbar
  3. Optimierte Scan-Funktion mit regelbarer Geschwindigkeit


	![AE5900_Remote_v2](/pictures/webui.jpg)

- Hier noch ein kurzer Clip. Ich sende hier mit einem Handfunkgerät an meine Heimstation und höre mich auf dem Smartphone

	[![AE5900 Webinterface V2](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Ein Foto, ok, zwei Fotos vom Prototyp

	![AE5900_Remote_v2](/pictures/prototype2.jpg)

## Über das Gerät & Warum

Das Albrecht AE-5900 ist das fantastische neue (2026) FM/AM/SSB/CW-Funkgerät, mit dem ich nicht gerechnet hatte. Es bietet riesiges Potenzial für jede Menge Spaß und hat mich nach 35 Jahren Funkpause wieder zum CB-Funk zurückgebracht.

Also habe ich etwas Zusätzliches dafür gebaut, und jemand (ja, danke nochmal, Kumpel!) hat mir geraten, es auf GitHub zu veröffentlichen. Ich dachte mir: Na gut.

Das Gerät basiert auf einem FT232RL FT232 FTDI USB 3,3 V 5,5 V zu TTL Seriell Adapter, einer günstigen USB-Soundkarte, einem USB-Hub-Breakout-Board, Spulen, Widerständen, Kondensatoren und ein paar Teilen aus meiner Bastelkiste. Es funktioniert einwandfrei und macht mir viel Spaß. Mal sehen, was die nächsten Tage bringen.

Aber warum?

Es ist ein Hobby, für das man einfach nicht genug Zeit haben wird. Besonders, wenn man ein älterer Kerl mit Kindern, Garten, einem oder mehreren Jobs und all den anderen Überraschungen des Lebens. Jetzt kannst du deine Heimstation mit deiner perfekten, selbstgebauten Antenne sogar auf der Toilette deines Arbeitsplatzes oder wo auch immer nutzen.

Genau deshalb.

## So funktioniert es:

1. Schließe das gebastelte Gerät an einen Raspberry Pi oder einen anderen Host-Rechner, auf dem das Python-Skript ausgeführt werden kann an. Dieses Gerät dient dann als Server.
2. Außerdem sollten Mikrofon RJ45 Stecker und Lautsprecherausgang des AE5900 angeschlossen sein.
3. Stelle die Ausgabelautstärke des AE5900 von 0 auf etwa 20 Klicks am Lautstärkeregler hoch.
4. Bestenfalls ist das AE5900 bereits auf FM und den Kanal 1 gesetzt.
5. Stelle an deinem AE5900 Mikrofon TYPE 2 ein, setze deine P1 - P4 Key-Shortcuts. Ich nutze P1 ASQ / P2 VOX / P3 MUTE
6. Starte Mumble auf dem Host-Rechner und deinem Endgerät (Handy /Laptop etc.)
7. Führe `python3 ae_5900_v2.py` auf dem Hostrechner/Server aus.
8. Öffne auf dem Endgerät `HOSTNAMEIP:5000` in deinem Browser. Du solltest nun bereits Kontrolle über dein AE5900 haben.
9. Öffne ganz unten im WebUI das Setup und führe den Sync aus.
10. Setze die entsprechenden Labels für die P1 bis P4 Tasten so, wie du sie am AE5900 gesetzt hast.
11. Auf dem Hostrechner solltest du im Lautstärkeregler (pavucontrol) gegebenenfalls Anpassungen machen. Typische Anpassungen wären hier: Menupunkt "Konfiguration" Standard Soundkarte deine im Nachbau verwendete Soundkarte oder einfach alle anderen "aus". Menupunkt "Eingabegeräte" regelt was du vom AE5900 hörst, also dessen Ausgabe. Ich bin da bei "Basis" was etwa 40% entspricht. Menupunkt "Ausgabeeräte" regelt was du über den RJ45 Stecker in das AE5900 rein gibst, also dein Mikrofon. Ist der Filter korrekt aufgebaut, solltest du hier etwa 70 - 90% verwenden. Dies lässt sich aber auch über die WebUI steuern.
12. Auf dem Hostrechner in Mumble kann nun im In & Output PulseAudio und Standard/Default verwendet werden. Audioeingabe: Die Übertragung sollte auf kontinuierlich gesetzt sein, die Qualität auf c.a 41 kb/s und Audio pro Paket auf 10ms. Audioausgabe: Standardpuffer auf 30 nd die Lautstäre darf auf 100%. Der Rest ist deaktiviert.

Das Script ist derzeitig nur für die Region (EU) ausgelegt. Die anderen Regionen folgen noch, so wie auch der VFO Mode.

Das ist eigentlich alles und wer nicht komplett ahnungslos ist, bekommt das schon hin.

## Die Hardware-Bastelei

Mit Bildern und allem was man wissen muss.

- Vorab mal die Komponenten für den Audiofilter und was man so zum Basteln nutzen kann. Das meisste davon hatte ich in meiner Bastelkiste.

  Für die Audiofilter nutzen wir hier nun:
  
  1. 2x 600:600 Ohm Transformatoren
  2. 1x 100 Ohm Widerstand
  3. 1x 10 KOhm Widerstand
  4. 1x Keramikkondensator 100nF (104) (mindestens einer um die HF zu filtern)
  5. 1x Elco Kondensator 10µF (c.a 16 - 50v)
  6. Klinkenstecker Buchse

	![AE5900_Remote_v2](/pictures/filterkomponenten.jpg)

  Restliche Komponenten:
  
  1. USB Breakoutboard oder einen HUB
  2. FT232RL FT232 FTDI USB 3,3 V 5,5 V zu TTL Seriell Adapter
  3. USB Soundkarte
  4. Rj45 Terminal
  5. Ein Gehäuse aus Metall

	![AE5900_Remote_v2](/pictures/steuerungkomponenten.jpg)

- Ich habe euch ein schönes Bild gemalt. Sieht zwar aus wie von einem Dreijährigen aber so verstehts vielleicht jeder Hobbybastler und Lötkolbenbesitzer.

	![AE5900_Remote_v2](/pictures/overview_v2.png)
	![AE5900_Remote_v2](/pictures/audiofilter.jpg)


Man kann die USB Geräte natürlich auch einfach in einen USB Hub stecken, aber wo bleibt da der Spass am "so klein wie möglich" bauen?
Die beiden Filter muss man aber dennoch löten. 

Es ist auch möglich ohne Klinkenstecker das Audio des AE5900 abzugreifen. Der Mic Plug bietet die Pins EXT-AF und GND. Da liegt ein schwaches Signal, womöglich extra für Soundkarten an.
Hier gibt es aber 2 Proleme. 1. Zumindest auf meinem AE5900 habe ich dort unschöne HF drauf, trotz Mantelwellensperre und Filter. 2. Will man dass das Gerät bei Remotenutzung zu Hause stumm da steht, muss man dennoch einen Klinkenstecker als Terminator verwenden.
Hierzu noch ein Nachtrag: Das Audiosignal lässt sich über EXT-AF abgreifen, ohne zusätzliche GND-Verkabelung. Dies, weil bereits eine GND auf MICG anliegt. Dennoch ist der Anschluss recht HF anfällig. Mit viel Ferrit und gut geschirmten Kabeln mag man das in den Griff bekommen.

Falls ihr HF auf der Leitung habt, euch also auf AM und SSB selber hört, weil eure Mantelwellensperre Schrott ist, lötet paralell zu den Ein- und Ausgängen der Audioverbindungen jeweils noch einen Keramikkondensator 104 (100nF). Das hilft. Auch das Anbringen diverser Klappferrite ist hier hilfreich.

### Wie ist das egentlich möglich

Das AMM-500 sendet seriell HEX codes an das AE-5900 und das AE-5900 antwrtet entsprechend. Damit ist so eniges möglich.
Um die Bastelei zu verwirklichen, musste ich zwischen den beiden Geräten mitlesen.
Prinzip: Man in the middle.

Da das AE-5900 selbst erst nach einem Handshake mit dem AMM-500 seine Codes freigibt, musste dies erst käuflich erworben und sehnlichst erwartet werden.

### Benötigte Software


Mumble & Mumble Server für die Audioübertragung
	
Tailscale auf all den Geräten die für dieses Projekt genutzt werden. :)

	# curl -fsSL https://tailscale.com/install.sh | sh

Dann wird in die Tasten gehauen oder der nachfolgende Krams einfach kopiert und eingefügt.

	# sudo apt update && sudo apt full-upgrade -y

	# sudo apt install git curl openssh-server python3-pyaudio python3-numpy python3-serial python3-flask pipewire pipewire-audio pipewire-alsa pipewire-pulse pipewire pipewire-audio-client-libraries pavucontrol wireplumber libpipewire-0.3-modules ladspa-sdk swh-plugins dbus-user-session mc htop
	# sudo apt remove pipewire-media-session

    # sudo usermod -a -G audio $USER
    # sudo usermod -a -G dialout $USER

    # mkdir ~/.config/pipewire/
    # mkdir ~/.config/pipewire/pipewire.conf.d/

    # mcedit ~/.config/pipewire/pipewire.conf.d/custom.conf

ADD:

context.properties = {
default.clock.rate = 48000
default.clock.allowed-rates = [ 44100 48000 88200 96000 ]
}


    # mkdir ~/.config/pipewire/pipewire-pulse.conf.d/
    # mcedit ~/.config/pipewire/pipewire-pulse.conf.d/99-disable-autogain.conf
ADD:

 pulse.rules = [
{
    matches = [
        { application.process.binary = "mumble" }
        { application.process.binary = "mumble-worker" }
    ]
    actions = { quirks = [ block-source-volume ] }
}
]

    # mcedit ~/.config/pipewire/pipewire-pulse.conf.d/block-autoscale.conf
ADD:

pulse.rules = [ { matches = [ { application.process.binary = "mumble" } ]; actions = { quirks = [ block-source-volume ] } } ]


## Los geht's!

Bestenfalls ist der Rechner neugestartet, damit "sudo usermod -a -G dialout $USER" auch seine Wirkung zeigt.

Wenn die Hardware aufgebaut und alle Einstellungen vorgenommen sind, dann:

	# git clone https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2

	# python3 ~/AE5900_Remote_V2/ae_5900_v2.py

Updaten kann man dann jeweils mit:

	# git pull

### Meine Audioeinstellungen für den Host/Server

Alle nachfolgenden Einstellungen betreffen den Host / Server.
Meine Audioeinstellungen müssen nicht zwangsläufig deine sein.
Sie dienen hier lediglich als Beispiel.

- Pavucontrol:

	![AE5900_Remote_v2](/pictures/pavucontrol1.png)
	![AE5900_Remote_v2](/pictures/pavucontrol2.png)
Der Bereich "PipeWire Alsa" steuert hier lediglich die Audiovisualisierung.


	![AE5900_Remote_v2](/pictures/pavucontrol3.png)
Wichtig: Ausgabe ist Eingabe und umgekehrt. Der bereich Ausgabe steuert somit dein Mic-Gain.
Dies lässt sich aber auch über die WebUI regeln.


	![AE5900_Remote_v2](/pictures/pavucontrol4.png)
Der Berich mit 25% steuert was du hörst. Das AE5900 habe ich auf 25 Klicks am Gerätelautstärkeregler eingestellt.


	![AE5900_Remote_v2](/pictures/pavucontrol5.png)

- Mumble:

	![AE5900_Remote_v2](/pictures/mumble1.png)
	![AE5900_Remote_v2](/pictures/mumble2.png)


Es empfiehlt sich zu Hause einen WebSDR zu betreiben umd die Installation ggf. überrüfen (Kanal/Modulation) zu können.
Ein guter WebSDR lässt sich einfach mit OpenWebRX, einem Raspberry Pi, einem RTL-SDR-Dongle (z. B. RTL-SDR Blog V3 oder V4 / Nooelec NESDR V5) und einer Antenne aufbauen.

Schau dir einfach OpenwebrxPlus an: https://luarvique.github.io/ppa/ RTL-SDR Blog v4: https://www.rtl-sdr.com/v4/

## Was du sonst noch erwarten kannst:

Nichts weiter als meine Erfahrung.
Ich werde keinen persönlichen Support anbieten.
Aber ich werde einige Skripte, Bilder und Ideen hochladen, um sie mit anderen zu teilen.

Ich bin kein Programmierer, aber ich kann Texte lesen, verstehen, umsetzen und in meine Projekte einbauen.

Ich übernehme keine Verantwortung für eure Basteleien. Bei meinem lieben Betatester und bei mir funktionieren Soft - so wie Hardware einwandfrei.
Das Audio bekam in QSO's durchweg gutes Feedback.



