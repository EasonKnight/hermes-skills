# Path of Exile + WeGame 完整清理示例

## 背景
用户手动删除了 PoE 国际服（独立客户端，非 Steam）和 WeGame 腾讯版流放之路的游戏文件，但：
1. 配置文件/缓存仍留在 AppData 和 Documents 中
2. 控制面板「程序和功能」里仍有残留的卸载条目

## 文件残留位置

| 路径 | 内容 | 大小 |
|------|------|------|
| `%USERPROFILE%\Documents\My Games\Path of Exile\` | 配置 .ini | 小 |
| `%APPDATA%\Path of Exile\` | 着色器缓存 (ShaderCacheD3D12 约 200+ 子目录) + Minimap + ShopImages + VideoCache | 大 |
| `C:\Program Files (x86)\流放之路(511)\` | WeGame 版游戏本体（已提前手动删） | 已空 |

## 残留卸载条目

| DisplayName | 注册表位置 |
|-------------|-----------|
| POE助手Repo | `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\POE助手Repo` |
| WeGame | `HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\WeGame` |

## PowerShell 清理脚本

```powershell
# 删除文件残留
Remove-Item -Path "$env:USERPROFILE\Documents\My Games\Path of Exile" -Recurse -Force
Remove-Item -Path "$env:APPDATA\Path of Exile" -Recurse -Force

# 删除注册表卸载条目
$paths = @(
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
)
foreach ($regPath in $paths) {
    Get-ChildItem $regPath -ErrorAction SilentlyContinue | ForEach-Object {
        $name = $_.GetValue("DisplayName")
        if ($name -match "PoE|Path of Exile|流放|WeGame|wegame") {
            Remove-Item -Path $_.PSPath -Recurse -Force
            Write-Host "DELETED: $name"
        }
    }
}
```

## 关键教训
- PoE 的 ShaderCacheD3D12 极其庞大（数百 MB ~ 数 GB），是清理的重点
- `reg query` 对中文名支持差（CP936 vs UTF-8 编码问题），一定要用 PowerShell
- 从 git-bash 调用 PowerShell 时，`$_` 会被 bash 展开，必须把脚本存为 `.ps1` 文件再执行
- HKLM 下的 Uninstall 条目通常不需要管理员权限即可删除（但试过才知道）
