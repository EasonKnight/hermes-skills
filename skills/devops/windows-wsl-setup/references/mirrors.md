# Chinese Mirrors for WSL Setup

## Ubuntu WSL Rootfs (for wsl --import)

Only some mirrors carry the `/ubuntu-cloud-images/` path — not all Ubuntu mirrors include cloud images.

### Verified working

| Mirror | URL | Status |
|--------|-----|--------|
| USTC (中科大) | `https://mirrors.ustc.edu.cn/ubuntu-cloud-images/wsl/releases/noble/current/ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz` | ✓ 340MB, ~10MB/s |

### Verified NOT working (404)

| Mirror | URL |
|--------|-----|
| Tsinghua (清华) | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu-cloud-images/wsl/releases/noble/current/...` |
| Tsinghua releases | `https://mirrors.tuna.tsinghua.edu.cn/ubuntu-releases/24.04/ubuntu-24.04-wsl-amd64.wsl` |
| USTC releases | `https://mirrors.ustc.edu.cn/ubuntu-releases/24.04/ubuntu-24.04-wsl-amd64.wsl` |
| Aliyun (阿里云) | `https://mirrors.aliyun.com/ubuntu-cdimage/wsl/noble/current/...` |

### URL path note

The correct path on cloud-images mirrors is:
```
/wsl/releases/24.04/current/ubuntu-noble-wsl-amd64-24.04lts.rootfs.tar.gz
```
NOT `/wsl/noble/current/` (that path was reorganized).

## APT Sources (Ubuntu 24.04 DEB822 format)

File: `/etc/apt/sources.list.d/ubuntu.sources`

### USTC (中科大) — verified working

```
Types: deb
URIs: https://mirrors.ustc.edu.cn/ubuntu
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
```

Also works for security updates (though these technically come from `security.ubuntu.com`, the mirror usually has them synced).

### Other mirrors (not tested but likely work)

- Tsinghua: `https://mirrors.tuna.tsinghua.edu.cn/ubuntu`
- Aliyun: `https://mirrors.aliyun.com/ubuntu`
- 163: `https://mirrors.163.com/ubuntu`

## WSL Install (wsl --install)

`wsl --install -d Ubuntu-24.04` fetches `raw.githubusercontent.com/microsoft/WSL/master/distributions/DistributionInfo.json` — this domain is blocked in mainland China. The `--web-download` flag does not bypass this; it still hits GitHub raw first.

**Recommendation**: Always use manual rootfs download + `wsl --import` in China. Never rely on `wsl --install`.
