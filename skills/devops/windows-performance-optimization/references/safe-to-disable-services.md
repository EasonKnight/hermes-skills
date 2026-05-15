# Safe-to-Disable Windows Services (Gaming PC)

Reference table of Windows services that are safe to disable or set to manual on a gaming/desktop PC, along with their impact.

## Already Disabled (check first — from prior sessions)

| Service | Start Type |
|---------|-----------|
| SysMain (Superfetch) | Disabled |
| DiagTrack (Telemetry) | Disabled |
| WSearch (Windows Search) | Disabled |
| XblAuthManager (Xbox Auth) | Disabled |
| XblGameSave (Xbox Save) | Disabled |
| XboxGipSvc (Xbox Accessory) | Disabled |
| `BcastDVRUserService_*` (Game Bar/DVR) | Disabled |
| `InventorySvc` (Compatibility Inventory) | Disabled |
| `AMD Crash Defender Service` | Disabled |
| `GigabyteUpdateService` | Disabled |
| `PCManager Service Store` (MS PC Manager) | Disabled |
| `PcaSvc` (Program Compatibility Asst) | Disabled |
| `WpnService` (Push Notifications) | Disabled |
| `lfsvc` (Geolocation) | Disabled |
| `OneSyncSvc_*` (Mail/Calendar Sync) | Disabled |
| `DoSvc` (Delivery Optimization) | Disabled |

## Safe to Disable

| Service Name | Display Name | Impact if Disabled |
|-------------|-------------|-------------------|
| `AMD Crash Defender Service` | AMD Crash Defender | Crash reporting won't upload (game performance unaffected) |
| `GigabyteUpdateService` | GIGABYTE Update | Motherboard auto-update disabled (manually check BIOS) |
| `InventorySvc` | Inventory/Compatibility Assessment | No impact on daily use |
| `PCManager Service Store` | Microsoft PC Manager | PC Manager app won't auto-start |
| `OneSyncSvc_*` | OneSync (Mail/Calendar) | Mail/calendar won't sync in background |
| `DoSvc` | Delivery Optimization | Windows Update no longer P2P (downloads only from MS servers) |
| `PcaSvc` | Program Compatibility Assistant | No more compatibility pop-ups |
| `WpnService` | Windows Push Notifications | No push notifications from apps/websites |
| `WpnUserService_*` | Push Notifications (User) | Same as above (user-level) |
| `lfsvc` | Geolocation Service | Apps can't detect your location |
| `TextInputManagementService` | Touch Keyboard Input | No effect without touch screen |
| `webthreatdefusersvc_*` | Web Threat Defense | Defender core still active; web-level checks reduced |
| `cbdhsvc_*` | Clipboard History | Win+V clipboard history won't sync across devices |
| `WifiAutoInstallSrv` | WiFi Auto Install | Only needed during WiFi adapter setup |

## Set to Manual (from Automatic)

| Service | Reason |
|---------|--------|
| `wuauserv` (Windows Update) | Triggered on-demand; doesn't need to auto-start |
| `cbdhsvc_*` (Clipboard History) | Only needed when you open clipboard history |

## Protected Services (Do NOT Touch)

| Service | Why |
|---------|-----|
| `WinDefend` / `SecurityHealthService` | Windows Defender antivirus |
| `mpssvc` | Windows Firewall |
| `BFE` | Base Filtering Engine (firewall dependency) |
| `EventLog` | System logging (diagnostics need it) |
| `Schedule` | Task Scheduler (many system functions depend on it) |
| `Themes` | Visual themes break without it |
| `WlanSvc` / `Wcmsvc` | WiFi connectivity |
| `AudioEndpointBuilder` / `Audiosrv` | No sound without it |
| `Dhcp` / `Dnscache` / `Nsi` | Network connectivity |
| `CryptSvc` | Certificate/encryption (Steam, HTTPS all need it) |
| Any `Intel(R)` or `NVIDIA` service | Driver-level functionality |

## Notes

- Services with `_*` suffix (e.g., `_8da59`) are per-user instances of template services. User SID suffix changes per user account. Use `sc query | findstr` to find the exact name.
- Setting a service to `Disabled` prevents it from running until re-enabled. Some Windows components (Defender, Firewall) will auto-re-enable themselves after Windows Update.
- After disabling services, a reboot is recommended to verify the system still boots and functions correctly.
