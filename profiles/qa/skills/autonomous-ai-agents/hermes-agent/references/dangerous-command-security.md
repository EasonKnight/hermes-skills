# Hermes Dangerous Command Security System

## Overview

Hermes has a **3-layer defense system** to prevent accidental or malicious destruction via the terminal tool. The layers are checked in order:

```
terminal(command="rm -rf /")
  → Check 1: HARDLINE BLOCKLIST  (unconditional, below yolo)
  → Check 2: YOLO bypass         (only bypasses DANGEROUS_PATTERNS, not HARDLINE)
  → Check 3: DANGEROUS_PATTERNS  (requires user approval)
  → Check 4: SUDO STDIN GUARD    (blocks password-guessing attacks)
  → Check 5: Approval mode       (manual | smart | off)
```

Only if ALL checks pass does the command execute.

---

## Layer 1: Hardline Blocklist (Unconditional)

**Source:** `tools/approval.py:148-209`

Commands so catastrophic they **cannot run even with `--yolo`**. Hardcoded in Python with regex patterns. From source code comment:

> "Hardline only applies to environments that can actually damage the host (local, ssh, container-host cron). Containerized backends (docker, singularity, modal, daytona) skip this entirely because nothing they do can touch the host."

```python
HARDLINE_PATTERNS = [
    # rm recursive at filesystem root
    rm -rf /, /home, /root, /etc, /usr, /var, /bin, /sbin, /boot, /lib
    rm -rf ~, $HOME
    
    # Format filesystem
    mkfs.*
    
    # Raw block device overwrite
    dd of=/dev/sd*, /dev/nvme*, /dev/hd*
    > /dev/sd*
    
    # Kill all processes
    kill -1
    
    # Fork bomb
    :() { :|:& };:
    
    # Shutdown / reboot
    shutdown, reboot, halt, poweroff
    systemctl poweroff/reboot
    init 0/6, telinit 0/6
]
```

Hardline matches produce this response:

```
BLOCKED (hardline): {description}.
This command is on the unconditional blocklist and cannot be
executed via the agent — not even with --yolo, /yolo,
approvals.mode=off, or cron approve mode. If you genuinely
need to run it, run it yourself in a terminal outside the agent.
```

---

## Layer 2: Dangerous Patterns (Requires Approval)

**Source:** `tools/approval.py:305-390`

Commands that are destructive but potentially legitimate in context. The LLM cannot run these without user confirmation.

```python
DANGEROUS_PATTERNS = [
    # File destruction
    rm in root path, rm -r (recursive delete)
    find -exec rm, find -delete, xargs rm
    
    # Permission changes
    chmod 777/666/world-writable
    chmod -R 777
    chown -R root
    
    # Disk operations
    dd if=... (disk copy)
    > /dev/sd* (write to block device)
    mkfs (format)
    
    # SQL destruction
    DROP TABLE/DATABASE
    DELETE FROM without WHERE
    TRUNCATE TABLE
    
    # System modification
    > /etc/ (write to system config)
    cp/mv/install into /etc/
    sed -i on /etc/
    systemctl stop/restart (stop services)
    
    # Process killing
    kill -9 -1, pkill -9
    
    # Remote execution risk
    curl | bash (pipe to shell)
    bash/sh/zsh <(curl ...)
    script execution via -e/-c flags
    script execution via heredoc
    chmod +x then immediate execution
    
    # Git destructive operations
    git reset --hard
    git push --force / -f
    git clean -f
    git branch -D
    
    # Sensitive file overwrite
    tee / overwrite ~/.ssh/authorized_keys
    tee / overwrite ~/.hermes/.env
    overwrite ~/.bashrc, ~/.zshrc
    overwrite project .env / config.yaml
    
    # Self-termination protection
    hermes gateway stop/restart
    hermes update
    pkill/killall hermes/gateway/cli.py
    kill $(pgrep ...)
    
    # Sudo privilege flags (without configured password)
    sudo -S (stdin), sudo -s (shell), sudo -a (list)
]
```

When a dangerous pattern matches, the user gets an interactive prompt:

```
⚠️  This command is potentially dangerous ({description}).
    Command: {command}

Allow options:
  [y] Yes, run once
  [s] Yes, allow for this session
  [a] Always allow this pattern
  [d] Deny
```

If denied, the LLM receives:

```
BLOCKED: User denied this potentially dangerous command (matched
'{description}' pattern). Do NOT retry this command - the user
has explicitly rejected it.
```

---

## Layer 3: Sudo Stdin Guard (Password Guess Prevention)

**Source:** `tools/approval.py:234-255`

```python
# When SUDO_PASSWORD is NOT configured in .env:
# Any explicit "sudo -S" in the command is the LLM piping
# a guessed password via stdin. This is a brute-force attack
# vector: the model iterates through candidate passwords,
# inspects sudo's "Sorry, try again" output, and refines.
# Treat this as an unconditional block.
```

If `SUDO_PASSWORD` is set in `.env`, Hermes injects `-S` internally — that's the legitimate path. The guard only fires when NOT set, meaning the LLM wrote `sudo -S` on its own to guess your password.

---

## Approval Modes (`approvals.mode`)

Set via `approvals.mode` in config.yaml:

| Mode | Behavior | When to use |
|------|----------|-------------|
| `manual` (default) | Always prompt user when a dangerous pattern matches | Default safety |
| `smart` | Use auxiliary LLM to auto-approve low-risk commands, prompt on high-risk | Reduce interruptions for experienced users |
| `off` | Skip all dangerous-command checks (equivalent to `--yolo`) | Fully trusted agent, never use in production |

```bash
hermes config set approvals.mode smart      # recommended middle ground
hermes config set approvals.mode off         # bypass everything (not recommended)
```

---

## Per-Session Approval Tracking

Approvals are tracked per-session via a thread-safe state keyed by `session_key`. When a user selects "allow for this session," the approval is cached for the duration of that session only.

The LLM is told exactly what the user chose — `"User denied this command, do NOT retry"` — preventing the LLM from attempting the same command again with a different phrasing.

---

## YOLO Mode

`--yolo` bypasses Layer 2 (DANGEROUS_PATTERNS) but NOT Layer 1 (HARDLINE). This is a deliberate design choice:

> "Opting into yolo is trusting the agent with your files and services, not trusting it to wipe the disk or power the box off."

```bash
# CLI flag
hermes --yolo

# Environment variable
export HERMES_YOLO_MODE=1

# In-session toggle (/yolo)
# (gateway only — scoped to current gateway session)
```

---

## Containerized Environments

Docker, Singularity, Modal, Daytona, and Vercel Sandbox backends **skip all dangerous-command checks entirely**. Since these environments are isolated from the host, destructive commands inside them cannot damage the user's machine.

Only the `local` and `ssh` backends run checks.

---

## Quick Reference Table

| Command | Layer | Bypassable? | Example error message |
|---------|-------|-------------|----------------------|
| `rm -rf /` | HARDLINE | ❌ Even with `--yolo` | "recursive delete of root filesystem" |
| `rm -rf ~/projects/*` | DANGEROUS | ✅ With `--yolo` or approval | "delete in root path" |
| `dd of=/dev/sda` | HARDLINE | ❌ Even with `--yolo` | "dd to raw block device" |
| `chmod 777 /tmp/x` | DANGEROUS | ✅ With approval | "world/other-writable permissions" |
| `sudo -S <password>` (no SUDO_PASSWORD) | SUDO GUARD | ❌ | "sudo password guessing via stdin" |
| `sudo -S <password>` (SUDO_PASSWORD set) | None | ✅ | No check (internal injection) |
| `docker run --rm alpine rm -rf /` | None (docker) | ✅ | No check (container isolation) |
| `reboot` | HARDLINE | ❌ Even with `--yolo` | "system shutdown/reboot" |
| `git push --force` | DANGEROUS | ✅ With approval | "force push" |
| `hermes gateway stop` | DANGEROUS | ✅ With approval | "stop/restart hermes gateway" |
