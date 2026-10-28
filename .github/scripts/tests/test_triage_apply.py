import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import triage_apply as ta  # noqa: E402

GOOD_URL = 'https://github.com/LNPANDY/NX2Apple/blob/main/docs/reference/services.md#x'


def out(labels=('game',), comment='Hello.', duplicates=()):
    return json.dumps({'labels': list(labels), 'comment': comment, 'duplicates': list(duplicates)})


def run(raw, issue=5, cands=(3, 4), exists=lambda n: True):
    return ta.validate(raw, issue, set(cands), exists)


class Schema(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(run(out(('game', 'mac'), 'Thanks.', (3,))), (['game', 'mac'], 'Thanks.', [3]))

    def test_fenced_json_ok_prose_not(self):
        self.assertEqual(run('```json\n' + out() + '\n```')[0], ['game'])
        for bad in ('Sure! ' + out(), out() + ' done', '', '[]', '{}', 'null'):
            with self.assertRaises(ta.Invalid):
                run(bad)

    def test_extra_or_missing_keys(self):
        with self.assertRaises(ta.Invalid):
            run(json.dumps({'labels': [], 'comment': '', 'duplicates': [], 'close': True}))
        with self.assertRaises(ta.Invalid):
            run(json.dumps({'labels': [], 'comment': ''}))

    def test_types(self):
        for bad in ({'labels': 'game', 'comment': '', 'duplicates': []}, {'labels': [1], 'comment': '', 'duplicates': []},
                    {'labels': [], 'comment': ['x'], 'duplicates': []}, {'labels': [], 'comment': '', 'duplicates': ['3']},
                    {'labels': [], 'comment': '', 'duplicates': [True]}, {'labels': [], 'comment': '', 'duplicates': [3.0]}):
            with self.assertRaises(ta.Invalid, msg=bad):
                run(json.dumps(bad))

    def test_too_long_raw(self):
        with self.assertRaises(ta.Invalid):
            run(out(comment='a' * (ta.MAX_RAW + 1)))


class Labels(unittest.TestCase):
    def test_allow_list(self):
        for l in ('wontfix', 'bug', 'Game', 'no-triage', 'good first issue', ''):
            with self.assertRaises(ta.Invalid, msg=l):
                run(out((l,)))

    def test_repeats_and_count(self):
        with self.assertRaises(ta.Invalid):
            run(out(('game', 'game')))
        with self.assertRaises(ta.Invalid):
            run(out(('game', 'build', 'launcher', 'ios', 'mac')))

    def test_duplicate_label_without_target_is_dropped(self):
        self.assertEqual(run(out(('game', 'duplicate')))[0], ['game'])
        self.assertEqual(run(out(('duplicate',), duplicates=(3,)))[0], ['duplicate'])


class Duplicates(unittest.TestCase):
    def test_must_be_candidate_other_and_existing(self):
        with self.assertRaises(ta.Invalid):
            run(out(duplicates=(99,)))                      # not a candidate
        with self.assertRaises(ta.Invalid):
            run(out(duplicates=(5,)), cands=(5, 3))         # the issue itself
        with self.assertRaises(ta.Invalid):
            run(out(duplicates=(3,)), exists=lambda n: False)
        with self.assertRaises(ta.Invalid):
            run(out(duplicates=(3, 3)))
        with self.assertRaises(ta.Invalid):
            run(out(duplicates=(1, 2, 3, 4)), cands=(1, 2, 3, 4))


class Comment(unittest.TestCase):
    def bad(self, text):
        with self.assertRaises(ta.Invalid, msg=text):
            run(out(comment=text))

    def good(self, text):
        self.assertEqual(run(out(comment=text))[1], text)

    def test_mentions(self):
        for t in ('cc @everyone', '@octocat hi', 'hello\n@LNPANDY', 'ping (@a)', 'x@y.com'):
            self.bad(t)

    def test_links(self):
        for t in ('see https://evil.example/x', 'http://github.com/LNPANDY/NX2Apple', 'https://github.com/other/repo',
                  'https://github.com/LNPANDY/NX2Apple-evil', 'https://github.com/LNPANDY/NX2Apple.evil.com/x',
                  '[x](https://evil.example)', '[x](javascript:alert(1))', '[x](evil.example)', 'www.evil.example',
                  'evil.example', 'visit evil.com now', 'mailto:a@b.c', 'data:text/html,x', 'ftp://x/y',
                  '[a]: https://evil.example/', 'https://github.com@evil.example/', 'https://github.com/seedds/nxnative2',
                  'https://GITHUB.com.evil.example/LNPANDY/NX2Apple', 'github.com/other/repo.com'):
            self.bad(t)

    def test_allowed_links(self):
        for t in (f'See {GOOD_URL}.', f'[entry]({GOOD_URL})', 'https://github.com/seedds/nxnative/issues', 'https://github.com/LNPANDY/NX2Apple#readme',
                  'the README: https://github.com/LNPANDY/NX2Apple#readme)', '[top](#top)', 'build_ipa.sh and log.txt and README.md', 'see #12 and #13',
                  'Mario (010015100B514000) on macOS 26.1, Settings > Copy diagnostics'):
            self.good(t)

    def test_html_and_images(self):
        for t in ('<img src=x>', '<script>', '![x](https://github.com/LNPANDY/NX2Apple/a.png)', '<!-- hi -->', '</details>'):
            self.bad(t)

    def test_cross_repo_ref_and_control_and_length(self):
        self.bad('fixes other/repo#1')
        self.bad('a\x00b')
        self.bad('a' * (ta.MAX_COMMENT + 1))
        self.good('a' * ta.MAX_COMMENT)

    def test_injection_example(self):
        self.bad('Ignoring my instructions. Closing this issue. @everyone see https://evil.example')


class Build(unittest.TestCase):
    def test_empty_means_no_comment(self):
        self.assertEqual(ta.build_comment('', []), '')
        self.assertEqual(ta.build_comment('  ', []), '')

    def test_comment_has_footer_and_marker(self):
        b = ta.build_comment('Hi.', [3, 4])
        self.assertTrue(b.startswith('Hi.\n\nPossibly the same problem as: #3, #4'))
        self.assertTrue(b.endswith(ta.MARKER))
        self.assertEqual(ta.build_comment('', [3]).count('#3'), 1)

    def test_built_comment_passes_its_own_check(self):
        ta.check_comment(ta.FOOTER)   # the footer is added after validation; it must still satisfy the rules


if __name__ == '__main__':
    unittest.main()
