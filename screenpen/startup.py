"""Explicit, per-user sign-in registration. Never enabled without a user choice."""
from pathlib import Path
import os
import plistlib
import subprocess
import sys

RUN_KEY = r'Software\Microsoft\Windows\CurrentVersion\Run'
LABEL = 'com.mypen.desktop'


class StartupManager:
    def __init__(self, platform=None, home=None, config_home=None, executable=None, script=None):
        self.platform = platform or sys.platform
        self.home = Path(home) if home else Path.home()
        self.config_home = Path(config_home or os.environ.get('XDG_CONFIG_HOME', self.home / '.config'))
        self.executable = Path(executable or sys.executable).resolve()
        self.script = Path(script or Path(__file__).resolve().parents[1] / 'main.py').resolve()

    def command(self):
        executable = self.executable
        if getattr(sys, 'frozen', False):
            return [str(executable), '--background']
        if self.platform == 'win32':
            windowed = executable.with_name('pythonw.exe')
            if windowed.exists():
                executable = windowed
        return [str(executable), str(self.script), '--background']

    def path(self):
        if self.platform == 'darwin':
            return self.home / 'Library' / 'LaunchAgents' / (LABEL + '.plist')
        return self.config_home / 'autostart' / 'my-pen.desktop'

    def enabled(self):
        if self.platform == 'win32':
            import winreg
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                    return bool(winreg.QueryValueEx(key, 'My Pen')[0])
            except FileNotFoundError:
                return False
        return self.path().exists()

    def set_enabled(self, enabled):
        if self.platform == 'win32':
            import winreg
            command = subprocess.list2cmdline(self.command())
            if enabled and len(command) > 260:
                raise OSError('Project path is too long for Windows startup. Move My Pen to a shorter path.')
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
                if enabled:
                    winreg.SetValueEx(key, 'My Pen', 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, 'My Pen')
                    except FileNotFoundError:
                        pass
            return
        path = self.path()
        if not enabled:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.platform == 'darwin':
            path.write_bytes(plistlib.dumps({'Label': LABEL, 'ProgramArguments': self.command(),
                                            'RunAtLoad': True, 'ProcessType': 'Interactive'}))
        elif self.platform.startswith('linux'):
            def quote(value):
                # Desktop Exec quoting followed by desktop-entry string escaping.
                if '\n' in value or '\r' in value:
                    raise ValueError('Startup paths cannot contain line breaks.')
                value = value.replace('%', '%%')
                value = ''.join('\\' + ch if ch in '\\"`$' else ch for ch in value)
                return '"' + value.replace('\\', '\\\\') + '"'
            command = ' '.join(quote(value) for value in self.command())
            path.write_text('[Desktop Entry]\nType=Application\nName=My Pen\nExec=' + command +
                            '\nTerminal=false\nX-GNOME-Autostart-enabled=true\n', encoding='utf-8')
        else:
            raise OSError('Startup is not supported on this platform.')
