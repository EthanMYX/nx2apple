"""Write half of issue triage: validate the model's JSON strictly, then add labels and post (or update) one comment.

Runs in a job with `issues: write` and no model token. The model's output is untrusted (the issue it read may have steered it), so
nothing in it is applied unless every check passes; a failed check applies nothing and fails the job. This script never closes an
issue, edits one, removes a label or touches code.

  schema      exactly {"labels": [str], "comment": str, "duplicates": [int]}
  labels      each from ALLOWED_LABELS, no repeats, at most 4; labels the repository does not have are skipped (never created)
  duplicates  at most 3 issue numbers, each a candidate that triage_prepare.py found, not the issue itself, and existing in this repository
  comment     at most 1500 characters; no @-mention, no HTML, no images, no link except github.com/LNPANDY/NX2Apple,
              github.com/seedds/nxnative (and the README, which is the first of them), no bare domain
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ALLOWED_LABELS = ['game', 'build', 'launcher', 'ios', 'mac', 'idea', 'question', 'needs-info', 'duplicate']
MAX_LABELS = 4
MAX_DUPLICATES = 3
MAX_COMMENT = 1500
MAX_RAW = 20000
MARKER = '<!-- nx2apple-triage -->'
FOOTER = '_Automated first look (AI-assisted, from the issue form and the log). A maintainer will follow up._'

ALLOWED_URL = re.compile(r'https://github\.com/(?:LNPANDY/NX2Apple|seedds/nxnative)(?:[/#?][^\s]*)?', re.I)
ALLOWED_BARE = re.compile(r'github\.com/(?:LNPANDY/NX2Apple|seedds/nxnative)(?![\w.-])(?:[/#?][^\s]*)?', re.I)
ANY_URL = re.compile(r'(?:[a-z][a-z0-9+.-]*://|www\.|mailto:|javascript:|data:)\S*', re.I)
TLD = re.compile(r'\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:com|net|org|io|dev|xyz|ru|cn|info|biz|example|test)\b', re.I)
TRAIL = ')]>.,;:!*_\'"`'


class Invalid(ValueError):
    pass


def parse_output(raw):
    """The model's text as the JSON object it must be: raw JSON, or one fenced block that holds it."""
    if len(raw) > MAX_RAW:
        raise Invalid('output too long')
    text = raw.strip()
    m = re.fullmatch(r'```(?:json)?\s*\n(.*)\n```', text, re.S)
    if m:
        text = m[1].strip()
    try:
        obj = json.loads(text)
    except ValueError as e:
        raise Invalid(f'not JSON: {e}')
    if not isinstance(obj, dict) or set(obj) != {'labels', 'comment', 'duplicates'}:
        raise Invalid('keys must be exactly labels, comment, duplicates')
    return obj


def check_comment(text):
    if not isinstance(text, str):
        raise Invalid('comment is not a string')
    if len(text) > MAX_COMMENT:
        raise Invalid('comment too long')
    if re.search(r'[\x00-\x08\x0b-\x1f\x7f]', text):
        raise Invalid('control characters in comment')
    if re.search(r'@\w', text):
        raise Invalid('@-mention in comment')
    if re.search(r'<[A-Za-z/!?]', text) or '![' in text:
        raise Invalid('HTML or image in comment')
    for m in ANY_URL.finditer(text):
        url = m.group(0).rstrip(TRAIL)
        if not ALLOWED_URL.fullmatch(url):
            raise Invalid(f'link not allowed: {url[:60]}')
    for target in re.findall(r'\]\(([^)\s]*)', text):
        if not (target.startswith('#') or ALLOWED_URL.fullmatch(target)):
            raise Invalid(f'link target not allowed: {target[:60]}')
    rest = ALLOWED_BARE.sub(' ', ALLOWED_URL.sub(' ', text))
    if re.search(r'[\w.-]+/[\w.-]+#\d+', rest):
        raise Invalid('cross-repository reference in comment')
    m = TLD.search(rest)
    if m:
        raise Invalid(f'domain in comment: {m.group(0)[:60]}')


def validate(raw, issue, candidates, exists):
    """Return (labels, comment, duplicates) or raise Invalid. `candidates`: the numbers triage_prepare found; `exists(n)`: the issue is in this repository."""
    obj = parse_output(raw)
    labels, comment, dups = obj['labels'], obj['comment'], obj['duplicates']
    if not isinstance(labels, list) or not all(isinstance(l, str) for l in labels):
        raise Invalid('labels must be a list of strings')
    if len(set(labels)) != len(labels) or len(labels) > MAX_LABELS:
        raise Invalid('labels repeat or exceed the limit')
    bad = [l for l in labels if l not in ALLOWED_LABELS]
    if bad:
        raise Invalid(f'labels not on the allow-list: {bad[:3]}')
    if not isinstance(dups, list) or any(type(n) is not int for n in dups):
        raise Invalid('duplicates must be a list of integers')
    if len(set(dups)) != len(dups) or len(dups) > MAX_DUPLICATES:
        raise Invalid('duplicates repeat or exceed the limit')
    for n in dups:
        if n == issue or n not in candidates or not exists(n):
            raise Invalid(f'duplicate #{n} is not a known other issue of this repository')
    check_comment(comment)
    if not dups and 'duplicate' in labels:
        labels = [l for l in labels if l != 'duplicate']   # a label without a target is dropped, not applied
    return labels, comment, dups


def build_comment(comment, dups):
    parts = [comment.strip()] if comment.strip() else []
    if dups:
        parts.append('Possibly the same problem as: ' + ', '.join(f'#{n}' for n in dups))
    if not parts:
        return ''
    return '\n\n'.join(parts + [FOOTER, MARKER])


def gh(*args, check=True):
    r = subprocess.run(['gh', *args], capture_output=True, text=True, timeout=60)
    if check and r.returncode:
        raise SystemExit(f'gh {args[0]} failed: {r.stderr.strip()[:300]}')
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', required=True)
    ap.add_argument('--issue', type=int, required=True)
    ap.add_argument('--input', required=True, help='input.json of triage_prepare.py')
    ap.add_argument('--result', required=True, help="the model's output")
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args(argv)

    data = json.loads(Path(a.input).read_text())
    cands = {c['number'] for c in data['duplicate_candidates']}
    exists = lambda n: gh('api', f'repos/{a.repo}/issues/{n}', check=False).returncode == 0
    try:
        labels, comment, dups = validate(Path(a.result).read_text(encoding='utf-8', errors='replace'), a.issue, cands, exists)
    except Invalid as e:
        print(f'::error::triage output rejected, nothing applied: {e}')
        return 1
    body = build_comment(comment, dups)

    have = {l['name'] for l in json.loads(gh('label', 'list', '-R', a.repo, '--limit', '200', '--json', 'name').stdout)}
    use = [l for l in labels if l in have]
    for l in labels:
        if l not in have:
            print(f'::notice::label {l!r} does not exist in {a.repo}, skipped')
    print(f'labels: {use}\nduplicates: {dups}\ncomment:\n{body}')
    if a.dry_run:
        return 0
    if use:
        gh('issue', 'edit', str(a.issue), '-R', a.repo, '--add-label', ','.join(use))
    if body:
        old = gh('api', f'repos/{a.repo}/issues/{a.issue}/comments', '--paginate', '--jq',
                 '.[] | select(.user.type == "Bot" and (.body | contains("%s"))) | .id' % MARKER).stdout.split()
        if old:   # a re-run updates the earlier comment: one comment per issue
            gh('api', '-X', 'PATCH', f'repos/{a.repo}/issues/comments/{old[0]}', '-f', f'body={body}')
        else:
            gh('issue', 'comment', str(a.issue), '-R', a.repo, '--body', body)
    return 0


if __name__ == '__main__':
    sys.exit(main())
