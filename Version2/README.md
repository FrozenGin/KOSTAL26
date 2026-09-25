# Version 2

Version 2 contains the state-based PiCar controller described in
`../docs/version2-plan.md`.

## Configure The Target Level

Edit `config.py` before starting a run:

```python
TARGET_LEVEL = "level1"
ACCEPTED_LEVELS = ("level1", "level2")
```

Accepted values are `level1` and `level2`. A black line followed directly by a normal
line starts the QR scan. The goal pattern is `BLACK -> WHITE -> BLACK -> WHITE -> BLACK -> WHITE`. A QR code may
contain either one line:
`left` or `right`, or two lines containing a level followed by a direction.
Set `accepted_levels` in `Config` to control which level routes are accepted. The
direction from every accepted QR code controls the maneuver.

Line correction is percentage-based: the center sensor is `0%` offset and the
outermost sensors are `100%` offset. `max_correction_percent` limits the maximum
motor-speed difference.

All driving speeds are easy to adjust at the top of `config.py`:

```python
SPEED_FOLLOW_LINE = 0.12
SPEED_START_EXIT = 0.17
SPEED_QR_MARKER = 0.12
SPEED_MANEUVER_FORWARD = 0.07
SPEED_MANEUVER_TURN = 0.12
SPEED_RECOVERY = 0.10
SPEED_GOAL_EXIT = 0.12
```

After a QR command, the maneuver drives a forward arc in the requested direction
until the marker is left. The `FIND_TARGET_LINE` state then searches for the requested
left or right line and returns to `FOLLOW_LINE` only after the line is centered and
stable.

## Run

Run the hardware entry point from the repository root:

```bash
python3 -m Version2
```

The local `start.sh` connects over SSH and starts `main.py` on the robot:

```bash
./start.sh
```

The camera decoder in `app.py` is a platform integration point. Replace the placeholder
decoder with the OpenCV/Picamera2 decoder used on the Raspberry Pi.

## Deploy Over SSH

Create `deploy.conf` from `deploy.conf.example` and set the robot's SSH target and
password. `sshpass` is used so deployment and start do not prompt for SSH login:

```bash
cp deploy.conf.example deploy.conf
./deploy.sh
```

Install `sshpass` on the PC first if needed:

```bash
sudo apt install sshpass
```

The password is stored in plaintext in the local, git-ignored `deploy.conf`.

The V2 runtime files are copied flat into `~/hackathon` with no subfolders,
then `main.py` is started through the SSH session. Output is shown live and saved
locally under `logs/`. The process stays attached to the SSH session so its output can
be captured reliably.

Set `WIFI_CHANGE=true` in `deploy.conf` to change the **local PC's** Wi-Fi with
`nmcli` before connecting to the robot. The script does not restore the previous
network automatically; switch the PC back manually after the run.

## Test Without Hardware

```bash
python3 -m unittest discover -s tests
python3 -m compileall Version2
```
