# Chinese GUI Apps on WSL2

WeChat Linux, DingTalk, and similar Chinese desktop apps are often Electron-based and bundle their own .so libraries in nested subdirectories. They will NOT work out of the box — expect multiple rounds of missing library errors.

## Dependency Resolution Workflow (ldd-first)

**Do NOT install libraries one at a time** — use `ldd` to find ALL missing libraries in one pass, then batch install.

### Step 1: Find all missing libraries

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 bash -c 'ldd /path/to/binary 2>&1 | grep "not found"'
```

This produces a clean list. Libraries fall into two categories:

- **System libraries** (libpulse, libxcb-*, libnss3, libnspr4, libatomic) — install via apt
- **App-bundled libraries** (libandromeda, libmmmojo, libowl, libvoip*) — these live in the app's own directories

### Step 2: Discover app-bundled .so directories

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 bash -c 'find /opt/<app> -name "*.so" -type f 2>/dev/null | xargs -r dirname | sort -u'
```

### Step 3: Install system libraries in one batch

```bash
apt-get install -y <list of packages>
```

### Step 4: Resolve bundled library loading

**CRITICAL: If the app has subprocesses that bundle their OWN versions of the same .so files (e.g., WeChat's RadiumWMPF/WeChatAppEx mini-program runtime ships its own `libowl.so`), do NOT include subprocess library directories in `LD_LIBRARY_PATH`.** The parent's path will leak into the subprocess, causing it to load the wrong `libowl.so` version and crash with `symbol lookup error: undefined symbol`.

**Preferred approach — ldconfig (system-wide, no subprocess pollution):**

```bash
# Add the app's main .so directory to the system library path
echo "/opt/<app>" > /etc/ld.so.conf.d/<app>.conf
ldconfig

# Launch wrapper with NO LD_LIBRARY_PATH:
#!/bin/bash
unset LD_LIBRARY_PATH
exec <app> "$@"
```

This way the main binary finds its libs via ldconfig, and subprocesses use their own RPATH without interference.

**Fallback — minimal LD_LIBRARY_PATH:**

Only include the main app directory, NOT subprocess directories:

```bash
#!/bin/bash
export LD_LIBRARY_PATH="/opt/<app>:$LD_LIBRARY_PATH"
exec <app> "$@"
```

## Chinese Input Method Setup

### Recommended: fcitx5 with wayland modules removed

fcitx5 crashes in WSLg because Weston denies `zwp_input_method_v1`. **Fix: remove its wayland modules** so it runs purely on X11 — candidate window is visible via classicui.

```bash
# Install
apt-get install -y fcitx5 fcitx5-chinese-addons fcitx5-frontend-gtk3 fcitx5-frontend-gtk2 fcitx5-frontend-qt5 fonts-noto-cjk

# Remove wayland modules
mv /usr/lib/x86_64-linux-gnu/fcitx5/libwayland.so /usr/lib/x86_64-linux-gnu/fcitx5/libwayland.so.bak
mv /usr/lib/x86_64-linux-gnu/fcitx5/libwaylandim.so /usr/lib/x86_64-linux-gnu/fcitx5/libwaylandim.so.bak
mv /usr/share/fcitx5/addon/wayland.conf /usr/share/fcitx5/addon/wayland.conf.bak
mv /usr/share/fcitx5/addon/waylandim.conf /usr/share/fcitx5/addon/waylandim.conf.bak

# Configure Pinyin as default
mkdir -p ~/.config/fcitx5
cat > ~/.config/fcitx5/profile << 'EOF'
[Groups/0]
Name=Default
Default Layout=us
DefaultIM=pinyin

[Groups/0/Items/0]
Name=keyboard-us
Layout=

[Groups/0/Items/1]
Name=pinyin
Layout=

[GroupOrder]
0=Default
EOF

# Start
fcitx5 -d
```

Launch wrapper additions:
```bash
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx
```

Toggle: `Ctrl+Space`. Candidate window is visible on X11.

### Better candidate quality: fcitx5-rime (Rime)

The default fcitx5-chinese-addons pinyin has mediocre candidate quality. Rime (中州韻) is an open-source alternative with superior suggestions — single package, zero config:

```bash
apt-get install -y fcitx5-rime

# Update ~/.config/fcitx5/profile:
# DefaultIM=rime
# [Groups/0/Items/1]
# Name=rime
```

Default scheme is luna_pinyin. Additional shortcuts: `Ctrl+'` (switch scheme), `F4` (toggle simplified/traditional).

### Fallback: ibus (candidate window invisible)

IBus in XIM mode works but its candidate panel is invisible/offscreen in WSLg. You can type pinyin and commit characters but can't see which candidate you're selecting.

```bash
apt-get install -y ibus ibus-pinyin ibus-gtk3 ibus-gtk
ibus-daemon -drx
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'pinyin']"
ibus engine pinyin
```

## WeChat Linux (wechat)

### Known system library dependencies

| Library | Package (Ubuntu 24.04) | Notes |
|---------|------------------------|-------|
| libatomic.so.1 | libatomic1 | |
| libpulse.so.0 | libpulse0 | |
| libpulse-simple.so.0 | libpulse0 | |
| libasound.so.2 | **libasound2t64** | Renamed in 24.04. Needed by WeChatAppEx. |
| libxkbcommon-x11.so.0 | libxkbcommon-x11-0 | |
| libxcb-icccm.so.4 | libxcb-icccm4 | |
| libxcb-image.so.0 | libxcb-image0 | |
| libxcb-shape.so.0 | libxcb-shape0 | |
| libxcb-xkb.so.1 | libxcb-xkb1 | |
| libxcb-render-util.so.0 | libxcb-render-util0 | |
| libxcb-keysyms.so.1 | libxcb-keysyms1 | |
| libnss3.so | libnss3 | |
| libnspr4.so | libnspr4 | |
| libgl / libEGL (Mesa) | libgl1-mesa-dri libglx-mesa0 libegl-mesa0 | See GPU section |

One-liner to install all:
```bash
apt-get install -y libatomic1 libpulse0 libasound2t64 libxkbcommon-x11-0 libxcb-icccm4 libxcb-image0 libxcb-shape0 libxcb-xkb1 libxcb-render-util0 libxcb-keysyms1 libnss3 libnspr4 libgl1-mesa-dri libglx-mesa0 libegl-mesa0
```

### Bundled library paths (reference)

```
/opt/wechat
/opt/wechat/RadiumWMPF/host
/opt/wechat/RadiumWMPF/runtime
/opt/wechat/RadiumWMPF/runtime/xfile
/opt/wechat/XEditor
/opt/wechat/XFile
```

### Working launch wrapper (~/wechat.sh) — ldconfig approach

Step 1: Register /opt/wechat with ldconfig (one-time):
```bash
echo "/opt/wechat" > /etc/ld.so.conf.d/wechat.conf && ldconfig
```

Step 2: Launch wrapper:
```bash
#!/bin/bash
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
unset LD_LIBRARY_PATH

# Start fcitx5 if not running
if ! pgrep -x fcitx5 > /dev/null; then
    fcitx5 -d 2>/dev/null
    sleep 1
fi
export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx

exec wechat --disable-gpu "$@"
```

The `--disable-gpu` flag is critical when WSLg GPU passthrough is broken — without it, Electron apps may silently hang or show only a tray icon with no window.

Launch from Windows:
```bash
wsl -d Ubuntu-24.04 -- bash ~/wechat.sh
```

### WeChat-specific quirks

- **No right-click context menu** for copy/paste — use `Ctrl+C` / `Ctrl+V` exclusively. WSLg auto-syncs clipboard text with Windows, but does NOT support file clipboard transfer.
- **File transfer**: Create symlinks in WSL home so the file picker shows Windows folders:
  ```bash
  ln -sf /mnt/c/Users/<user>/Desktop   ~/Desktop
  ln -sf /mnt/c/Users/<user>/Downloads ~/Downloads
  ln -sf /mnt/c/Users/<user>/Documents ~/Documents
  ```
  For receiving files, change WeChat's save path to `/mnt/c/Users/<user>/Downloads/WeChat/` (or the symlink target of `~/Downloads`). Received files then appear directly in Windows without manual copying.
- **`update-desktop-database: not found`** during install is harmless.
- **fcitx5-remote crash**: `fcitx5-remote -s rime` may fail with DBus error in WSLg. Ignorable — fcitx5 reads the profile file at startup, so restarting picks up the correct IM.
- **`--disable-gpu` + `--disable-software-rasterizer` together**: causes instant crash (exit code 255) for Electron apps. Use ONLY `--disable-gpu` — the MESA env vars (`LIBGL_ALWAYS_SOFTWARE=1`, `MESA_LOADER_DRIVER_OVERRIDE=llvmpipe`) handle software rasterization.

### Keyboard shortcut to launch WSL app from Windows

To create a global `Ctrl+Alt+W` hotkey for launching a WSL GUI app:

**Step 1**: Create a VBS wrapper that launches the app silently:
```vbscript
' C:\Users\<user>\bin\<app>_hotkey.vbs
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "C:\Windows\System32\wsl.exe -d Ubuntu-24.04 -- bash /home/<user>/<app>.sh", 0, False
```

**Step 2**: Create a Windows shortcut (.lnk) with the hotkey using PowerShell:
```powershell
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\<App>.lnk")
$sc.TargetPath = "wscript.exe"
$sc.Arguments = "$env:USERPROFILE\bin\<app>_hotkey.vbs"
$sc.Hotkey = "Ctrl+Alt+W"
$sc.Save()
```

Run the .ps1 from cmd (not git-bash, which chokes on backtick escaping):
```cmd
powershell.exe -ExecutionPolicy Bypass -File C:\Users\<user>\make_shortcut.ps1
```

**Note**: Windows shortcut hotkeys are case-sensitive and only work for shortcuts on the Desktop. The shortcut link may need to be right-clicked once before Windows "registers" the hotkey.

## GPU / WSLg Rendering

When GPU passthrough (vGPU / D3D12) is not working in WSL2, Electron-based GUI apps may fail to create an OpenGL context. Symptoms:

```
MESA: error: ZINK: failed to choose pdev
glx: failed to create drisw screen
```

### Diagnosis

```bash
ls /dev/dri/              # Empty = no GPU passthrough
glxinfo -B 2>&1 | head -5 # (requires mesa-utils)
```

### Fix: Force software rendering

1. Install Mesa with llvmpipe (CPU) driver:
   ```bash
   apt-get install -y libgl1-mesa-dri libglx-mesa0 libegl-mesa0 mesa-utils
   ```

2. Launch wrapper env vars:
   ```bash
   export LIBGL_ALWAYS_SOFTWARE=1
   export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe
   ```
   Plus `--disable-gpu` flag for Electron apps (critical — without it, app may still try GPU).

### Invisible window diagnosis (xdotool)

If the process stays alive but no window appears on the Windows desktop:

```bash
apt-get install -y xdotool
xdotool search --name "" 2>&1
xdotool getactivewindow getwindowname
```

If `xdotool` finds a window (e.g., "Weixin") but you can't see it, it's a WSLg compositing issue.
