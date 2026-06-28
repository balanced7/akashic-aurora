@echo off
chcp 65001 >nul
echo Creating Desktop Shortcuts...
powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut($Desktop + '\Akashic Aurora Launch.lnk'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/k E:\AI-Setup\turbo_launch.bat'; $Shortcut.WorkingDirectory = 'E:\AI-Setup'; $Shortcut.Description = 'Launch Akashic Aurora with OpenCode'; $Shortcut.Save(); Write-Host 'Created: Akashic Aurora Launch'"
powershell -NoProfile -Command "$WshShell = New-Object -comObject WScript.Shell; $Desktop = [Environment]::GetFolderPath('Desktop'); $Shortcut = $WshShell.CreateShortcut($Desktop + '\Akashic Aurora Status.lnk'); $Shortcut.TargetPath = 'cmd.exe'; $Shortcut.Arguments = '/k cd /d E:\AI-Setup && python -c \"from project_context import get_context_manager; mgr = get_context_manager(); ctx = mgr.get_full_context(); print()\"'; $Shortcut.WorkingDirectory = 'E:\AI-Setup'; $Shortcut.Description = 'Quick status'; $Shortcut.Save(); Write-Host 'Created: Akashic Aurora Status'"
echo Done! Shortcuts on Desktop.
pause
