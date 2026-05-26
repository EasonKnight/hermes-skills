---
name: windows-wsl-setup
description: Install, configure, and troubleshoot WSL2 on Windows — distro import, Chinese mirrors, GUI app launch, MSYS path quirks.
category: devops
triggers:
  - User asks to install WSL, set up a Linux distro, or run Linux GUI apps on Windows
  - User mentions WSL, wsl --install, wsl --import, wsl.conf
  - User wants to run a .deb/.AppImage on Windows
  - WSL commands produce garbled output in git-bash
  - User mentions Chinese mirrors / 中国源 for WSL downloads
---

# Windows WSL2 Setup

Install and configure WSL2 on Windows, with Chinese mirror support for mainland China networks where GitHub/Ubuntu archive are slow or blocked.

## Quick Overview

1. Enable WSL + Virtual Machine Platform features (requires reboot)
2. Install a distro — prefer `wsl --import` from rootfs.tar.gz when Microsoft Store / GitHub are blocked
3. Create a non-root user, configure sudo, set default user
4. Launch GUI apps via WSLg

## Pitfalls

### MSYS Path Conversion (git-bash)

When running `wsl` from git-bash/MSYS, POSIX-looking paths like `/bin/bash`, `/etc/wsl.conf`, `/mnt/...` get auto-converted to Windows paths. This breaks `wsl --import` and any command with path arguments.

**Fix**: Always prefix with `MSYS_NO_PATHCONV=1`:

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root useradd -m -G sudo -s /bin/bash mayn
MSYS_NO_PATHCONV=1 wsl --import Ubuntu-24.04 "C:\Users\Mayn\wsl\Ubuntu-24.04" "C:\Users\Mayn\ubuntu-wsl.tar.gz"
```

### Garbled wsl output in git-bash

`wsl.exe` outputs UTF-16-LE. git-bash/MSYS terminals often display this as gibberish. Use Python `subprocess` with `utf-16-le` decoding for reliable output:

```python
import subprocess
r = subprocess.run(["wsl", "--list", "--verbose"], capture_output=True)
stdout = r.stdout.decode('utf-16-le', errors='replace')
```

### Network blocks in China

- `wsl --install -d Ubuntu-24.04` fetches `raw.githubusercontent.com` → blocked in China → `WININET_E_TIMEOUT`
- `cloud-images.ubuntu.com` direct .tar.gz downloads may also be slow/blocked

**Workaround**: Download rootfs from Chinese mirrors, then `wsl --import`.

## Installing WSL on a Fresh Machine

### Step 1: Enable WSL features

Requires administrator. Create a `.ps1` script and run with `Start-Process -Verb RunAs`:

```powershell
# install_wsl.ps1
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
wsl --set-default-version 2
```

**Must reboot** after enabling features.

### Step 2: Install a distro

If `wsl --install -d Ubuntu-24.04` works (network OK), use it directly. Otherwise, manual import:

1. Download rootfs from a Chinese mirror (see references/mirrors.md for URLs)
2. Import:

```bash
wsl --import Ubuntu-24.04 "C:\Users\<user>\wsl\Ubuntu-24.04" "C:\Users\<user>\ubuntu-wsl.tar.gz"
```

### Step 3: Create user and configure

```bash
# Create user
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root useradd -m -G sudo -s /bin/bash <username>

# Passwordless sudo
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash -c \
  'echo "<username> ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/<username> && chmod 440 /etc/sudoers.d/<username>'

# Set default user
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash -c \
  'echo "[user]" > /etc/wsl.conf && echo "default=<username>" >> /etc/wsl.conf'
```

Shutdown and restart for wsl.conf to take effect:
```bash
wsl --shutdown
```

### Step 4: Configure APT mirrors (China)

For Ubuntu 24.04 (DEB822 format), edit `/etc/apt/sources.list.d/ubuntu.sources`:

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash -c \
  'sed -i "s|http://archive.ubuntu.com|https://mirrors.ustc.edu.cn|g" /etc/apt/sources.list.d/ubuntu.sources && \
   sed -i "s|http://security.ubuntu.com|https://mirrors.ustc.edu.cn|g" /etc/apt/sources.list.d/ubuntu.sources && \
   apt-get update'
```

### Step 5: Install .deb packages

Files under `/mnt/c/` are accessible in WSL:

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -u root bash -c \
  'dpkg -i /mnt/c/Users/<user>/Downloads/package.deb; apt-get install -f -y'
```

**After dpkg, use `ldd` to find ALL missing libraries at once** — don't iterate one error at a time:

```bash
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 bash -c 'ldd /usr/bin/<binary> 2>&1 | grep "not found"'
```

This splits into two categories:
- **System libs** (libpulse, libxcb-*, libnss3, etc.) → `apt-get install -y <packages>`
- **App-bundled libs** (in /opt/<app>/...) → register with `ldconfig` (preferred) or add only the main app directory to `LD_LIBRARY_PATH` — do NOT include subprocess directories (see Step 6)

For Chinese Electron-based GUI apps (WeChat, DingTalk, etc.) see `references/chinese-gui-apps.md` for known dependency lists.

### Step 6: Launch GUI app

WSLg handles display automatically. For apps that bundle their own .so libraries, **prefer `ldconfig` over `LD_LIBRARY_PATH`** to avoid subprocess library conflicts:

```bash
# One-time: register app libs with system linker
echo "/opt/<app>" > /etc/ld.so.conf.d/<app>.conf && ldconfig
```

Then create a wrapper script WITHOUT `LD_LIBRARY_PATH`:

```bash
#!/bin/bash
export LIBGL_ALWAYS_SOFTWARE=1          # Force software rendering if GPU passthrough fails
unset LD_LIBRARY_PATH                   # Let subprocesses use their own RPATH
exec <command> --disable-gpu "$@"       # --disable-gpu critical for Electron apps
```

```bash
wsl -d Ubuntu-24.04 -- bash ~/wrapper.sh
```

If `ldconfig` isn't an option, use a **minimal** LD_LIBRARY_PATH with only the main app directory (not subprocess directories — they'll use their own RPATH). See `references/chinese-gui-apps.md` for the full dependency resolution workflow.

## Chinese Input Method (fcitx5 vs ibus)

WSLg's Weston compositor blocks Wayland input method protocol. Both `fcitx5` and `ibus` have issues — choose based on what matters most.

### Option A: fcitx5 (recommended — visible candidate window)

fcitx5 crashes at startup because WSLg denies `zwp_input_method_v1`. **Fix: remove the wayland modules so fcitx5 runs on X11 only.**

```bash
# Install
apt-get install -y fcitx5 fcitx5-chinese-addons fcitx5-frontend-gtk3 fcitx5-frontend-gtk2 fcitx5-frontend-qt5 fonts-noto-cjk

# Remove wayland modules (causes crash in WSLg)
mv /usr/lib/x86_64-linux-gnu/fcitx5/libwayland.so /usr/lib/x86_64-linux-gnu/fcitx5/libwayland.so.bak
mv /usr/lib/x86_64-linux-gnu/fcitx5/libwaylandim.so /usr/lib/x86_64-linux-gnu/fcitx5/libwaylandim.so.bak
mv /usr/share/fcitx5/addon/wayland.conf /usr/share/fcitx5/addon/wayland.conf.bak
mv /usr/share/fcitx5/addon/waylandim.conf /usr/share/fcitx5/addon/waylandim.conf.bak

# Configure Pinyin as default input method
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

**CRITICAL: Do NOT restart fcitx5 inside the same shell session as `exec wechat`.** Putting `pkill fcitx5; fcitx5 -d; exec wechat` in one script causes wechat to hang/timeout (exit 124) — likely a race between fcitx5's X11 reconnection and wechat's display init.

**Correct approach: fcitx5 as a persistent daemon.** Start it once and leave it running. The wrapper script only checks + sets env vars:

```bash
# In wechat.sh — do NOT pkill/restart fcitx5 here:
#!/bin/bash
export LIBGL_ALWAYS_SOFTWARE=1
unset LD_LIBRARY_PATH

# Check-only: start fcitx5 if missing, but don't restart
pgrep -x fcitx5 >/dev/null || { DISPLAY=:0 fcitx5 -d 2>/dev/null; sleep 1; }

export GTK_IM_MODULE=fcitx
export QT_IM_MODULE=fcitx
export XMODIFIERS=@im=fcitx

exec wechat --disable-gpu "$@"
```

If fcitx5 gets stuck (can't switch to Chinese after a fresh WSL boot), kill and restart it **as a separate command** before launching the app:

```bash
# Separate commands, not in the app wrapper:
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- pkill -9 fcitx5 2>/dev/null
MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash -c 'DISPLAY=:0 fcitx5 -d 2>/dev/null; sleep 2'
# Then launch the app
```

Candidate window appears on X11 via classicui — fully visible in WSLg. Toggle with `Ctrl+Space`.

### Option B: fcitx5-rime (best candidate quality)

Rime (中州韻) is an open-source input method engine with much better candidate quality than fcitx5-chinese-addons' built-in pinyin. It works with the same fcitx5 framework (wayland modules already removed). Install is a single package:

```bash
apt-get install -y fcitx5-rime

# Set rime as default IM in ~/.config/fcitx5/profile:
[Groups/0/Items/1]
Name=rime
Layout=
```

No additional configuration needed — the default 朙月拼音 (luna_pinyin) scheme works immediately. Toggle with `Ctrl+Space`. Additional shortcuts:
- `Ctrl+`` — switch input scheme
- `F4` — toggle simplified/traditional

### Option C: ibus (fallback — invisible candidate window)

IBus in XIM mode (`-drx`) works but the **candidate window is invisible/offscreen** in WSLg. Input still works (you can type pinyin and commit characters) but you cannot see which candidate you're selecting.

```bash
apt-get install -y ibus ibus-pinyin ibus-gtk3 ibus-gtk
ibus-daemon -drx
gsettings set org.freedesktop.ibus.general preload-engines "['xkb:us::eng', 'pinyin']"
ibus engine pinyin
```

Use ibus only if fcitx5 wayland removal fails or you don't need visible candidate words.

## WSL ↔ Windows File Sharing

GUI apps in WSL have their own file picker that defaults to the Linux filesystem. To make Windows files easily accessible, create symlinks in the WSL home directory:

```bash
ln -sf /mnt/c/Users/<user>/Desktop   ~/Desktop
ln -sf /mnt/c/Users/<user>/Downloads ~/Downloads
ln -sf /mnt/c/Users/<user>/Documents ~/Documents
```

Now the app's file dialog (Home → Desktop/Downloads/Documents) maps directly to Windows folders.

For **receiving** files, change the app's save path to a `/mnt/c/` location so files land in Windows.

## Clipboard

WSLg automatically syncs the text clipboard between Windows and Linux. **Ctrl+C / Ctrl+V** work bidirectionally.

Limitations:
- File clipboard transfer is NOT supported — cannot copy a file in Windows Explorer and paste into WSLg app (or vice versa). Use the file picker instead.
- Chinese GUI apps often lack right-click context menus — rely on keyboard shortcuts exclusively.

## Global Hotkey for WSL GUI Apps

To launch a WSL GUI app with a global shortcut like `Ctrl+Alt+W`:

1. Create a VBS wrapper (silent launch, no console flash):
   ```vbscript
   ' C:\Users\<user>\bin\<app>_hotkey.vbs
   Set WshShell = CreateObject("WScript.Shell")
   WshShell.Run "C:\Windows\System32\wsl.exe -d Ubuntu-24.04 -- bash /home/<user>/<app>.sh", 0, False
   ```

2. Create a .lnk shortcut with the hotkey. **Must run PowerShell from cmd, not git-bash** (git-bash backtick escaping breaks PowerShell inline commands):
   ```powershell
   # make_shortcut.ps1 — run via: cmd /c powershell -File C:\Users\<user>\make_shortcut.ps1
   $ws = New-Object -ComObject WScript.Shell
   $sc = $ws.CreateShortcut("$env:USERPROFILE\Desktop\<App>.lnk")
   $sc.TargetPath = "wscript.exe"
   $sc.Arguments = "$env:USERPROFILE\bin\<app>_hotkey.vbs"
   $sc.Hotkey = "Ctrl+Alt+W"
   $sc.Save()
   ```

   Then: `cmd //c "powershell -ExecutionPolicy Bypass -File C:\Users\<user>\make_shortcut.ps1"`

3. Also create a `wechat.cmd` in a PATH directory (e.g. `C:\Users\<user>\bin\`) for direct terminal use:
   ```bat
   @echo off
   C:\Windows\System32\wsl.exe -d Ubuntu-24.04 -- bash /home/<user>/<app>.sh
   ```

Limitations: Windows shortcut hotkeys need a right-click first to "register". Re-running while app is open activates the existing window.

## Verification

```bash
wsl --list --verbose    # Should show distro with STATE=Stopped/Running, VERSION=2
wsl --status            # Should show "默认版本: 2" with no errors about virtualization
wsl --version           # Shows WSLg version (needed for GUI)
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "WSL2 无法启动，此计算机上未启用虚拟化" | VirtualMachinePlatform not enabled OR BIOS VT-x disabled | Enable in BIOS + `dism` feature, reboot |
| "没有已安装的分发" | Distro not installed | Use `wsl --import` |
| `WININET_E_TIMEOUT` during `wsl --install` | GitHub raw blocked | Manual rootfs download + import |
| `dpkg` 404 on cloud-images.ubuntu.com | Wrong URL path | Use `/wsl/releases/24.04/current/` not `/wsl/noble/current/` |
| `useradd: invalid shell` | MSYS mangled `/bin/bash` path | Add `MSYS_NO_PATHCONV=1` |
| `update-desktop-database: not found` after dpkg | Missing desktop-file-utils | Harmless warning, ignore |
| `MESA: error: ZINK: failed to choose pdev` / `glx: failed to create drisw screen` | GPU passthrough broken (no /dev/dri), WSLg falls back to software but Mesa libs missing or wrong flags | Install `libgl1-mesa-dri libglx-mesa0 libegl-mesa0`, then force software rendering in wrapper: `export LIBGL_ALWAYS_SOFTWARE=1`. Add `--disable-gpu` flag for Electron apps. **DO NOT add `--disable-software-rasterizer` alongside `--disable-gpu`** — the combination crashes Electron apps with exit 255. |
| `libasound.so.2: not found` on Ubuntu 24.04 | Package renamed to `libasound2t64` (64-bit time_t migration) | `apt-get install -y libasound2t64` |
| Process stays alive but NO window appears on desktop | Window exists in WSLg's Weston compositor but not bridged to Windows desktop | Install `xdotool`, run `xdotool search --name ""` to confirm window exists; if found, it's a WSLg compositing issue. Also try `--disable-gpu` flag for Electron apps |
| `symbol lookup error: undefined symbol` from subprocess .so | LD_LIBRARY_PATH leaks parent lib path into subprocess, loading wrong library version | Use `ldconfig` + `/etc/ld.so.conf.d/` instead of LD_LIBRARY_PATH; unset LD_LIBRARY_PATH in wrapper |
| Chinese input: fcitx5 crashes with `zwp_input_method_v1 permission denied` | WSLg Weston blocks Wayland input method protocol | Remove fcitx5 wayland modules (libwayland.so, libwaylandim.so + conf files) — fcitx5 then runs on X11 with visible candidate window; see Chinese Input Method section |
| Chinese input: ibus pinyin works but candidate window invisible/offscreen | WSLg rendering — ibus candidate panel not visible | Use fcitx5 instead (above); ibus is only a fallback |
| `fcitx5-remote` crashes with `Failed to create dbus connection` | No DBus session bus in WSL | Harmless — ignore. fcitx5 works fine without DBus in X11-only mode. Use `pgrep fcitx5` to verify it's running, not `fcitx5-remote`. |

## Quick-launch from Terminal

Multiple methods, all pointing to the same wrapper script:

**git-bash** — add a function to `~/.bash_profile` (git-bash is a login shell, doesn't read `.bashrc` by default):
```bash
# ~/.bash_profile
wechat() { MSYS_NO_PATHCONV=1 wsl -d Ubuntu-24.04 -- bash /home/mayn/wechat.sh; }
```

**cmd/PowerShell** — place a `.cmd` file in a PATH directory (`C:\Users\<user>\bin\`):
```bat
@echo off
C:\Windows\System32\wsl.exe -d Ubuntu-24.04 -- bash /home/<user>/<app>.sh
```

**Desktop** — a `.bat` file for double-click launch (same content as `.cmd` above).

## References

- `references/mirrors.md` — Chinese mirror URLs for Ubuntu WSL rootfs and APT sources
- `references/chinese-gui-apps.md` — WeChat/DingTalk dependency resolution workflow, `ldd`-first pattern, known library lists
