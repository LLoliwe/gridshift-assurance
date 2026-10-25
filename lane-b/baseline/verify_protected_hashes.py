#!/usr/bin/env python3
"""Verify the protected hashes from the private handoff evidence snapshot.

Exits non-zero on ANY mismatch. Read-only: writes nothing into the repository.

Checks, in order:
  1. d084b7f resolves to the expected full commit and every path listed in
     evidence-snapshot/protected_tree_d084b7f.sha256 hashes to the listed value
     *in that commit's git objects* (byte-exact, independent of the work tree).
  2. Work tree vs the same list. A difference is allowed ONLY for files in
     KNOWN_POST_D084B7F_CHANGES (changed deliberately by a later commit, named
     below), or for files in OWNER_R1_CHANGES whose work-tree bytes are IDENTICAL to
     their blob at the owner's lane-b/private-r1 tip (the rebase base). Any other
     drift, or a listed file missing from the work tree, fails.
  3. Frozen adversarial artifacts: cases.py and FROZEN_MANIFEST.json equal both the
     pinned hashes and their blobs at the freeze commit 3fbd448; run1_pre_fix and
     run2_post_fix result files equal their blobs at be8280c; and
     `python3 lane-b/adversarial/cases.py` (no --write) reports the manifest verified.
  4. The handoff folder's own SHA256SUMS.
"""
from hashlib import sha256
from pathlib import Path
import argparse
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
D084 = 'd084b7ffa09d4c920ff998105e6941934024964f'
FREEZE = '3fbd448'
HANDOFF_HEAD = 'be8280c9f9830acc07e3a06f32d2ac5d2482706b'
KNOWN_POST_D084B7F_CHANGES = {
    'web/workspace/case_adapter.py': '1b3aae5 (portable-number intake) and lane-b/quarantine (one guard line)',
    'web/workspace/workspace-worker.js': '1b3aae5 (adapter hash pin) and lane-b/quarantine (quarantine bridge)',
}
# Owner commits on lane-b/private-r1 (964f692, 840f636, 9b841af, c8eb25b, 52a2373) changed these
# protected files. Allowed only while byte-identical to the rebase base below.
OWNER_R1_TIP = '52a23736b5cedaf30da8d67f7430a6e127d0f4a7'
OWNER_R1_CHANGES = ['browser-tests/workspace.spec.mjs', 'web-tests/workspace-ui-native.mjs',
                    'web-tests/workspace-worker-contract.mjs', 'web/workspace/index.html',
                    'web/workspace/workspace.css', 'web/workspace/workspace.js',
                    'web/workspace/engine-controller.js']
FROZEN_PINS = {
    'lane-b/adversarial/cases.py': '7938f18d7ed42387bf7ac9bfb6fc28bcdae8d3a8fff921835f4974214b33def4',
    'lane-b/adversarial/FROZEN_MANIFEST.json': '9ab4f827be3e23beb5bd0f22044b6ea97094aedf95769b4071bc66382a394877',
}
RESULT_FILES = [f'lane-b/adversarial/results/{run}/{name}' for run in ('run1_pre_fix', 'run2_post_fix')
                for name in ('browser.json', 'comparison.json', 'native.json', 'playwright.log')]


def git(*args, binary=False):
    out = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, check=True)
    return out.stdout if binary else out.stdout.decode().strip()


def blob_sha(rev, path):
    return sha256(git('cat-file', 'blob', f'{rev}:{path}', binary=True)).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--handoff', default='/workspace/handoff-be8280c')
    args = ap.parse_args()
    handoff = Path(args.handoff)
    listing = handoff / 'evidence-snapshot/protected_tree_d084b7f.sha256'
    failures, lines = [], []

    def record(ok, text):
        lines.append(('OK   ' if ok else 'FAIL ') + text)
        if not ok:
            failures.append(text)

    record(git('rev-parse', 'd084b7f^{commit}') == D084, f'd084b7f resolves to {D084}')
    record(git('rev-parse', 'be8280c^{commit}') == HANDOFF_HEAD, f'be8280c resolves to {HANDOFF_HEAD}')
    entries = [l.split(None, 1) for l in listing.read_text().splitlines() if l.strip()]
    record(len(entries) > 0, f'{listing} lists {len(entries)} protected files')
    drift = 0
    for expected, path in entries:
        path = path.strip()
        try:
            got = blob_sha(D084, path)
        except subprocess.CalledProcessError:
            got = 'MISSING'
        record(got == expected, f'[commit d084b7f] {path}')
        wt = ROOT / path
        actual = sha256(wt.read_bytes()).hexdigest() if wt.is_file() else 'MISSING'
        if actual == expected:
            continue
        if path in KNOWN_POST_D084B7F_CHANGES and actual != 'MISSING':
            drift += 1
            lines.append(f'NOTE [worktree] {path} differs from d084b7f; allowed: {KNOWN_POST_D084B7F_CHANGES[path]}')
        elif path in OWNER_R1_CHANGES and actual != 'MISSING':
            try:
                owner = blob_sha(OWNER_R1_TIP, path)
            except subprocess.CalledProcessError:
                owner = 'MISSING'
            record(actual == owner, f'[worktree] {path} differs from d084b7f; must equal owner tip '
                                    f'{OWNER_R1_TIP[:7]} blob ({owner}) -> {actual}')
            drift += actual == owner
        else:
            record(False, f'[worktree] {path} unexpected drift ({actual})')
    record(True, f'[worktree] {len(entries) - drift} listed files byte-identical to d084b7f, {drift} allowed known changes')

    for path, pin in FROZEN_PINS.items():
        actual = sha256((ROOT / path).read_bytes()).hexdigest()
        record(actual == pin, f'[frozen] {path} sha256 {actual} == pinned {pin}')
        record(actual == blob_sha(FREEZE, path), f'[frozen] {path} equals its blob at freeze commit {FREEZE}')
    for path in RESULT_FILES:
        actual = sha256((ROOT / path).read_bytes()).hexdigest()
        record(actual == blob_sha(HANDOFF_HEAD, path), f'[frozen] {path} equals be8280c blob ({actual[:16]}…)')
    regen = subprocess.run([sys.executable, '-B', str(ROOT / 'lane-b/adversarial/cases.py')], capture_output=True, text=True, cwd=ROOT)
    record(regen.returncode == 0 and 'frozen manifest verified: 31 cases' in regen.stdout,
           f'[frozen] cases.py regeneration: {regen.stdout.strip() or regen.stderr.strip()}')

    sums = handoff / 'SHA256SUMS'
    for line in sums.read_text().splitlines():
        expected, name = line.split(None, 1)
        target = handoff / name.strip()
        actual = sha256(target.read_bytes()).hexdigest() if target.is_file() else 'MISSING'
        record(actual == expected, f'[handoff] {name.strip()}')

    print('\n'.join(lines))
    print(f'RESULT: {"FAIL" if failures else "PASS"} ({len(failures)} mismatches)')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
