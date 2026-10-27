# Release notes: both languages, every time

Every release body is written in **Chinese first, then English**, in the same file, with the same
structure. This exists because the fork's users are mostly Chinese while the upstream project and
most contributors are not, and a release written in one language loses half of them.

## The shape

```
## 这一版做了什么 / What this release does

**中文** — one paragraph: what changed for someone who already uses the app.

**English** — the same paragraph, not a summary of it.

## 修复 / Fixes

- 中文条目。
- English entry.
- （同一件事两种语言写在相邻的两行，不分组、不重复编号）

## 已知问题 / Known issues

- （同上）

## 安装 / Install

- **macOS**: 文件名 + 一句操作说明（两种语言各一行）
- **Windows**: 发布与否、在哪里取（两种语言各一行）
```

Rules that matter more than the template:

1. **Both languages say the same thing.** Not "a translation of the headline and a summary of the
   rest" — a user reading either language must learn everything the other one learns.
2. **Never renumber or split by language.** Item 2 in Chinese is item 2 in English; a reader
   comparing two versions of the same release must not have to map lists.
3. **Say what it does for the user, not what the commit did.** "游戏数据现在是一个文件，拷到手机上
   快得多" beats "switched romfs_arc.py to romfs_image.py" — and the English line says the same.
4. **State what is NOT shipped.** If the Windows build is not in the release, both languages say so
   in the same place (a reader who only reads one must not conclude the other platform shipped).
5. **Credit contributors by name in both languages**, with the PR number.

## Where the text comes from

- `README.md` and `README.zh-CN.md` share an update-history table; a release row goes in both, the
  English one first (it is the canonical project history), then translated.
- The release body itself is written once, in both languages, and is what `gh release edit
  --notes-file` takes. Keep the file in `/tmp` while working; the release is the record.
- If a fact differs per platform (a macOS-only fix), say which platform in the same sentence in both
  languages rather than relying on the reader's inference.

## A worked example (v0.4.7)

```markdown
## 这一版做了什么 / What this release does

**中文** 游戏数据现在打成一个 `romfs.img`（一个文件，不再是几十万个碎文件），拷到手机上快得多，
也可以整个放在外置硬盘上。DLC 跟着游戏数据走，不再塞进 IPA——IPA 更小，装得更快。

**English** Game data is now one `romfs.img` (a single file, not hundreds of thousands), which
copies to a phone far faster and can live on an external drive as a whole. DLC follows the game
data instead of going into the IPA, so the IPA is smaller and installs faster.

## 修复 / Fixes

- 依赖面板的语言切换现在翻译整个界面。
- The language toggle now translates the whole interface.
```

That example is what "both languages, same structure" means in practice: the Chinese paragraph and
the English paragraph carry the same facts, and the bullet list interleaves rather than splitting
into two lists.
