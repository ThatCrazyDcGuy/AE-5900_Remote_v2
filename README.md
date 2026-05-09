# AE5900 Remote Control V2

**Language / Sprache:** [🇩🇪 Deutsch](#deutsch) | [🇬🇧 English](#english)

---

## DEUTSCH

Eine komplexere LAN/Web-Fernsteuerung für das Albrecht AE-5900 Funkgerät, die das AMM-500 Mikrofon simuliert. Per Webbrowser bedienbar.
=======================================================

### Das Vorwort: Der Blickwinkel und das Hörensagen

In Userforen und Gruppen diverser Messenger wird die Legalität des Projekts heiss diskutiert.
Dazu sei folgendes vermerkt:

Dieses Projekt bietet lediglich eine Möglichkeit, das Gerät aus der Ferne zu steuern. Zeigt also nur auf, was unter gegebenen Umständen ohne Modifikation an der Funkgerätehardware technisch möglich ist.
Es handelt sich hierbei auch nicht um eine Modifikation, sondern um einen Adapter, der ein nicht modifiziertes AE5900 (evtl. auch ein AT-5000) aus der Ferne bedienbar macht.
Was jener, der dies hier nachbaut und testet, aus dieser Möglichkeit macht ist seine Angelegenheit.

Der Witz an dieser Diskussion ist jedoch, dass in selbigen Kreisen Powermodifikationen und Frequenzerweiterungen durch direkten Eingriff in die Hardware des Funkgerätes beinahe schon gerühmt werden.

Es sei auch erwähnt, dass das Funkgerät amateurfunktauglich ist und für jene, lizensierte Amateurfunker, der Remotebetrieb legal ist.
Vermerk: Frequenz und Power-Modifikationen werden derzeit auch durch offizielle Shops für kleines Geld angeboten.

Daher:

**WARNUNG!!!** Es besteht die Gefahr, dass die Nutzung je nach Landesbestimmung strafbar ist.
Dummschwätzen und Klugscheissen bleibt aber bis auf weiteres straffrei.

### Hauptziel des Projekts:

Entwicklung einer komplexeren LAN/Web-Fernsteuerung für das Albrecht AE-5900.
Es ist zwar nicht mit rigctl oder hamlib vergleichbar, aber es funktioniert.
Sinn und Zweck ist schlussendlich auch, den CB-Funk wieder zu beleben und atraktiver zu machen.
Flexible Lösungen verschaffen besseren Zugang. Und genau das soll dieses Projekt ermöglichen.

Falls Du das Funkgerät nicht kennst: https://www.alan-electronics.de/product-details.aspx?WPParams=50C9D4C6C5D2E6BDA5A98494A895
Ich habe mein AE5900 von https://gmw-funktechnik.ch/, einem fantastischen Fachgeschäft für klassische CB- und Amateurfunkgeräte.

### Ein Bild erzählt dir mehr als deine Ehefrau

- Ein Screenshot vom aktuellen UI, im Browser, auf dem Smartphone

1. visuelles Audiofeedback
2. Lautstärke des Mikrofons regelbar
3. Optimierte Scan-Funktion mit regelbarer Geschwindigkeit

![AE5900_Remote_v2](/pictures/webui.jpg)

- Hier ein kurzer Clip. Ich sende hier mit einem Handfunkgerät an meine Heimstation und höre mich auf dem Smartphone. (Bildschirmaufnahme des Smartphones)

[![AE5900 Webinterface V2 RX ](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Noch ein kurzer Clip. Ich sende hier mit dem AE5900.  (Bildschirmaufnahme des Smartphones)

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/znx0lKvbVLs/0.jpg)](https://www.youtube.com/shorts/znx0lKvbVLs)

- Diverse Funktionen werden hier vorgestellt. Über mehrere Endgeräte gleichzeitig bedienbar. Der aktuelle, hier gesehene Code wird noch bereinigt und dann veröffentlicht. Leider alles sehr leise.

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/BA9iDk-M_aI/0.jpg)](https://www.youtube.com/watch?v=BA9iDk-M_aI)

- Ein Foto, ok, zwei Fotos in einem vom Prototyp

![AE5900_Remote_v2](/pictures/prototype2.jpg)

### Über das Gerät & Warum

Das Albrecht AE-5900 ist das fantastische neue (2026) FM/AM/SSB/CW-Funkgerät, mit dem ich nicht gerechnet hatte. Es bietet riesiges Potenzial für jede Menge Spaß und hat mich nach 35 Jahren Funkstille wieder "infiziert".

Also habe ich etwas Zusätzliches dafür gebaut, und jemand (ja, danke nochmal, Kumpel!) hat mir geraten, es auf GitHub zu veröffentlichen. Ich dachte mir: Na gut.

Das Gerät basiert auf einem FT232RL FT232 FTDI USB 3,3 V 5,5 V zu TTL Seriell Adapter, einer günstigen USB-Soundkarte, einem USB-Hub-Breakout-Board, Spulen, Widerständen, Kondensatoren und einem Gehäuse aus Metall.

Aber warum?

Es ist ein Hobby, für das man einfach nicht genug Zeit haben wird. Besonders, wenn man ein älterer Kerl mit Kindern, Garten, einem oder mehreren Jobs und all den anderen Überraschungen des Lebens ist.

Genau deshalb.

### So funktioniert es:

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
11. Auf dem Hostrechner solltest du im Lautstärkeregler (pavucontrol) gegebenenfalls Anpassungen machen. Typische Anpassungen wären hier: Menupunkt "Konfiguration" Standard Soundkarte deine im Netzwerk angebundene Soundkarte.
12. Auf dem Hostrechner in Mumble kann nun im In & Output PulseAudio und Standard/Default verwendet werden. Audioeingabe: Die Übertragung sollte auf kontinuierlich gesetzt sein, die Qualität auf etwa 44kb/s.

Das Script ist derzeitig nur für die Region (EU) ausgelegt. Die anderen Regionen folgen noch, so wie auch der VFO Mode.

Das ist eigentlich alles und wer nicht komplett ahnungslos ist, bekommt das schon hin.

### Die Hardware-Bastelei

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
Hier gibt es aber 2 Probleme. 1. Zumindest auf meinem AE5900 habe ich dort unschöne HF drauf, trotz Mantelwellensperre und Filter. 2. Will man dass das Gerät bei Remotenutzung zu Hause stumm da sitzt, sollte man hier eine eigene Schaltung aufbauen.
Hierzu noch ein Nachtrag: Das Audiosignal lässt sich über EXT-AF abgreifen, ohne zusätzliche GND-Verkabelung. Dies, weil bereits eine GND auf MICG anliegt. Hier benötigen wir also eine andere Lösung.

- Hier eine Version der Bastelei ohne Klinkenstecker

![AE5900_Remote_v2](/pictures/rj45audiosingle.png)

Das RX Audio wird hier über EXT-AF und GND abgegriffen. Ohne 600:600 Transformator, dafür aber mit 2x 102 Keramikkondensatoren in Reihe zu den Leitungen und 1x 104 Keramikhondensator paralel zu GND.
Die HF-Einstrahlung ist deutlich minimiert, das Signal aber einiges leiser. Daher muss das AE5900 am Lautärkeregler fast bis Anschlag aufgedreht sein und in den Audiosettings zurückgeregelt werden.

Falls ihr HF auf der Leitung habt, euch also auf AM und SSB selber hört, weil eure Mantelwellensperre Schrott ist, lötet paralell zu den Ein- und Ausgängen der Audioverbindungen jeweils noch ein 100nF Keramikkondensator.

#### Wie ist das eigentlich möglich

Das AMM-500 sendet seriell HEX codes an das AE-5900 und das AE-5900 antwrtet entsprechend. Damit ist so eniges möglich.
Um die Bastelei zu verwirklichen, musste ich zwischen den beiden Geräten mitlesen.
Prinzip: Man in the middle.

Da das AE-5900 selbst erst nach einem Handshake mit dem AMM-500 seine Codes freigibt, musste dies erst käuflich erworben und sehnlichst erwartet werden.

#### Benötigte Software

Mumble & Mumble Server für die Audioübertragung (Audio Chat)

Tailscale auf all den Geräten die für dieses Projekt genutzt werden.
Bei Betrieb im lokalen Netzwerk kann auf Tailscale verzichtet werden.
Tailscale ist für Privatanwender kostenlos, benötigt aber dennoch einen Account.

Dann wird in die Tasten gehauen oder der nachfolgende Krams einfach kopiert und eingefügt.

```bash
sudo apt update && sudo apt full-upgrade -y

sudo apt install git curl openssh-server python3-pyaudio python3-numpy python3-serial python3-flask pipewire pipewire-audio pipewire-alsa pipewire-pulse pipewire pipewire-audio-client-libraries
sudo apt remove pipewire-media-session

sudo usermod -a -G audio $USER
sudo usermod -a -G dialout $USER

mkdir ~/.config/pipewire/
mkdir ~/.config/pipewire/pipewire.conf.d/

mcedit ~/.config/pipewire/pipewire.conf.d/custom.conf
```

ADD:

```
context.properties = {
default.clock.rate = 48000
default.clock.allowed-rates = [ 44100 48000 88200 96000 ]
}
```

```bash
mkdir ~/.config/pipewire/pipewire-pulse.conf.d/
mcedit ~/.config/pipewire/pipewire-pulse.conf.d/99-disable-autogain.conf
```

ADD:

```
pulse.rules = [
{
    matches = [
        { application.process.binary = "mumble" }
        { application.process.binary = "mumble-worker" }
    ]
    actions = { quirks = [ block-source-volume ] }
}
]
```

```bash
mcedit ~/.config/pipewire/pipewire-pulse.conf.d/block-autoscale.conf
```

ADD:

```
pulse.rules = [ { matches = [ { application.process.binary = "mumble" } ]; actions = { quirks = [ block-source-volume ] } } ]
```

Für die Steuerung aus der Ferne:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### Los geht's!

Bestenfalls ist der Rechner neugestartet, damit "sudo usermod -a -G dialout $USER" auch seine Wirkung zeigt.

Wenn die Hardware aufgebaut und alle Einstellungen vorgenommen sind, dann:

```bash
git clone https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2

python3 ~/AE5900_Remote_V2/ae_5900_v2.py
```

Updaten kann man dann jeweils mit:

```bash
git pull
```

#### Meine Audioeinstellungen für den Host/Server

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

### Was noch fehlt // Was noch nicht funktioniert

1. EMG und DW, Funktionen die man auf die P1 - P4 Tasten legen könnte, geben noch keine Rückmeldung an das WebUI.

2. Das Geräteeigene "Scan", welches man auch auf  P1 - P4 Tasten legen könnte, hat ein Timingproblem.
Daher wurde eine eigene S-Scan Funktion implementiert.

### Extras und Testläufe

1. JS8Call funktioniert damit recht gut. Man muss natürlich etwas an den Settings rumspielen und VOX aktivieren.
Es sollte allerdings eine Kleinigkeit sein, hier noch eine PTT Funktion für entsprechende Software zu bauen.

2. User Feedback vom 30. April 2026: Linux Mint um die Version 21.3 und drunter, versteht die Python- Vol- und Vol+ nicht.
Nur falls jemand au so einem System testet. Ein mintupgrade hilft das Problem zu lösen.

3. Das Script ae_5900_maninthemiddle.py wurde hinzugefügt. Damit lassen sich HEX Codes zwischen Mikrofon und Funkgerät auslesen.

### Was du sonst noch erwarten kannst:

Nichts weiter als meine Erfahrung.
Ich werde keinen persönlichen Support anbieten.
Aber ich werde einige Skripte, Bilder und Ideen hochladen, um sie mit anderen zu teilen.

Ich bin kein Programmierer, aber ich kann Texte lesen, verstehen, umsetzen und in meine Projekte einbauen.

Ich übernehme keine Verantwortung für eure Basteleien. Bei meinem lieben Betatester und bei mir funktionieren Soft - so wie Hardware einwandfrei.
Das Audio bekam in QSO's durchweg gutes Feedback.

---

## ENGLISH

A sophisticated LAN/Web remote control for the Albrecht AE-5900 radio that simulates the AMM-500 microphone. Controllable via web browser.
=======================================================

### Foreword: Perspective and Hearsay

The legality of this project is hotly debated in user forums and various messenger groups.
Here's what should be noted:

This project merely provides a way to control the device remotely. It simply demonstrates what is technically possible under given circumstances without hardware modifications to the radio.
This is not a modification, but rather an adapter that makes an unmodified AE5900 (possibly also an AT-5000) remotely operable.
What anyone who builds and tests this does with this capability is their own business.

The irony of this discussion is that in the same circles, power modifications and frequency extensions through direct hardware interference with the radio are almost celebrated.

It should also be noted that the radio is suitable for amateur radio use, and for licensed amateur radio operators, remote operation is legal.
Note: Frequency and power modifications are currently even offered by official shops for little money.

Therefore:

**WARNING!!!** There is a risk that use may be punishable depending on the laws of your country.
Talking nonsense and showing off remains unpunished for the time being.

### Main Goal of the Project:

Development of a sophisticated LAN/web remote control for the Albrecht AE-5900.
While it's not comparable to rigctl or hamlib, it works.
Ultimately, the purpose is also to revive CB radio and make it more attractive.
Flexible solutions provide better access. And that's exactly what this project should enable.

If you don't know the radio: https://www.alan-electronics.de/product-details.aspx?WPParams=50C9D4C6C5D2E6BDA5A98494A895
I got my AE5900 from https://gmw-funktechnik.ch/, a fantastic specialist shop for classic CB and amateur radio equipment.

### A Picture is Worth a Thousand Words

- A screenshot of the current UI in the browser on the smartphone

1. Visual audio feedback
2. Microphone volume adjustable
3. Optimized scan function with adjustable speed

![AE5900_Remote_v2](/pictures/webui.jpg)

- Here's a short clip. I'm transmitting with a handheld to my home station and listening to myself on my smartphone. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 RX ](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Another short clip. I'm transmitting with the AE5900. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/znx0lKvbVLs/0.jpg)](https://www.youtube.com/shorts/znx0lKvbVLs)

- Various features are demonstrated here. Operable via multiple devices simultaneously. The code shown here will be cleaned up and then published. Unfortunately, everything is very quiet.

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/BA9iDk-M_aI/0.jpg)](https://www.youtube.com/watch?v=BA9iDk-M_aI)

- A photo, well, two photos in one of the prototype

![AE5900_Remote_v2](/pictures/prototype2.jpg)

### About the Device & Why

The Albrecht AE-5900 is the fantastic new (2026) FM/AM/SSB/CW radio that I didn't expect. It offers huge potential for lots of fun and has "infected" me again after 35 years of radio silence.

So I built something extra for it, and someone (yes, thanks again, buddy!) advised me to publish it on GitHub. I thought: why not.

The device is based on an FT232RL FT232 FTDI USB 3.3V 5.5V to TTL serial adapter, an inexpensive USB soundcard, a USB hub breakout board, coils, resistors, capacitors, and a metal enclosure.

But why?

It's a hobby for which you simply won't have enough time. Especially if you're an older guy with kids, a garden, one or more jobs, and all the other surprises life brings.

That's exactly why.

### How It Works:

1. Connect the custom device to a Raspberry Pi or another host computer on which the Python script can be executed. This device then serves as a server.
2. Also connect the microphone RJ45 connector and speaker output of the AE5900.
3. Increase the output volume of the AE5900 from 0 to about 20 clicks on the volume control.
4. Ideally, the AE5900 is already set to FM and channel 1.
5. Set your AE5900 microphone to TYPE 2, set your P1 - P4 key shortcuts. I use P1 ASQ / P2 VOX / P3 MUTE
6. Start Mumble on the host computer and your device (phone/laptop, etc.)
7. Run `python3 ae_5900_v2.py` on the host/server.
8. Open `HOSTNAMEIP:5000` in your browser on the device. You should now have control of your AE5900.
9. Open Setup at the bottom of the WebUI and run Sync.
10. Set the appropriate labels for the P1 to P4 buttons as you have set them on the AE5900.
11. On the host computer, you may need to make adjustments in the volume control (pavucontrol). Typical adjustments would be: Menu item "Configuration" default sound card your network-connected sound card.
12. On the host computer in Mumble, PulseAudio and Standard/Default can now be used for input and output. Audio input: Transmission should be set to continuous, quality to about 44kb/s.

The script is currently only designed for the EU region. Other regions will follow, as will VFO mode.

That's basically it, and anyone who's not completely clueless should be able to figure it out.

### The Hardware Build

With pictures and everything you need to know.

- First, the components for the audio filter and what you can use for building. Most of it I had in my parts box.

For the audio filters we use:

1. 2x 600:600 Ohm transformers
2. 1x 100 Ohm resistor
3. 1x 10 kOhm resistor
4. 1x 100nF ceramic capacitor (104) (at least one to filter the RF)
5. 1x 10µF electrolytic capacitor (approx. 16 - 50v)
6. Jack connector socket

![AE5900_Remote_v2](/pictures/filterkomponenten.jpg)

Remaining components:

1. USB breakout board or a hub
2. FT232RL FT232 FTDI USB 3.3V 5.5V to TTL serial adapter
3. USB soundcard
4. RJ45 terminal
5. A metal enclosure

![AE5900_Remote_v2](/pictures/steuerungkomponenten.jpg)

- I drew you a nice picture. It looks like it was drawn by a three-year-old, but maybe every hobbyist builder and soldering iron owner will understand it.

![AE5900_Remote_v2](/pictures/overview_v2.png)
![AE5900_Remote_v2](/pictures/audiofilter.jpg)

Of course, you can also just plug the USB devices into a USB hub, but where's the fun in building "as small as possible"?
But you still have to solder the two filters.

It's also possible to tap the AE5900's audio without a jack connector. The Mic plug offers the pins EXT-AF and GND. There's a weak signal there, possibly specifically for sound cards.
However, there are 2 problems with this. 1. At least on my AE5900, I have ugly RF noise there, despite shielded cable and filters. 2. If you want the device to sit silently at home during remote use, you should build a separate circuit here.
Additional note: The audio signal can be tapped via EXT-AF without additional GND wiring. This is because there's already a GND on MICG. Here we need a different solution.

- Here's a version of the build without a jack connector

![AE5900_Remote_v2](/pictures/rj45audiosingle.png)

The RX audio is tapped here via EXT-AF and GND. Without a 600:600 transformer, but with 2x 102 ceramic capacitors in series to the lines and 1x 104 ceramic capacitor in parallel to GND.
RF radiation is significantly reduced, but the signal is somewhat quieter. Therefore, the AE5900 must be turned up almost to maximum on the volume control and then adjusted back in the audio settings.

If you have RF on the line, i.e., you hear yourself on AM and SSB because your shielded cable is junk, solder a 100nF ceramic capacitor in parallel to the inputs and outputs of the audio connections.

#### How Is This Actually Possible

The AMM-500 sends hex codes serially to the AE-5900 and the AE-5900 responds accordingly. This makes a lot possible.
To make the build work, I had to listen in between the two devices.
Principle: Man in the middle.

Since the AE-5900 itself only releases its codes after a handshake with the AMM-500, this had to be purchased and eagerly awaited.

#### Required Software

Mumble & Mumble Server for audio transmission (audio chat)

Tailscale on all devices used for this project.
When operating on a local network, Tailscale can be omitted.
Tailscale is free for private users but requires an account.

Then you hit the keys or just copy and paste the following stuff.

```bash
sudo apt update && sudo apt full-upgrade -y

sudo apt install git curl openssh-server python3-pyaudio python3-numpy python3-serial python3-flask pipewire pipewire-audio pipewire-alsa pipewire-pulse pipewire pipewire-audio-client-libraries
sudo apt remove pipewire-media-session

sudo usermod -a -G audio $USER
sudo usermod -a -G dialout $USER

mkdir ~/.config/pipewire/
mkdir ~/.config/pipewire/pipewire.conf.d/

mcedit ~/.config/pipewire/pipewire.conf.d/custom.conf
```

ADD:

```
context.properties = {
default.clock.rate = 48000
default.clock.allowed-rates = [ 44100 48000 88200 96000 ]
}
```

```bash
mkdir ~/.config/pipewire/pipewire-pulse.conf.d/
mcedit ~/.config/pipewire/pipewire-pulse.conf.d/99-disable-autogain.conf
```

ADD:

```
pulse.rules = [
{
    matches = [
        { application.process.binary = "mumble" }
        { application.process.binary = "mumble-worker" }
    ]
    actions = { quirks = [ block-source-volume ] }
}
]
```

```bash
mcedit ~/.config/pipewire/pipewire-pulse.conf.d/block-autoscale.conf
```

ADD:

```
pulse.rules = [ { matches = [ { application.process.binary = "mumble" } ]; actions = { quirks = [ block-source-volume ] } } ]
```

For remote control:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### Let's Get Started!

It's best if the computer has been restarted so that "sudo usermod -a -G dialout $USER" takes effect.

Once the hardware is set up and all settings are made, then:

```bash
git clone https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2

python3 ~/AE5900_Remote_V2/ae_5900_v2.py
```

You can update with:

```bash
git pull
```

#### My Audio Settings for the Host/Server

All of the following settings relate to the host / server.
My audio settings don't necessarily have to be yours.
They serve merely as an example here.

- Pavucontrol:

![AE5900_Remote_v2](/pictures/pavucontrol1.png)
![AE5900_Remote_v2](/pictures/pavucontrol2.png)
The "PipeWire Alsa" area here only controls the audio visualization.

![AE5900_Remote_v2](/pictures/pavucontrol3.png)
Important: Output is input and vice versa. The output area thus controls your mic gain.
This can also be controlled via the WebUI.

![AE5900_Remote_v2](/pictures/pavucontrol4.png)
The area with 25% controls what you hear. I have the AE5900 set to 25 clicks on the device volume control.

![AE5900_Remote_v2](/pictures/pavucontrol5.png)

- Mumble:

![AE5900_Remote_v2](/pictures/mumble1.png)
![AE5900_Remote_v2](/pictures/mumble2.png)

It's a good idea to run a WebSDR at home to check your installation if necessary (channel/modulation).
A good WebSDR can be easily set up with OpenWebRX, a Raspberry Pi, an RTL-SDR dongle (e.g., RTL-SDR Blog V3 or V4 / Nooelec NESDR V5), and an antenna.

Check out OpenwebrxPlus: https://luarvique.github.io/ppa/ RTL-SDR Blog v4: https://www.rtl-sdr.com/v4/

### What's Still Missing // What Doesn't Work Yet

1. EMG and DW, functions that could be placed on the P1 - P4 buttons, don't yet provide feedback to the WebUI.

2. The device's own "Scan", which could also be placed on P1 - P4 buttons, has a timing problem.
Therefore, a custom S-Scan function has been implemented.

### Extras and Test Runs

1. JS8Call works quite well with it. Of course, you have to play around with the settings a bit and enable VOX.
But it should be simple to add a PTT function for the appropriate software.

2. User feedback from April 30, 2026: Linux Mint around version 21.3 and below don't understand the Python Vol- and Vol+.
Just in case someone tests on such a system. A mint upgrade helps solve the problem.

3. The script ae_5900_maninthemiddle.py has been added. With this you can read hex codes between the microphone and the radio.

### What Else to Expect:

Nothing more than my experience.
I will not provide personal support.
But I will upload some scripts, images, and ideas to share with others.

I am not a programmer, but I can read, understand, implement, and incorporate texts into my projects.

I take no responsibility for your builds. For my dear beta tester and me, both software and hardware work flawlessly.
The audio received consistently good feedback in QSOs.
