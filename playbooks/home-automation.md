# One app for the whole house

We had five vendor apps for one house. Some worked badly, not everyone in the family had access, and none could give someone access for a set period. So we built one private web app with Claude Code that controls all of it.

The code itself is not published. It is tied to one house: its rooms, its devices, its people. What follows is the pattern, and the things that bit us along the way.

## The shape

- **One home server.** A Mac mini M4 runs the app as a container, behind the same Caddy and Cloudflare tunnel as our other apps (see [running-on-a-mac-mini.md](running-on-a-mac-mini.md)). Python, SQLite and plain JavaScript, no framework.
- **Passkeys for login.** No passwords to share or reset. Access is set per person, per place, per room and per period, so a guest can get access to one room for a limited time.
- **One connector per system.** Homebridge (on a Raspberry Pi in the house), Eufy for cameras and doorbell (through the Homebridge plugin), tado for heating (cloud), Tuya for plugs and lights (cloud), and a few more. Each connector is a small module with its own tests against a fake version of that system.
- **One app instead of five.** A floor plan where each room glows in the colour of its real lights. Tap a room and its scenes come up: Full, Soft, Dimmed, Off, plus a few extras. To tune a scene, you set the lamps by hand and press "Save current light".

**Why not Home Assistant?** We considered putting Home Assistant underneath with our own front end on top, and chose to build the connectors ourselves. The cost is real: when a vendor changes its API, the fix is ours. In return we control the screens, the access rules and the look.

## What bit us

**Docker on macOS can't reach broadcast or multicast on the LAN.** Waking a TV with Wake-on-LAN and finding devices with mDNS/SSDP don't work from a container. Now the app wakes devices through Homebridge on the Pi, which sits on the LAN itself, and finds devices from known starting addresses plus the system's own topology.

**The cloud API says "success" when the device ignored the command.** A Tuya lamp accepts at most eight steps in a scene. With twelve, the API returned `success: true` and the lamp kept its old scene. Now we read the status back after every scene command and compare.

**A plugin update needed a different Pi.** The Eufy plugin V5 needs Node 24, which does not exist for 32-bit ARM, so the Pi had to move to a 64-bit system. It also has to log in with the country of the main account, and its config needs the new platform block.

**Phones kept the old JavaScript.** Cloudflare caches `.js` and `.css` for hours. Now scripts and styles carry the version number in their URL.

**Camera frames arrived late.** An RTSP stream through ffmpeg gave the first frame after 16 to 19 seconds. The `fps` filter and default buffers were holding frames. Now: no filter, `-fps_mode passthrough`, and low-delay input flags (`-fflags nobuffer -flags low_delay`). First frame in about 2 seconds.

**The screen fought the user.** A background refresh could flip a button back right after a tap. Now an answer older than your last tap is ignored, and refresh waits while you hold a slider. All systems are read in parallel, so one slow cloud no longer holds up the rest.

## Projection shows on a cheap projector

We turned a cheap Android 14 projector (1 GB RAM, 1280×720) into a fixed show machine for projection mapping at Halloween and a ceiling show at Christmas.

- **The show runs on the projector itself,** as our own app, not over HDMI from a laptop. The app carries a tiny local web server, because `fetch()` refuses `file://`. If the Wi-Fi drops, the show keeps going.
- **A WebGL engine with a mask per surface.** In a mapping editor we draw each part of the building on the live projection: handles, points, undo, export to JSON. Soft masks let light run across surfaces without a seam.
- **A calibration tool.** The projector shows Gray-code patterns, a webcam records them, and every camera pixel gets its projector pixel. Surfaces marked in the camera image are converted to the mapping. After the projector moves: scan, map, check.
- **Memory is the limit, not the GPU.** Decoding all sounds at once took about 300 MB. Now audio loads per film, in mono, and the canvas renders at two thirds of the resolution.

Two lessons cost us the most time:

**Auto-start needs the app to own the device.** On Android 14 our boot receiver ran, but the activity never appeared (`BAL_BLOCK` in logcat). A root process from the manufacturer turned its own launcher back on at every boot. What worked: make our app device owner (`dpm set-device-owner <pkg>/.AdminReceiver`, possible only while no accounts are on the device). A device owner may start from the background, sets itself as HOME and pins itself with lock task. To switch between launchers later, hide the other launcher through the device owner instead of stacking preferences. Test both directions and a reboot.

**Wait about two minutes after boot before ADB.** ADB accepted the connection but did not answer the handshake. It looked like a revoked key; it was timing. Now scripts wait until the port is open and then another two minutes. We also set `settings put global adb_allowed_connection_time 0` so the key does not expire after seven days.

## Cleaning up Android TVs

For the TVs we used [tv-home](https://github.com/mihirgupta0900/tv-home) by mihirgupta0900, an open-source project under the MIT licence. You hand Claude Code one prompt and it debloats an Android TV or Google TV over ADB (disabling, never uninstalling), installs a minimal home screen and writes a restore script. Credit for the approach is theirs.

One thing we added: our launcher window has to be explicitly opaque (`windowIsTranslucent`, `windowIsFloating` and `windowShowWallpaper` set to false). The firmware theme marked it translucent, so pressing Home left the app below running and on screen. Check with `dumpsys activity activities`: the home task should be `translucent=false`, the app below `STOPPED`.

## Make this better

If you built something like this, we'd like to hear what bit you and what you do differently. Open an issue or a thread at https://github.com/RichardTheuws/ai-toolkit/discussions.

---

Written with Claude, checked by Richard.
