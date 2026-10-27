import SwiftUI

/// "A new version is out", with what it changes, shown when the app opens or Check for updates finds
/// one. The app already had the update machinery (checkAppUpdate / performAppUpdate); what it lacked
/// was a reason to press the button: the status line said a tag name and nothing else, and a user who
/// was working fine had no way to tell whether the new version mattered to them.
///
/// The notes come from the release body, which this project writes in both languages (see
/// docs/RELEASE-NOTES-GUIDE.md). The sheet does not try to translate them; it shows the lines that
/// match the interface language and falls back to the whole body when it cannot tell them apart.
struct UpdateSheet: View {
    @ObservedObject var m: BuildModel
    @Environment(\.dismiss) private var dismiss

    private var update: (tag: String, url: String, notes: String)? { m.appUpdate }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            VStack(alignment: .leading, spacing: 6) {
                Text(m.t("update.title"))
                    .font(.manrope(24, .heavy)).tracking(-0.5)
                Text(String(format: m.t("update.fromTo"), BuildModel.appVersion, update?.tag ?? ""))
                    .font(.manrope(13)).foregroundStyle(.secondary)
            }
            .padding(.horizontal, 28).padding(.top, 26).padding(.bottom, 18)

            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    if let notes = update?.notes, !notes.isEmpty {
                        ForEach(Array(Self.lines(notes, for: m.lang).enumerated()), id: \.offset) { _, line in
                            Text(line)
                                .font(.manrope(13))
                                .fixedSize(horizontal: false, vertical: true)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    } else {
                        Text(m.t("update.noNotes")).font(.manrope(13)).foregroundStyle(.secondary)
                    }
                }
                .padding(.horizontal, 28).padding(.bottom, 20)
            }
            .frame(maxHeight: 340)

            Divider().opacity(0.3)
            HStack(spacing: 12) {
                if let u = update {
                    Link(m.t("update.openPage"), destination: URL(string: "https://github.com/LNPANDY/NX2Apple/releases/tag/\(u.tag)")!)
                        .font(.manrope(12.5))
                }
                Spacer(minLength: 8)
                Button(m.t("update.later")) { dismiss() }
                    .buttonStyle(LauncherSecondaryButtonStyle())
                    .keyboardShortcut(.cancelAction)
                Button {
                    m.performAppUpdate()
                    dismiss()
                } label: {
                    Text(m.t("update.now")).font(.manrope(13.5, .bold)).foregroundStyle(.black)
                        .padding(.horizontal, 20).padding(.vertical, 9)
                        .background(LauncherPalette.cream, in: Capsule())
                }
                .buttonStyle(.plain)
                .disabled(m.appBusy)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.horizontal, 28).padding(.vertical, 16)
        }
        .frame(width: 560)
        .background(LauncherPalette.background)
        .preferredColorScheme(.dark)
        .tint(LauncherPalette.cream)
    }

    /// The release body's lines for one language.
    ///
    /// The notes are written to a fixed shape (docs/RELEASE-NOTES-GUIDE.md): a bilingual heading
    /// ("## 这一版做了什么 / What this release does"), then `**中文** …` and `**English** …` paragraphs,
    /// then a bullet list that interleaves the two languages one item at a time. So the language is
    /// known from the line's own marker, not from whether it happens to contain Chinese characters —
    /// the first version of this did that and gave an English reader the Chinese paragraph, because
    /// `**中文** …` contains both.
    static func lines(_ notes: String, for lang: Lang) -> [String] {
        var zh: [String] = [], en: [String] = []
        // Headings go to both lists, so "one list is empty" is not the test for a bilingual body —
        // a monolingual body with a heading fills both. Count the tagged and bulleted lines instead.
        var bilingual = 0
        for raw in notes.split(separator: "\n", omittingEmptySubsequences: false) {
            var s = raw.trimmingCharacters(in: .whitespaces)
            if s.isEmpty || s.hasPrefix("---") { continue }
            if s.hasPrefix("#") {                              // a heading: keep it once, in either list
                while s.hasPrefix("#") { s.removeFirst() }
                s = s.trimmingCharacters(in: .whitespaces)
                if !s.isEmpty { zh.append(s); en.append(s) }
                continue
            }
            // `**中文** …` / `**English** …` — the marker decides, and it is removed from the text
            if let r = s.range(of: "**中文**") {
                bilingual += 1
                zh.append(s[r.upperBound...].replacingOccurrences(of: "**", with: "").trimmingCharacters(in: .whitespaces))
            } else if let r = s.range(of: "**English**") {
                bilingual += 1
                en.append(s[r.upperBound...].replacingOccurrences(of: "**", with: "").trimmingCharacters(in: .whitespaces))
            } else {
                // A bullet or plain line: no marker, so it belongs to whichever language it is in.
                // Chinese text has Han characters; English does not. (A bullet naming a title in
                // Chinese would land in the Chinese list, which is the right place for it.)
                s = s.replacingOccurrences(of: "**", with: "")
                if s.range(of: "\u{4e00}", options: []) != nil || s.unicodeScalars.contains(where: { (0x4e00...0x9fff).contains($0.value) }) {
                    zh.append(s)
                } else { en.append(s) }
            }
        }
        // A body with no language markers at all is shown whole: splitting it would silently drop
        // half of it, which is what the first version did to a plain English body.
        if bilingual == 0 || zh.isEmpty || en.isEmpty {
            var all: [String] = []
            for raw in notes.split(separator: "\n", omittingEmptySubsequences: false) {
                var s = raw.trimmingCharacters(in: .whitespaces)
                if s.isEmpty || s.hasPrefix("---") { continue }
                while s.hasPrefix("#") { s.removeFirst() }
                s = s.replacingOccurrences(of: "**中文**", with: "").replacingOccurrences(of: "**English**", with: "")
                s = s.replacingOccurrences(of: "**", with: "").trimmingCharacters(in: .whitespaces)
                if !s.isEmpty { all.append(s) }
            }
            return all
        }
        return lang == .zh ? zh : en
    }
}
