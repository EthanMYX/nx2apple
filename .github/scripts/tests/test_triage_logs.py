import io
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import triage_logs as tl  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]

SYMPTOMS = """# Symptom index

## Services

- `[RED] fs ReadFile into … failed at +0 (EFAULT): VM region … protection 1`, now and then. → [ReadFile into write-protected texture pool pages](../reference/services.md#readfile-into-write-protected-texture-pool-pages)
- no sound: `[RED] audren: no DeviceSink (ID 0x10) in the command list, 0 commands of 0x148 bytes`. → [SDK 4: DeviceSink](../reference/audio.md#sdk-4-devicesink)
- a `[RED] x` line alone. → [Too short](../reference/services.md#too-short)
- `[RED] MapMemory refused (0xd401)` for a stack, then an abort. → [Thread stacks](../reference/services.md#thread-stacks)
"""

SERVICES = """# Services

## Other

### ReadFile into write-protected texture pool pages

- **Symptom:** `[RED] fs ReadFile into … failed`
- **Found on:** [Monster Train 2](../../dm/games/010051701FB46000/README.md) at 60 fps, and [Other](../../dm/games/0100A6301214E000/README.md).
- **Check:** four runs.

### Thread stacks

- **Symptom:** x
"""


class Extract(unittest.TestCase):
    def test_signals(self):
        log = ["[dm] boot", "12:00 [RED] audren: a second renderer 7", "12:01 [RED] audren: a second renderer 9",
               "[RED] MapMemory refused (0xd401): 0x1000", "[RED] MapMemory refused (0xd402): 0x2000",
               "[dm] CRASH sig=10 (stderr held)", "fork patches: a, b", "noise"]
        s = tl.finish_signals(tl.extract_signals(log))
        self.assertEqual([c for _, c in s['red']], [2, 2])   # folded: same line, only numbers differ
        self.assertEqual(len(s['crash']), 1)
        self.assertEqual(s['fork_patches'], ['fork patches: a, b'])

    def test_caps(self):
        s = tl.finish_signals(tl.extract_signals(f'[RED] distinct message number {chr(97 + i % 26)}{"x" * (i // 26)}' for i in range(500)))
        self.assertEqual(len(s['red']), tl.MAX_SIGNAL_LINES)
        s = tl.finish_signals(tl.extract_signals(['[RED] ' + 'a' * 5000]))
        self.assertLess(len(s['red'][0][0]), tl.MAX_LINE + 20)

    def test_no_signals(self):
        s = tl.finish_signals(tl.extract_signals(['hello', 'world']))
        self.assertEqual(s, {'red': [], 'crash': [], 'fork_patches': []})


class Match(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        (d / 'agents').mkdir()
        (d / 'reference').mkdir()
        (d / 'reference' / 'services.md').write_text(SERVICES)
        self.docs = d
        self.syms = tl.parse_symptoms(SYMPTOMS)

    def tearDown(self):
        self.tmp.cleanup()

    def test_parse(self):
        self.assertEqual(len(self.syms), 4)
        self.assertEqual(self.syms[2]['fragments'], [])   # too few literal characters to match on

    def test_hit_with_games(self):
        line = '[RED] fs ReadFile into 0x7f001000 failed at +0 (EFAULT): VM region 0x7f00 protection 1'
        hits = tl.match_symptoms([line], self.syms, self.docs)
        self.assertEqual(len(hits), 1)
        h = hits[0]
        self.assertEqual(h['entry'], 'ReadFile into write-protected texture pool pages')
        self.assertEqual(h['url'], tl.BLOB + 'docs/reference/services.md#readfile-into-write-protected-texture-pool-pages')
        self.assertEqual([g['title_id'] for g in h['found_on']], ['010051701FB46000', '0100A6301214E000'])

    def test_numbers_do_not_matter(self):
        hits = tl.match_symptoms(['[RED] audren: no DeviceSink (ID 0x99) in the command list, 7 commands of 0x10 bytes'], self.syms, self.docs)
        self.assertEqual([h['entry'] for h in hits], ['SDK 4: DeviceSink'])
        self.assertEqual(hits[0]['found_on'], [])   # its reference file is not there

    def test_no_hit(self):
        self.assertEqual(tl.match_symptoms(['[RED] something entirely new happened here'], self.syms, self.docs), [])
        self.assertEqual(tl.match_symptoms(['[RED] x'], self.syms, self.docs), [])

    def test_order_of_pieces(self):
        self.assertFalse(tl.fragment_matches(['b', 'a'], 'a b'))

    def test_slug(self):
        self.assertEqual(tl.slug('`ro::LookupModuleSymbol` for a name'), 'rolookupmodulesymbol-for-a-name')
        self.assertEqual(tl.slug('SDK 4: DeviceSink is command 0xf'), 'sdk-4-devicesink-is-command-0xf')


class RealIndex(unittest.TestCase):
    @unittest.skipUnless((REPO_ROOT / 'docs/agents/symptoms.md').is_file(), 'no vendored docs')
    def test_every_fragment_matches_itself_and_entries_resolve(self):
        docs = REPO_ROOT / 'docs'
        syms = tl.parse_symptoms((docs / 'agents/symptoms.md').read_text(encoding='utf-8'))
        self.assertGreater(len(syms), 100)
        n = 0
        for e in syms:
            for pieces in e['fragments']:
                n += 1
                self.assertTrue(tl.fragment_matches(pieces, ' 12 '.join(pieces)), pieces)
        self.assertGreater(n, 20)
        # every linked entry has its heading in its reference file (found_on returns a list, never raises)
        for e in syms[:40]:
            self.assertIsInstance(tl.found_on(docs, e['href']), list)


class Attachments(unittest.TestCase):
    def test_urls(self):
        body = ('log: https://github.com/user-attachments/files/123/game.log. also https://evil.example/x.log and '
                '![x](https://user-images.githubusercontent.com/1/a.png) https://github.com/user-attachments/files/123/game.log')
        self.assertEqual(tl.attachment_urls(body), ['https://github.com/user-attachments/files/123/game.log',
                                                    'https://user-images.githubusercontent.com/1/a.png'])

    def test_limit(self):
        body = ' '.join(f'https://github.com/user-attachments/files/{i}/a.log' for i in range(10))
        self.assertEqual(len(tl.attachment_urls(body)), tl.MAX_ATTACHMENTS)

    def test_other_host_refused_without_a_request(self):
        class Boom:
            def open(self, *a, **k):
                raise AssertionError('must not be fetched')
        self.assertEqual(list(tl.fetch_lines('https://evil.example/a.log', opener=Boom())), [])
        self.assertEqual(list(tl.fetch_lines('http://github.com/user-attachments/files/1/a.log', opener=Boom())), [])

    def _opener(self, data, ctype='text/plain'):
        class R(io.BytesIO):
            headers = {'Content-Type': ctype}
            def __enter__(s): return s
            def __exit__(s, *a): pass
        class O:
            def open(s, req, timeout=None):
                self.timeout = timeout
                return R(data)
        return O()

    URL = 'https://github.com/user-attachments/files/1/a.log'

    def test_lines_and_timeout(self):
        o = self._opener(b'one\n[RED] two\nthree')
        self.assertEqual(list(tl.fetch_lines(self.URL, opener=o)), ['one', '[RED] two', 'three'])
        self.assertEqual(self.timeout, tl.FETCH_TIMEOUT)

    def test_size_cap(self):
        o = self._opener(b'a line\n' * 1000)
        lines = list(tl.fetch_lines(self.URL, opener=o, max_bytes=700))
        self.assertLessEqual(sum(len(x) + 1 for x in lines), 700)

    def test_binary_and_images_skipped(self):
        self.assertEqual(list(tl.fetch_lines(self.URL, opener=self._opener(b'ab\0cd'))), [])
        self.assertEqual(list(tl.fetch_lines(self.URL, opener=self._opener(b'png', 'image/png'))), [])

    def test_redirect_to_other_host_refused(self):
        h = tl._Redirect()
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(None, None, 302, 'Found', {}, 'https://evil.example/x')
        with self.assertRaises(urllib.error.URLError):
            h.redirect_request(None, None, 302, 'Found', {}, 'http://github.com/x')


if __name__ == '__main__':
    unittest.main()
