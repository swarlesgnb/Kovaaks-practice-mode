# KovaaK's Practice Mode

A small Windows companion app for [KovaaK's FPS Aim Trainer](https://kovaaks.com/) that lets
you hide your score / high-score readouts so a session is about the process of improving,
not about chasing a number.

## For users: just want to run it

1. Download `KovaaksPracticeMode.exe` (from `dist\`) — no Python or install needed.
2. **Important:** in KovaaK's, go to **Settings (gear icon) → Video → Display Mode** and set
   it to **Windowed Fullscreen**. See "Why Windowed Fullscreen?" below for why this step
   isn't optional.
3. Launch KovaaK's, then double-click `KovaaksPracticeMode.exe`. A small window opens and a
   "P" icon appears in your system tray.
4. Click **Calibrate Score Regions...** and drag boxes over the score / high score / rank
   areas you want hidden. Press **Enter** to save.
5. Click **Turn Practice Mode ON**. Those areas are now covered whenever KovaaK's is running.
   Toggle it from the window, the tray icon, or the hotkey **Ctrl+Alt+P**.

Closing the window doesn't quit the app — it keeps running in the tray so it stays out of
your way during a session. Right-click the tray icon → **Quit** to actually exit.

## Why Windowed Fullscreen?

Windows gives a true exclusive **Fullscreen** window special "optimized" presentation
handling that suppresses *all* always-on-top overlays over it — not just this one; Discord,
Steam's own overlay, OBS, and FPS counters all hit the identical wall on exclusive
fullscreen. **Windowed Fullscreen** (a.k.a. Borderless) looks pixel-identical and has no
performance cost, but is a normal composited window, so overlays render over it fine. If
cover boxes ever stop appearing, this setting reverting is the most likely cause (e.g.
after a game update).

## How it works

This does **not** modify KovaaK's, read its memory, or touch its files. It runs as a
separate, always-on-top overlay window that sits over the KovaaK's window and follows it
as it moves or resizes. When Practice Mode is on, opaque cover boxes are drawn over the
screen regions you calibrate. The overlay is click-through, so your mouse/keyboard input
goes straight to the game underneath — it's purely visual.

Regions are saved relative to the game window, so they keep working if you move or resize
it. If you change resolution or a scenario's UI places numbers somewhere different, just
recalibrate (it overwrites the saved regions). Settings live at
`%APPDATA%\KovaaksPracticeMode\config.json`.

## For developers: running or building from source

Requires Python 3.10+ on Windows.

```
pip install -r requirements.txt
python main.py
```

To rebuild the standalone `.exe` (outputs to `dist\KovaaksPracticeMode.exe`):

```
powershell -ExecutionPolicy Bypass -File build.ps1
```

That installs `pyinstaller`, regenerates `assets\icon.ico` from the in-app icon design
(`build_icon.py`), and packages via `KovaaksPracticeMode.spec`.

## Notes

- If the global hotkey doesn't respond, try running the app as Administrator — some setups
  need elevated rights for global key hooks to see input while a game has focus.
- The cover boxes are a fixed screen position, not OCR-based — if KovaaK's changes its HUD
  layout, or you play at a very different resolution than you calibrated at, recalibrate.
