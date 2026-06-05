# Dasung Paperlike 253 – Linux Driver

An unofficial Linux driver for the **Dasung Paperlike 253** E-Ink monitor.

The official Paperlike client app only runs on Windows and macOS. This project
reverse-engineers the USB protocol and provides a Python script that works on
any Linux distribution.

---

## How it works

The Dasung Paperlike 253 uses two connections simultaneously:

- **HDMI** – carries the video signal
- **USB** – controls the monitor (init, keepalive, settings)

The USB connection uses a **QinHeng CH340 USB-to-Serial converter** (vendor
`1a86`, product `7523`) built into the monitor. Linux recognizes this chip
automatically via the `ch341` kernel module – no manual driver installation
needed.

The monitor communicates via **ASCII strings** over serial at **115200 baud**.
Every command follows this format:

```
5FF5 [8 bytes as 16 hex chars] A0FA
```

### Protocol details

| Direction | Command | Meaning |
|-----------|---------|---------|
| Host → Monitor | `5FF50A10000000000000A0FA` | Query firmware version |
| Host → Monitor | `5FF50A01000000000000A0FA` | Query contrast level |
| Host → Monitor | `5FF50A02000000000000A0FA` | Query display mode |
| Monitor → Host | `5FF5F520000000000000A0FA` | Monitor ready signal (sent spontaneously) |
| Host → Monitor | `5FF52001000000000000A0FA` | **Display ON / Keepalive** |

**Important:** The monitor turns off the image after ~5 seconds unless it
receives `5FF52001000000000000A0FA` at least every 4–5 seconds. This keepalive
must run continuously as long as the monitor is in use.

---

## Requirements

### Hardware
- Dasung Paperlike 253
- HDMI cable (for video signal)
- USB-B cable (for control)

### Software
- Linux kernel with `ch341` module (included in all major distros)
- Python 3.6+
- [pyserial](https://pypi.org/project/pyserial/)

### Install pyserial

**Ubuntu / Debian / Linux Mint:**
```bash
sudo apt install python3-serial
# or
pip install pyserial
```

**Arch Linux / Manjaro:**
```bash
sudo pacman -S python-pyserial
```

**Fedora / RHEL:**
```bash
sudo dnf install python3-pyserial
```

**NixOS:**
```nix
environment.systemPackages = [
  (python3.withPackages (ps: [ ps.pyserial ]))
];
```

Or ad-hoc:
```bash
nix-shell -p python3Packages.pyserial
```

---

## Setup

### 1. Fix the brltty conflict

On most Linux distributions, `brltty` (a Braille screen reader daemon)
automatically claims the CH340 chip and immediately disconnects it, preventing
`/dev/ttyUSB0` from appearing.

**Ubuntu / Debian / Linux Mint (one-time fix):**
```bash
sudo rm /usr/lib/udev/rules.d/85-brltty.rules
# reconnect USB cable after this
```

**systemd-based distros:**
```bash
sudo systemctl stop brltty
sudo systemctl disable brltty
```

**NixOS:**
```nix
services.brltty.enable = false;
```

### 2. Serial port permissions

Your user needs access to `/dev/ttyUSB0`.

**Add user to dialout group (permanent):**
```bash
sudo usermod -a -G dialout $USER
# log out and back in for this to take effect
```

**Quick fix (current session only):**
```bash
sudo chmod 666 /dev/ttyUSB0
```

**NixOS:**
```nix
users.users.youruser.extraGroups = [ "dialout" ];
```

### 3. Verify the device appears

Connect both HDMI and USB cables, then:
```bash
ls /dev/ttyUSB*
# should show /dev/ttyUSB0
```

If nothing appears, check:
```bash
dmesg | grep -i ch34
```

---

## Usage

```bash
python3 dasung.py
```

Optional arguments:
```bash
python3 dasung.py /dev/ttyUSB0   # specify port (default: /dev/ttyUSB0)
python3 dasung.py /dev/ttyUSB0 115200   # port + baud rate
python3 dasung.py /dev/ttyUSB0 115200 15   # port + baud + ready timeout (seconds)
```

The script will:
1. Open the serial connection
2. Toggle RTS (required for CH340 init)
3. Query current monitor registers
4. Wait for the monitor's ready signal
5. Send Display ON command
6. **Keep running** and send keepalive every 4 seconds

**Keep this script running** as long as you use the monitor. Press `Ctrl+C` to exit.

### xrandr

After running the script, tell your compositor about the monitor:

```bash
# show as second display to the right
xrandr --output HDMI-1 --auto --right-of eDP-1

# portrait mode (rotated)
xrandr --output HDMI-1 --auto --rotate left --left-of eDP-1
```

Replace `HDMI-1` with your actual output name from `xrandr | grep connected`.

---

## Troubleshooting

**`/dev/ttyUSB0` does not appear:**
- Check `dmesg | grep brltty` – if brltty is mentioned, follow the fix above
- Try unplugging and replugging the USB cable

**Permission denied on `/dev/ttyUSB0`:**
- Add yourself to the `dialout` group (see setup above)
- Or run with `sudo` as a temporary workaround

**Monitor shows "No Signal – run the Paperlike client":**
- Make sure HDMI is connected before running the script
- The monitor sends a ready signal when it detects the HDMI signal
- Try increasing the timeout: `python3 dasung.py /dev/ttyUSB0 115200 30`

**Image disappears after a few seconds:**
- The keepalive loop stopped – make sure the script is still running
- Do not close the terminal window running `dasung.py`

---

## Running in the background

To run the keepalive in the background while using the monitor normally:

```bash
python3 dasung.py > /tmp/dasung.log 2>&1 &
echo "Dasung keepalive PID: $!"
```

To stop it later:
```bash
kill $(pgrep -f dasung.py)
```

---

## Protocol: reverse engineering notes

The protocol was discovered by capturing USB traffic with Wireshark (USBPcap
on Windows) while the official Paperlike client was running.

Key findings:

- Commands are plain ASCII strings, not binary
- Magic header `5FF5`, magic trailer `A0FA`
- The monitor spontaneously sends `5FF5F520000000000000A0FA` when it detects
  an HDMI signal and is ready to display
- The host must reply with `5FF52001000000000000A0FA` to activate the image
- This same command must be repeated every ~4 seconds as a keepalive
- The CH340 is configured at **115200 baud**, 8N1

---

## Tested on

| Distribution | Status |
|---|---|
| Linux Mint 22 | ✅ Working |
| NixOS 24.11 | ✅ Working |

Contributions with results on other distributions are welcome!

---

## Contributing

If you have a Dasung Paperlike 253 and get it working on your distribution,
please open a PR or issue with your setup notes.

Especially useful:
- Mode switching commands (Text / Photo / Video / Auto)
- Contrast level commands
- Screen refresh / ghost clearing commands

These are likely in the same `5FF5...A0FA` format but the register values
are not yet fully documented.

---

## Author

**Denis Sandmann**
- Website: [denissandmann.de](https://denissandmann.de)

---

## License

MIT
