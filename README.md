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

If you don't know the radio: https://www.alan-electronics.de/product-details.aspx?WPParams=50C9D4C6C5D2E6BDA5A98494A895
I got my AE5900 from https://gmw-funktechnik.ch/, a fantastic specialist shop for classic CB and amateur radio equipment.

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

![AE5900_Remote_v2](/pictures/webui260526_1.jpeg)

- Here's a short clip. I'm transmitting with a handheld to my home station and listening to myself on my smartphone. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 RX ](https://img.youtube.com/vi/vvg-HywBKIc/0.jpg)](https://www.youtube.com/shorts/vvg-HywBKIc)

- Another short clip. I'm transmitting with the AE5900. (Screenshot of the smartphone)

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/znx0lKvbVLs/0.jpg)](https://www.youtube.com/shorts/znx0lKvbVLs)

- Various features are demonstrated here. Operable via multiple devices simultaneously. The code shown here will be cleaned up and then published. Unfortunately, everything is very quiet.

[![AE5900 Webinterface V2 TX ](https://img.youtube.com/vi/BA9iDk-M_aI/0.jpg)](https://www.youtube.com/watch?v=BA9iDk-M_aI)

- A photo of the newest prototype without jack conector. All audio & control over RJ45.

![AE5900_Remote_v2](/pictures/v218mar2.jpeg)

For using RX and TX audio via the RJ45 microphone connector, please note the following:

1. Omit the jack-to-600:600 transformer circuit and connect one 103 ceramic capacitor in paralel with the lines and one 100 Ohm resistor in series on signal line. The RX audio is then tapped from the microphone/RJ45 connector via EXT-AF and ground.
2. Proper grounding of the transceiver becomes more important than ever. This alone can prevent approximately 90% of RF interference from reaching the sound card.
3. The audio settings will change slightly because the capacitors attenuate the signal more than the transformer circuit. You will need to turn up the volume on the transceiver.
4. You have to plug a jack plug into the PA/EXT output as a dummy.

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

- I've drawn you a nice picture. It might look like it was drawn by a three-year-old, but any hobbyist and soldering iron owner should be able to understand it. Ignore the jack-to-transformer part.

Use the 10nF // 100 Ohm circuit described above for the RX audio signal. A new schematic will follow.

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
