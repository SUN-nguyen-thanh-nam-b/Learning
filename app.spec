# PyInstaller spec.  Build with:  pyinstaller --noconfirm app.spec
#
# TikTokLive's protobuf messages live in TikTokLiveProto and are resolved by
# name at runtime, so PyInstaller's static analysis cannot see them. The same
# goes for the generated Euler Stream SDK. Both are collected wholesale.

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

_RUNTIME_PACKAGES = (
    "TikTokLive",
    "TikTokLiveProto",
    "EulerApiSdk",
    "betterproto2",
)

hiddenimports = []
datas = collect_data_files("certifi")
for package in _RUNTIME_PACKAGES:
    hiddenimports += collect_submodules(package)
    datas += collect_data_files(package)

a = Analysis(
    ["run_app.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="tiktok-follower-printer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
)
