# Tencent App Naming Conventions

Tencent products often have mismatched internal and display names. Use all variations when searching.

## WeChat Desktop (微信)
- Internal/process name: `WeChat`, `wechat`
- Data directory: `%APPDATA%\Tencent\xwechat` or `%APPDATA%\Tencent\WeChat`
- Install directory: `%LOCALAPPDATA%\Tencent\WeChat` or `C:\Program Files\Tencent\WeChat`
- Uninstall entry: "微信" or "WeChat"

## WeChat Input Method (微信输入法) — SEPARATE PRODUCT
- Internal/process name: `WeType`, `WeChatInput`, `wetype`
- Chinese name: 微信输入法 (sometimes marketed as 微信键盘 in early versions)
- Possible install locations:
  - `C:\Program Files (x86)\Tencent\WeType`
  - `%LOCALAPPDATA%\Tencent\WeType`
  - Windows Store Appx package
- Registers as a Windows TSF IME via CTF TIP CLSID (see SKILL.md Step 1 — IME apps)
- Does NOT appear in normal Uninstall registry — must check HKLM CTF TIP
- NOT part of WeChat desktop; must be installed separately

## WeGame (腾讯WeGame)
- Internal name: `WeGame`
- Install directory: `C:\Program Files (x86)\WeGame` or `C:\WeGameApps`
- Data: Various Tencent subdirs in AppData

## QQ / QQNT
- Internal name: `QQ`, `QQNT`
- Install directory: `C:\Program Files\Tencent\QQNT`
- Data: `%APPDATA%\Tencent\QQ`, `%APPDATA%\Tencent\QQNT`
