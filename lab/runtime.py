"""Native GCC/Clang build shared by Windows, macOS, and Linux entry points."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent


def executable_path(platform=None):
    return PROJECT / 'build' / ('simulator.exe' if (platform or os.name) == 'nt' else 'simulator')


def build(force=False):
    compiler = os.environ.get('CC', 'gcc')
    found = shutil.which(compiler)
    if not found:
        raise RuntimeError(
            f'C compiler {compiler!r} was not found. Install native GCC (for example '
            'MSYS2 UCRT64 GCC on Windows), add its bin folder to PATH, and reopen '
            'PowerShell. WSL and Make are not required. You can also set CC to clang.'
        )
    target = executable_path()
    sources = [ROOT / 'simulator.c', PROJECT / 'simlib.c']
    dependencies = sources + [PROJECT / 'simlib.h', PROJECT / 'trace.h', Path(__file__)]
    if force or not target.exists() or any(p.stat().st_mtime > target.stat().st_mtime for p in dependencies):
        target.parent.mkdir(parents=True, exist_ok=True)
        # C11 is sufficient for the model and works with older MinGW GCC.
        command = [found, '-std=c11', '-O2', '-Wall', '-Wextra', '-Wpedantic',
                   '-I', str(PROJECT), *(str(p) for p in sources), '-lm', '-o', str(target)]
        print(f'Building {target.name} with {found}', flush=True)
        subprocess.run(command, check=True, cwd=PROJECT)
    return target


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--force', action='store_true')
    args = p.parse_args()
    print(build(force=args.force))


if __name__ == '__main__':
    main()
