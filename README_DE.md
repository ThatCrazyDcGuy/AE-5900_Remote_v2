# AE5900 Remote Control V2

Switch lang. to EN: [🇬🇧 English](https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2/blob/main/README.md)

## DEUTSCHE VERSION DER README:

Ein LAN/Web Rig Control System für das Albrecht AE-5900 Funkgerät, dass das AMM-500 Mikrofon simuliert. Das AE5900 wird so per Webbrowser in einem Webinterface bedienbar.
=======================================================

### Das Vorwort:

**WARNUNG!!!** Es besteht die Gefahr, dass die Nutzung je nach Landesbestimmung strafbar ist.
Klärt das mit eurem Gewissen. Ich bin nicht eure Mutti!

### Hauptziel des Projekts:

Entwicklung einer LAN/Web-Fernsteuerung für das Albrecht AE-5900.
Es ist zwar nicht mit rigctl oder hamlib vergleichbar, aber es funktioniert.
Sinn und Zweck ist schlussendlich auch, das Thema Funk wieder zu beleben und attraktiver zu machen.
Flexible Lösungen verschaffen besseren Zugang. Und genau das soll dieses Projekt ermöglichen.

### Ein Bild erzählt dir mehr als deine Ehefrau:

- Ein Screenshot vom aktuellen UI, im Browser, auf dem Smartphone

1. Visuelles Audiofeedback
2. Lautstärke des Mikrofons regelbar
3. Optimierte Scan-Funktion mit regelbarer Geschwindigkeit
4. Clarifier
5. Lock
6. Mute
7. Vox
8. MW (multi chanel scan)
9. Squelch // Autosquelch
10. Der PTT-Kill-Schalter wird 30 Sekunden nach Verbindungsverlust aktiviert.
11. Eigene Rogerbeeps erstellen. Einfach zu den Bestätigungstönen im Ordner hinzufügen.
12. Physische PTT-Taste/Sondertaste am Telefon oder an der Tastatur verwenden.

![AE5900_Remote_v2](/pictures/webui_last.jpg)

- Hier ein kurzer Clip. Ich sende hier mit einem Handfunkgerät an meine Heimstation und höre mich auf dem Smartphone. (Bildschirmaufnahme des Smartphones)

[![AE5900 Webinterface V2 RX ](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Noch ein kurzer Clip. Ich sende hier mit dem AE5900.  (Bildschirmaufnahme des Smartphones)

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/znx0lKvbVLs/0.jpg)](https://www.youtube.com/shorts/znx0lKvbVLs)

- Diverse Funktionen werden hier vorgestellt. Über mehrere Endgeräte gleichzeitig bedienbar. Der aktuelle, hier gesehene Code wird noch bereinigt und dann veröffentlicht. Leider alles sehr leise.

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/2GPGKDhqmEw/0.jpg)](https://www.youtube.com/watch?v=2GPGKDhqmEw)

- Ein Foto vom neuesten Prototyp ohne Klinkenstecker. Audio und Steuerung über RJ45.

![AE5900_Remote_v2](/pictures/v218mar2.jpeg)

### So funktioniert es:

1. Schließe das gebastelte Gerät an einen Raspberry Pi oder einen anderen Host-Rechner, auf dem das Python-Skript ausgeführt werden kann an. Dieses Gerät dient dann als Server.
2. Adapter mit dem Mikrofonport verbinden.
3. Um den Lautsprecher stummzuschalten, muss ein Klinkenstecker als Blindstecker in den PA/EXT-Ausgang eingesteckt werden.
4. Stelle die Ausgabelautstärke des AE5900 von 0 auf etwa 75% am Lautstärkeregler hoch.
5. Sorgen Sie für eine ordnungsgemäße Erdung, um HF-Störungen zu vermeiden.
6. Bestenfalls ist das AE5900 bereits auf FM und den Kanal 1 gesetzt.
7. Stelle an deinem AE5900 Mikrofon TYPE 2 ein, setze deine P1 - P4 Key-Shortcuts. Ich nutze P1 ASQ / P2 VOX / P3 MUTE
8. Starte Mumble auf dem Host-Rechner und deinem Endgerät (Handy /Laptop etc.)
9. Führe `python3 ae_5900_v2.py` auf dem Hostrechner/Server aus.
10. Öffne auf dem Endgerät `HOSTNAMEIP:5000` in deinem Browser. Du solltest nun bereits Kontrolle über dein AE5900 haben.
11. Öffne ganz unten im WebUI das Setup und führe den Sync aus.
12. Setze die entsprechenden Labels für die P1 bis P4 Tasten so, wie du sie am AE5900 gesetzt hast.
13. Auf dem Hostrechner solltest du im Lautstärkeregler (pavucontrol) gegebenenfalls Anpassungen machen. Typische Anpassungen wären hier: Menupunkt "Konfiguration" Standard Soundkarte deine im Netzwerk angebundene Soundkarte.
14. Auf dem Hostrechner in Mumble kann nun im In & Output PulseAudio und Standard/Default verwendet werden. Audioeingabe: Die Übertragung sollte auf kontinuierlich gesetzt sein, die Qualität auf etwa 44kb/s.

Das Script ist derzeitig nur für die Region (EU) ausgelegt. Die anderen Regionen folgen noch, so wie auch der VFO Mode.

Das ist eigentlich alles und wer nicht komplett ahnungslos ist, bekommt das schon hin.

### Mindestanforderung für dieses Projekt:

1. Die Fähigkeit zu lesen
2. Die Fähigkeit zu verstehen
3. Die Fähigkeit umzusetzen
4. Lötkolbenerfahrung
5. Raspberry PI 3
6. Etwas Kleingeld für die Teile

### Die Hardware-Bastelei

Mit Bildern und allem was man wissen muss.

- Vorab mal die Komponenten für den Audiofilter und was man so zum Basteln nutzen kann. Das meisste davon hatte ich in meiner Bastelkiste.

Für die Audiofilter nutzen wir hier nun:

1. 1x 600:600 Ohm Transformatoren
2. 1x 100 Ohm Widerstand
3. 1x 10 KOhm Widerstand
4. 1x Keramikkondensator 10nF (103) (mindestens einer um die HF zu filtern)
5. 1x Elco Kondensator 10µF (c.a 16 - 50v)

Restliche Komponenten:

1. USB Breakoutboard oder einen HUB
2. FT232RL FT232 FTDI USB 3,3 V 5,5 V zu TTL Seriell Adapter
3. USB Soundkarte
4. Rj45 Terminal
5. Ein Gehäuse aus Metall

![AE5900_Remote_v2](/pictures/allpartsv2.jpg)

- Ich habe euch ein schönes Bild gemalt. Sieht zwar aus wie von einem Dreijährigen aber so verstehts vielleicht jeder Hobbybastler und Lötkolbenbesitzer.

![AE5900_Remote_v2](/pictures/overview_v3.png)

Man kann die USB Geräte natürlich auch einfach in einen USB Hub stecken, aber wo bleibt da der Spass am "so klein wie möglich" bauen?
Die beiden Filter muss man aber dennoch löten.

#### Wie ist das eigentlich möglich

Das AMM-500 sendet seriell HEX codes an das AE-5900 und das AE-5900 antwrtet entsprechend. Damit ist so eniges möglich.
Um die Bastelei zu verwirklichen, musste ich zwischen den beiden Geräten mitlesen.
Prinzip: Man in the middle.

Da das AE-5900 selbst erst nach einem Handshake mit dem AMM-500 seine Codes freigibt, musste dies erst käuflich erworben und sehnlichst erwartet werden.

#### Benötigte Software // Installation

Mumble & Mumble Server für die Audioübertragung (Audio Chat)

Tailscale auf all den Geräten die für dieses Projekt genutzt werden.
Bei Betrieb im lokalen Netzwerk kann auf Tailscale verzichtet werden.
Tailscale ist für Privatanwender kostenlos, benötigt aber dennoch einen Account.

Für die ganz faulen, mit frisch installiertem Raspberry Trixie Image:

Mit diesem Block wird das Raspberry zuerst mit dem Script und den System-Updates gefüttert.
Danach wird alles notwendige wie Python, Mumble, Audio, Tailscale installiert.
Zum Schluss werden die Settings in Mumble und dem Audio angepasst, so wie ein stupider/einfacher Autostart hinzugefügt.
Nach dem Neustart wird Mumble fragen stellen: Nach dem Zertifikat und dem Speicherort der Datenbank.
Nun nochmals neustarten und alles ist für den ersten Testlauf eingerichtet.

Kopiert einfach den gesamten Block in die Konsole.

```bash
git clone https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2
cd ~/AE5900_Remote_V2/
sudo chmod +x install.sh
./install.sh
#Wer tailscale nutzen möchte:
#Kopiere den erstellten TailscaleLink in deinen Browser und folge der Anleitung
sudo tailscale up
reboot
```
#### Meine Audioeinstellungen für den Host/Server

Alle nachfolgenden Einstellungen betreffen den Host / Server.
Meine Audioeinstellungen müssen nicht zwangsläufig deine sein.
Sie dienen hier lediglich als Beispiel.

- Pavucontrol:

![AE5900_Remote_v2](/pictures/pavucontrolsettings.png)

- Mumble:

![AE5900_Remote_v2](/pictures/mumblesettings.png)

Es empfiehlt sich zu Hause einen WebSDR zu betreiben umd die Installation ggf. überrüfen (Kanal/Modulation) zu können.
Ein guter WebSDR lässt sich einfach mit OpenWebRX, einem Raspberry Pi, einem RTL-SDR-Dongle (z. B. RTL-SDR Blog V3 oder V4 / Nooelec NESDR V5) und einer Antenne aufbauen.

### Was noch fehlt // Was noch nicht funktioniert

1. Es fehlt immer irgendetwas. Was nicht ist, das kommt noch.

2. ....

### Versionsinformationen & Änderungsübersicht (Aktualisierungen immer mit „git pull“ durchführen)


Aktuell: V-190626 i2/a5 CQRP

1. Neue Terminaltasten können unter „Einstellungen & Synchronisierung“ ausgewählt und bearbeitet werden.
2. Mit den Tasten können QSOs aufgezeichnet und wiedergegeben sowie CQ-Rufzeichen aufgezeichnet und wiederholt werden. Diese Funktion kann unter „Einstellungen & Synchronisierung“ aktiviert werden.
3. Fehlerbehbungen

Vorherige Version: V-170626 i4/a1 FLK

1. Einige Bugfixes in der Benutzeroberfläche
2. A/SQ-Ebene zur Anzeige hinzugefügt. Bitte verwende zunächst A/SQ Res. (dauert etwa 25 Sekunden) und verwende dann die Tasten A/SQ +/-.
3. Unschöne Tastenbewegung behoben.

Vorherige Version: V-150626 i4/a5 BTN

1. Fehlerbehebungen für Schaltflächen. Bei Fehlern bitte 140626ae_5900_v2.py verwenden.

Vorherige Version: V-120626 i1/a1 LN-RB

1. Roger-Piepton-Schalter hinzugefügt

Vorherige Version: V-110626 i9/a9 LNG

1. Die Sprache des Handbuchs unter „Einrichtung & Synchronisierung“ ändert sich entsprechend der Browsersprache.

Vorherige Version: V-110626 i8/a9 VX-RB-SM-MW

1. VOX-Funktion korrigiert
2. Rogebeep-Funktion implementiert
3. Simulationsmodus für Tests ohne Box hinzugefügt
4. MultiWatch-Fehler behoben

### Extras und Testläufe

1. JS8Call funktioniert damit recht gut. Man muss natürlich etwas an den Settings rumspielen und VOX aktivieren.
Es sollte allerdings eine Kleinigkeit sein, hier noch eine PTT Funktion für entsprechende Software zu bauen.

2. User Feedback vom 30. April 2026: Linux Mint um die Version 21.3 und drunter, versteht die Python- Vol- und Vol+ nicht.
Nur falls jemand au so einem System testet. Ein mintupgrade hilft das Problem zu lösen.

### Was du sonst noch erwarten kannst:

Nichts weiter als meine Erfahrung.
Ich werde keinen persönlichen Support anbieten.
Aber ich werde einige Skripte, Bilder und Ideen hochladen, um sie mit anderen zu teilen.

Ich bin kein Programmierer, aber ich kann Texte lesen, verstehen, umsetzen und in meine Projekte einbauen.

Ich übernehme keine Verantwortung für eure Basteleien. Bei meinem lieben Betatester und bei mir funktionieren Soft - so wie Hardware einwandfrei.
Das Audio bekam in QSO's durchweg gutes Feedback.

---

