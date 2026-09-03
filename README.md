# tiktok-follower-printer

Prints the avatar of everyone who sends you a gift **during a TikTok LIVE**,
on a PD-01 mini thermal printer.

```
TikTokLive ──GiftEvent──▶ avatar URL
                             │
                  download ──▶ square crop, 384 px, greyscale
                             │
               queue + dedupe + rate limit + retry
                             │
                TiMini-Print CLI ──BLE──▶ PD-01
```

Each slip carries the avatar, the `@handle`, and the gift name and count, e.g.
`Rose x9`. A combo gift prints **once**, when the combo ends -- TikTok emits one
event per tick, and printing mid-combo would produce one slip per rose. Every
separate gift prints, including repeat gifts from the same person.

## Hard limits — read these first

- **Only works while you are live.** Gift events arrive on the live room's
  event stream. Nothing reaches the app while you are offline.
- **Wake the printer before you start.** It sleeps after a few idle minutes and
  stops advertising over BLE, which makes discovery fail.
- **TikTokLive is unofficial.** It reverse-engineers TikTok's webcast protocol
  and can break without warning.
- **BLE holds one connection.** Disconnect the printer from your phone and
  from the FunPrint app before starting this, or it will not connect.
- **Windows 10 1709+** is required — `bleak` reaches Bluetooth through WinRT.

## Setup (Windows)

1. Download the build artifact and unzip it. It contains:
   - `tiktok-follower-printer.exe`
   - `TiMini-Print-Command-Line-Windows-x86_64.exe`
   - `config.ini`
2. Turn the printer on and make sure nothing else is connected to it.
3. Find the printer's Bluetooth name:
   ```
   tiktok-follower-printer.exe --scan
   ```
4. Edit `config.ini` — set `[tiktok] username` and `[printer] bluetooth_name`.
5. Verify the printer before going live:
   ```
   tiktok-follower-printer.exe --test-print some-photo.jpg
   ```
6. Start your TikTok LIVE, then run:
   ```
   tiktok-follower-printer.exe
   ```

## Configuration

See `config.example.ini` — every key is commented. The settings worth tuning:

| Key | Why it matters |
|---|---|
| `max_per_minute` | Hard cap on prints. Protects paper and the print head during a viral moment. |
| `queue_max` | Jobs past this are dropped rather than backing up. |
| `avatar_scale` | How much of the 48 mm paper width the avatar fills, `0.2`-`1.0`. Lower prints smaller and shortens each slip. |
| `dedupe` | Suppress the same gift event arriving twice. Does **not** limit a person to one slip. |
| `retries` | Extra attempts when a print fails. The printer sleeps after a few idle minutes; gift events never repeat. |
| `darkness` | Passed to the TiMini-Print CLI. Raise it if prints look faint. |
| `sign_api_key` | Euler Stream key. Only needed if the free tier rate-limits you. |

## Building the .exe

PyInstaller cannot cross-compile, so the Windows executable is built by
GitHub Actions on a `windows-latest` runner.

```bash
git remote add origin git@github.com:<you>/tiktok-follower-printer.git
git push -u origin main
```

The `build-windows` workflow runs on every push to `main`/`master` and can be
triggered by hand from the Actions tab. Download the
`tiktok-follower-printer-windows` artifact when it finishes.

To build locally **on a Windows machine** instead:

```
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm app.spec
```

## Running from source

```bash
pip install -r requirements.txt
cp config.example.ini config.ini   # then edit it
python run_app.py
```

## Layout

| File | Role |
|---|---|
| `app/main.py` | CLI parsing and wiring |
| `app/tiktok_listener.py` | TikTokLive connection, gift events, reconnect loop |
| `app/avatar_renderer.py` | download, square crop, scale, caption |
| `app/print_worker.py` | queue, dedupe, rate limit, background thread |
| `app/printer_client.py` | subprocess wrapper around the TiMini-Print CLI |
| `app/app_config.py` | config.ini loading |
| `app/paths.py` | path resolution under PyInstaller |

Third-party components and licences: [THIRD_PARTY.md](THIRD_PARTY.md).
