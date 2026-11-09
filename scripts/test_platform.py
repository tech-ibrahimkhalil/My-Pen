"""Run portable tests and optional native Qt startup checks; write honest per-host evidence."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(command, env, timeout):
    start = time.perf_counter()
    try:
        process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
        return {'status': 'passed' if process.returncode == 0 else 'failed',
                'returncode': process.returncode, 'seconds': round(time.perf_counter()-start, 3),
                'output': process.stdout+process.stderr}
    except subprocess.TimeoutExpired:
        return {'status': 'failed', 'reason': 'Timed out', 'seconds': timeout, 'output': ''}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gui-smoke', action='store_true', help='Also open/close native Qt windows on this desktop')
    parser.add_argument('--output', type=Path, default=ROOT/'test-results')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    results = {'date_utc': datetime.now(timezone.utc).isoformat(), 'system': platform.system(),
               'os_release': platform.release(), 'os_version': platform.version(),
               'machine': platform.machine(), 'python': platform.python_version(),
               'native_desktop_acceptance': 'not_tested', 'checks': {}}
    if hasattr(platform, 'freedesktop_os_release') and sys.platform.startswith('linux'):
        results['distribution'] = platform.freedesktop_os_release().get('PRETTY_NAME')
    try:
        import PySide6
        from PySide6.QtCore import qVersion
        results.update(pyside=PySide6.__version__, qt=qVersion())
    except ImportError as error:
        results['checks']['dependencies'] = {'status':'failed', 'output':str(error)}
    else:
        print('Running offscreen regression suite...', flush=True)
        suite = run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], env, 180)
        found = re.search(r'Ran (\d+) tests?', suite['output'])
        suite['tests_run'] = int(found.group(1)) if found else None
        results['checks']['offscreen_suite'] = suite
        results['checks']['background_startup_offscreen'] = run(
            [sys.executable, 'main.py', '--background', '--smoke-test'], env, 20)
        if args.gui_smoke:
            available = not sys.platform.startswith('linux') or bool(os.environ.get('DISPLAY') or os.environ.get('WAYLAND_DISPLAY'))
            if available:
                native_env = dict(os.environ)
                native_env.pop('QT_QPA_PLATFORM', None)
                for flag in ('--windowed', '--overlay', '--background'):
                    print('Native startup check: '+flag, flush=True)
                    results['checks']['native_'+flag[2:]] = run(
                        [sys.executable, 'main.py', flag, '--smoke-test'], native_env, 20)
                results['native_desktop_acceptance'] = 'startup_checks_only; manual interaction not tested'
            else:
                results['checks']['native_startup'] = {'status':'skipped', 'reason':'No DISPLAY or WAYLAND_DISPLAY'}
        else:
            results['checks']['native_startup'] = {'status':'not_run', 'reason':'Use --gui-smoke on a graphical desktop'}
    name = re.sub(r'[^a-z0-9_-]', '_', (platform.system()+'_'+platform.machine()).lower())
    report = args.output/(name+'.json')
    report.write_text(json.dumps(results, indent=2), encoding='utf-8')
    log = args.output/(name+'.log')
    log.write_text('\n\n'.join(key+'\n'+value.get('output',value.get('reason',''))
                               for key,value in results['checks'].items()), encoding='utf-8')
    for key, value in results['checks'].items():
        print(key+': '+value['status'])
    print('Report: '+str(report))
    return int(any(value['status']=='failed' for value in results['checks'].values()))


if __name__ == '__main__':
    raise SystemExit(main())
