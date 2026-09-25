# Version 2

Version 2 contains the state-based PiCar controller described in
`../docs/version2-plan.md`.

## Configure The Target Level

Edit `config.py` before starting a run:

```python
TARGET_LEVEL = "level1"
```

Accepted values are `level1` and `level2`. A QR code may contain either one line:
`left` or `right`, or two lines containing a level followed by a direction.

## Run

Run the hardware entry point from the repository root:

```bash
python3 -m Version2
```

The camera decoder in `app.py` is a platform integration point. Replace the placeholder
decoder with the OpenCV/Picamera2 decoder used on the Raspberry Pi.

## Test Without Hardware

```bash
python3 -m unittest discover -s tests
python3 -m compileall Version2
```
