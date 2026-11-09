"""Build on Windows x64: executable folder, smoke check, then Inno installer."""
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'win32' or struct.calcsize('P') != 8:
        raise SystemExit('Run this build with 64-bit Python on Windows.')
    os.chdir(ROOT)
    candidates = [os.environ.get('ISCC_EXE'), shutil.which('ISCC.exe')]
    for env in ('ProgramFiles(x86)', 'ProgramFiles', 'LOCALAPPDATA'):
        base = os.environ.get(env)
        if base:
            candidates += [str(Path(base) / 'Inno Setup 6' / 'ISCC.exe'),
                           str(Path(base) / 'Programs' / 'Inno Setup 6' / 'ISCC.exe')]
    compiler = next((p for p in candidates if p and Path(p).is_file()), None)
    if not compiler:
        raise SystemExit('Install Inno Setup 6, or set ISCC_EXE to its ISCC.exe path.')
    from PIL import Image
    icon = ROOT / 'images' / 'app' / 'my_pen.ico'
    with Image.open(ROOT / 'images' / 'app' / 'my_pen_icon.png') as im:
        im.convert('RGBA').save(icon, sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
                    '--onedir', '--windowed', '--name', 'My Pen',
                    '--icon', str(icon), '--add-data', 'images:images',
                    '--add-data', 'docs:docs', 'main.py'], check=True)
    exe = ROOT / 'dist' / 'My Pen' / 'My Pen.exe'
    subprocess.run([str(exe), '--windowed', '--smoke-test'], check=True, timeout=60)
    subprocess.run([compiler, str(ROOT / 'installer' / 'MyPen.iss')], check=True)
    print('Installer:', ROOT / 'installer-output' / 'MyPen-Setup-10.0-x64.exe')


if __name__ == '__main__':
    main()
