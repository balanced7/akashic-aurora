# BREAKTHROUGH STACK - QUICK LAUNCH GUIDE

## One-Click Launch (Recommended)

Double-click **`turbo_launch.bat`** for the fastest startup:
- Auto-checks Docker, starts if needed
- Verifies Redis HA is running
- Pre-generates context
- Launches OpenCode fully primed

## Individual Shortcuts

| Shortcut | Purpose |
|----------|---------|
| `turbo_launch.bat` | Full launch with OpenCode |
| `bootstrap.bat` | Bootstrap services only |
| `install_shortcuts.bat` | Create Desktop shortcuts |

## First-Time Setup

1. Run `install_shortcuts.bat` to create Desktop shortcuts
2. Pin "BreakThrough Launch" to taskbar for 1-click startup
3. Docker Desktop should auto-start with Windows (enable in Docker settings)

## Startup Flow

```
turbo_launch.bat
├── Check Docker (skip if running)
│   └── Auto-start if needed (waits up to 45s)
├── Check Redis HA (skip if responding)
│   └── Start containers if needed (6-8s)
├── Pre-generate context
│   └── quick_context.json for fast load
├── Start sync service (background)
└── Launch OpenCode
    └── Reads AGENT_PRIMER.md for full context
```

## Expected Startup Times

| Scenario | Time |
|----------|------|
| Docker already running | ~3-5 seconds |
| Docker needs restart | ~30-45 seconds |
| First run (cold) | ~60 seconds |

## Manual Commands

```powershell
# Check status
python E:\AI-Setup\services\redis_sync.py --status

# Restart services
E:\AI-Setup\bootstrap.bat

# Quick context
python E:\AI-Setup\project_context.py --context
```

## Troubleshooting

**Docker won't start?**
- Check Docker Desktop settings > General > "Start Docker Desktop when you sign in"
- Manually start Docker Desktop, then run turbo_launch.bat

**Redis not responding?**
- Run `docker ps` to check containers
- Run `E:\AI-Setup\bootstrap.bat` for full restart

**OpenCode not primed?**
- First message: "Tell me the current status"
