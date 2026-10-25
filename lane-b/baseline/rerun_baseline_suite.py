#!/usr/bin/env python3
"""Rerun the baseline Python suite and write a log plus its sha256.

Usage: rerun_baseline_suite.py [--suite tests|web-tests] [--out DIR]
Writes DIR/<suite>_<UTC timestamp>.log and DIR/<same>.log.sha256 (sha256sum format).
Exits with the unittest exit status (non-zero if any test failed or errored).
Nothing is written into the repository.
"""
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--suite', default='tests', choices=['tests', 'web-tests'])
    ap.add_argument('--out', default='/workspace/el-verify/logs/baseline')
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    head = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain', '--untracked-files=no'],
                           capture_output=True, text=True).stdout.strip()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    proc = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', args.suite, '-v'],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    header = (f'# GRIDSHIFT baseline rerun\n# suite: {args.suite}\n# utc: {stamp}\n# commit: {head}\n'
              f'# tracked changes: {"YES" if dirty else "none"}\n# python: {sys.version.split()[0]}\n'
              f'# command: {sys.executable} -m unittest discover -s {args.suite} -v\n# exit: {proc.returncode}\n\n')
    log = out / f'{args.suite}_{stamp}.log'
    log.write_text(header + proc.stdout + proc.stderr)
    digest = sha256(log.read_bytes()).hexdigest()
    (out / f'{log.name}.sha256').write_text(f'{digest}  {log.name}\n')
    ran = re.search(r'Ran (\d+) tests?', proc.stderr)
    print(f'suite={args.suite} ran={ran.group(1) if ran else "?"} exit={proc.returncode} '
          f'status={"OK" if proc.returncode == 0 else "FAILED"}\nlog={log}\nsha256={digest}')
    return proc.returncode


if __name__ == '__main__':
    sys.exit(main())
