# tiktok-follower-printer

Prints the avatar of everyone who follows you or sends you a gift **during a
TikTok LIVE**, on a PD-01 mini thermal printer.

```
TikTokLive ──FollowEvent──▶ avatar URL
           ──GiftEvent────▶     │
                                │
                     download ──▶ square crop, 384 px, gray8
                                │
                  queue + dedupe + rate limit
                                │
                   TiMini-Print CLI ──BLE──▶ PD-01
```

Follows print captioned `@handle`. Gifts add a second line with the gift name
and count, e.g. `Rose x9`. A combo gift prints **once**, when the combo ends --
TikTok emits one event per tick, and printing mid-combo would produce one slip
per rose. Each viewer prints at most once per session *per reason*, so someone
who follows and later sends a gift gets both.

## Hard limits — read these first

- **Only works while you are live.** Follow events arrive on the live room's
  event stream. Anyone who follows you while you are offline produces nothing.
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
| `dedupe` | Print each viewer at most once per session, per reason. |
| `print_gifts` | Set to `false` to print follows only. |
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
| `app/tiktok_listener.py` | TikTokLive connection, follow/gift events, reconnect loop |
| `app/avatar_renderer.py` | download, square crop, scale, caption |
| `app/print_worker.py` | queue, dedupe, rate limit, background thread |
| `app/printer_client.py` | subprocess wrapper around the TiMini-Print CLI |
| `app/app_config.py` | config.ini loading |
| `app/paths.py` | path resolution under PyInstaller |

Third-party components and licences: [THIRD_PARTY.md](THIRD_PARTY.md).
