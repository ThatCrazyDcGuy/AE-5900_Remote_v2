# AE5900 Remote Control V2

Wechsle Sprache zu DE: [🇩🇪 Deutsch](https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2/blob/main/README_DE.md)

## ENGLISH VERSION OF README

A LAN/Web Rig Control System for the Albrecht AE-5900 radio, simulating the AMM-500 microphone. This allows the AE5900 to be operated via a web browser in a webinterface.
=======================================================

### The Foreword:

**WARNING!!!** There is a risk that using this equipment may be illegal, depending on the laws of your country.
Consider this with your conscience. I'm not your mother!

### Main Goal of the Project:

Development of a sophisticated LAN/web remote control for the Albrecht AE-5900.
While it's not comparable to rigctl or hamlib, it works.
Ultimately, the purpose is also to revive CB radio and make it more attractive.
Flexible solutions provide better access. And that's exactly what this project should enable.

### A picture will tell you more than your wife:

- A screenshot of the current UI, in the browser, on your smartphone

1. Visual audio feedback
2. Adjustable microphone volume
3. Optimized scan function with adjustable speed
4. Clarifier
5. Lock
6. Mute
7. Vox
8. MW (multi chanel scan)
9. Squelch // Autosquelch
10. PTT kill switch activates after 30 seconds following connection loss.
11. Own roger beeps. Just add them to folder beeps.
12. Physically PTT key / Special key on phone or keyboard
13. Country codes must be set in the web interface and on the device.

![AE5900_Remote_v2](/pictures/webui_last.jpg)

- Here's a short clip. I'm transmitting with a handheld to my home station and listening to myself on my smartphone. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 RX ](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Another short clip. I'm transmitting with the AE5900. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/znx0lKvbVLs/0.jpg)](https://www.youtube.com/shorts/znx0lKvbVLs)

- Various features are demonstrated here. Operable via multiple devices simultaneously. The code shown here will be cleaned up and then published. Unfortunately, everything is very quiet.

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/2GPGKDhqmEw/0.jpg)](https://www.youtube.com/watch?v=2GPGKDhqmEw)

- A photo of the newest prototype without jack conector. All audio & control over RJ45.

![AE5900_Remote_v2](/pictures/v218mar2.jpeg)

### How It Works:

1. Connect the custom device to a Raspberry Pi or another host computer on which the Python script can be executed. This device then serves as a server.
2. Connect the Adapter to Mic Port of AE5900.
3. You have to plug a jack plug into the PA/EXT output as a dummy to silence the speaker.
4. Increase the output volume of the AE5900 from 0 to about 75% on the volume control.
5. Ensure proper grounding to prevent rf.
6. Ideally, the AE5900 is already set to FM and channel 1.
7. Set your AE5900 microphone to TYPE 2, set your P1 - P4 key shortcuts. I use P1 ASQ / P2 VOX / P3 MUTE
8. Start Mumble on the host computer and your device (phone/laptop, etc.)
9. Run `python3 ae_5900_v2.py` on the host/server.
10. Open `HOSTNAMEIP:5000` in your browser on the device. You should now have control of your AE5900.
11. Open Setup at the bottom of the WebUI and run Sync.
12. Set the appropriate labels for the P1 to P4 buttons as you have set them on the AE5900.
13. On the host computer, you may need to make adjustments in the volume control (pavucontrol). Typical adjustments would be: Menu item "Configuration" default sound card your network-connected sound card.
14. On the host computer in Mumble, PulseAudio and Standard/Default can now be used for input and output. Audio input: Transmission should be set to continuous, quality to about 44kb/s.

The script is currently designed for ALL region. VFO mode will follow.

That's basically it, and anyone who's not completely clueless should be able to figure it out.

### Minimum requirements for this project:

1. Reading comprehension skills
2. Understanding skills
3. Implementation skills
4. Soldering experience
5. Raspberry Pi 3
6. Some spare cash for parts

### The Hardware Build

With pictures and everything you need to know.

- First, the components for the audio filter and what you can use for building. Most of it I had in my parts box.

For the audio filters we use:

1. 1x 600:600 Ohm transformers
2. 1x 100 Ohm resistor
3. 1x 10 kOhm resistor
4. 1x 10nF ceramic capacitor (103) (at least one to filter the RF)
5. 1x 10µF electrolytic capacitor (approx. 16 - 50v)

Remaining components:

1. USB breakout board or a hub
2. FT232RL FT232 FTDI USB 3.3V 5.5V to TTL serial adapter
3. USB soundcard
4. RJ45 terminal
5. A metal enclosure

![AE5900_Remote_v2](/pictures/allpartsv2.jpg)

- I've drawn you a nice picture. It might look like it was drawn by a three-year-old, but any hobbyist and soldering iron owner should be able to understand it.

![AE5900_Remote_v2](/pictures/overview_v3.png)

You can, of course, simply plug the USB devices into a USB hub, but where's the fun in building something "as small as possible"?
You still have to solder the two filters, though.

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

For those who prefer a more relaxed approach, using a fresh Raspberry Pi Trixie image:

This block will first install the script and system updates on the Raspberry Pi.
Then, everything necessary, such as Python, Mumble, audio, and Tailscale, will be installed.
Finally, the settings in Mumble and the audio will be adjusted, and a simple autostart will be added.
After restarting, Mumble will ask for the certificate and the database location.
Now restart again, and everything is set up for the first test run.

Simply copy the entire block into the console.

```bash
git clone https://github.com/ThatCrazyDcGuy/AE5900_Remote_V2
cd ~/AE5900_Remote_V2/
sudo chmod +x install.sh
./install.sh
#If you want to use tailscale:
#Copy the created TailscaleLink into your browser and follow the instructions
sudo tailscale up
reboot
````

#### My Audio Settings for the Host/Server

All of the following settings relate to the host / server.
My audio settings don't necessarily have to be yours.
They serve merely as an example here.

- Pavucontrol:

![AE5900_Remote_v2](/pictures/pavucontrolsettings.png)

- Mumble:

![AE5900_Remote_v2](/pictures/mumblesettings.png)

It's a good idea to run a WebSDR at home to check your installation if necessary (channel/modulation).
A good WebSDR can be easily set up with OpenWebRX, a Raspberry Pi, an RTL-SDR dongle (e.g., RTL-SDR Blog V3 or V4 / Nooelec NESDR V5), and an antenna.

Check out OpenwebrxPlus: https://luarvique.github.io/ppa/ RTL-SDR Blog v4: https://www.rtl-sdr.com/v4/

### What's Still Missing // What Doesn't Work Yet

1. There's always something missing. What isn't there, will come later.

2. ....

### Version Info & Changelog (always perform updates with 'git pull')


Current: V-240626 i1/a4 JS8

1. Reimplementation of JS8call control.
   
 As trigger in JS8call in Radio / Rigoptions (will switch on/off automatically) use:

```bash
curl -s http://127.0.0.1:5000/api/cmd/TX?state=%1"
````
 In other digimodes use for TX:
  ```bash
  curl -s http://127.0.0.1:5000/api/cmd/TX?state=%1
````
 For RX:
 
   ```bash
    curl -s http://127.0.0.1:5000/api/cmd/TX?state=%0"
   ````

Replace 127.0.0.1 with your ip.
You can also build a on/off script with these commands.

2. VOX bugfixes

Previous version: V-210626 i6/a9 BPLC

1. ALL country codes added. Greetings to my testers in Poland and Great Britain.
2. Again, some Bugfixes for FW 1.12 users.

Previous version: V-190626 i2/a5 CQRP

1. New terminal keys can be selected and edited in Setup & Sync.
2. Keys can be used to record and play back QSOs, as well as to record and repeat CQ calls. This function can be selected in Setup & Sync.
3. Bugfixes

Previous version: V-170626 i4/a1 FLK

1. Some bugfixes in UI.
2. A/SQ level to display added. Please first use A/SQ Res. (will run about 25sec) then use the A/SQ +/- buttons.
3. Ugly movement of buttons fixed.

Previous version: V-150626 i4/a5 BTN

1. Button bugfixes.

Previous version: V-120626 i1/a1 LN-RB

1. Roger beep switch added.

Previous version: V-110626 i9/a9 LNG

1. The language of the manual under Setup & Sync changes according to the browser language setting.

Previous version: V-110626 i8/a9 VX-RB-SM-MW

1. VOX function fixed.
2. Rogebeep function implemented.
3. Simulation mode added for testing without the box.
4. MultiWatch fixed.


### Extras and Test Runs

1. JS8Call works quite well with it. Of course, you have to play around with the settings a bit and enable VOX.
But it should be simple to add a PTT function for the appropriate software.

2. User feedback from April 30, 2026: Linux Mint around version 21.3 and below don't understand the Python Vol- and Vol+.
Just in case someone tests on such a system. A mint upgrade helps solve the problem.

### What Else to Expect:

Nothing more than my experience.
I will not provide personal support.
But I will upload some scripts, images, and ideas to share with others.

I am not a programmer, but I can read, understand, implement, and incorporate texts into my projects.

I take no responsibility for your builds. For my dear beta tester and me, both software and hardware work flawlessly.
The audio received consistently good feedback in QSOs.
