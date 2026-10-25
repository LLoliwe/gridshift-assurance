"""Lane B regression (C17): both runtimes emit the identical intake-size message from one
shared source (web/workspace/intake-limits.json). Synthetic development test."""
from pathlib import Path
import json, re, subprocess, sys, unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'web/engine/src'), str(ROOT / 'web/workspace')]
from case_adapter import open_case
LIMITS = json.loads((ROOT / 'web/workspace/intake-limits.json').read_text(encoding='utf-8'))


class SharedLimitMessageTests(unittest.TestCase):
    def test_native_empty_and_oversize_use_shared_message(self):
        self.assertEqual(LIMITS['open_size_message'], 'Open expects 1 byte to 768 KiB (786432 bytes) of original raw file bytes.')
        for raw in [b'', b' ' * (LIMITS['envelope_limit_bytes'] + 1)]:
            with self.subTest(size=len(raw)), self.assertRaises(ValueError) as ctx:
                open_case(raw)
            self.assertEqual(str(ctx.exception), LIMITS['open_size_message'])

    def test_worker_emits_identical_string_from_same_source(self):
        script = ("import {validateMessage} from './web/workspace/workspace-worker.js';"
                  "try{validateMessage({id:1,type:'review',activities:{operation:'open',raw:new Uint8Array(0)}});}"
                  "catch(e){process.stdout.write(e.message);}")
        out = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', script], cwd=ROOT,
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.stdout, LIMITS['open_size_message'], out.stderr)

    def test_c17_error_text_byte_identical_across_runtimes(self):
        """Native `ValueError: msg` equals the worker's structured refusal formatted as the harness does."""
        for raw in [b'', b' ' * (LIMITS['envelope_limit_bytes'] + 1)]:
            with self.subTest(size=len(raw)):
                try:
                    open_case(raw)
                except ValueError as error:
                    native = f'{type(error).__name__}: {error}'
                script = ("import {handleMessage} from './web/workspace/workspace-worker.js';"
                          f"const raw=new Uint8Array({len(raw)});"
                          "for(const operation of ['open','intake']){let m;"
                          "await handleMessage({id:1,type:'review',activities:{operation,raw}},x=>m=x,async()=>{throw Error('Python must not load');});"
                          "process.stdout.write(JSON.stringify({kind:m.kind,text:m.exception?`${m.exception}: ${m.message}`:`JSWorkerError: ${m.message}`})+'\\n');}")
                out = subprocess.run(['node', '--no-warnings', '--input-type=module', '-e', script], cwd=ROOT,
                                     capture_output=True, text=True, timeout=60)
                rows = [json.loads(line) for line in out.stdout.splitlines()]
                self.assertEqual(len(rows), 2, out.stderr)
                for row in rows:
                    self.assertEqual(row, {'kind': 'intake_refusal', 'text': native})
                self.assertEqual(native.encode('utf-8'), rows[0]['text'].encode('utf-8'))

    def test_no_duplicated_literal_size_text(self):
        for name in ['workspace-worker.js', 'workspace.js', 'case_adapter.py']:
            text = (ROOT / 'web/workspace' / name).read_text(encoding='utf-8')
            self.assertNotRegex(text, r'1–768 KiB|1–\{limit\}|786432', name)


if __name__ == '__main__':
    unittest.main()
