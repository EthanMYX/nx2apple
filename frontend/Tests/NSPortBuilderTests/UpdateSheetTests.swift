import XCTest
@testable import NSPortBuilder

/// The update sheet's bilingual split (UpdateSheet.lines): the release bodies follow
/// docs/RELEASE-NOTES-GUIDE.md — a bilingual heading, `**中文** …` / `**English** …` paragraphs, then
/// bullets that interleave. A Chinese reader must not get the English paragraph and vice versa.
final class UpdateSheetTests: XCTestCase {
    private let body = """
    ## 这一版做了什么 / What this release does

    **中文** 游戏数据现在打成一个 `romfs.img`，拷到手机上快得多。

    **English** Game data is now one `romfs.img`, which copies to a phone far faster.

    ## 修复 / Fixes

    - iOS 构建修好了：两处宏未定义。
    - The iOS build is fixed: two macros were left undefined.
    """

    func testChineseReaderGetsTheChineseParagraphNotTheEnglishOne() {
        let zh = UpdateSheet.lines(body, for: .zh)
        XCTAssertTrue(zh.contains { $0.contains("拷到手机上快得多") })
        XCTAssertFalse(zh.contains { $0.contains("copies to a phone far faster") },
                       "the English paragraph must not reach a Chinese reader: \(zh)")
    }

    func testEnglishReaderGetsTheEnglishParagraphNotTheChineseOne() {
        let en = UpdateSheet.lines(body, for: .en)
        XCTAssertTrue(en.contains { $0.contains("copies to a phone far faster") })
        XCTAssertFalse(en.contains { $0.contains("拷到手机上快得多") })
    }

    func testTheHeadingAppearsInBoth() {
        for lang in [Lang.zh, Lang.en] {
            XCTAssertTrue(UpdateSheet.lines(body, for: lang).contains { $0.contains("这一版做了什么") }, "\(lang)")
        }
    }

    func testBulletsGoToTheirOwnLanguage() {
        let zh = UpdateSheet.lines(body, for: .zh)
        let en = UpdateSheet.lines(body, for: .en)
        XCTAssertTrue(zh.contains { $0.hasPrefix("- iOS 构建修好了") })
        XCTAssertFalse(zh.contains { $0.hasPrefix("- The iOS build is fixed") })
        XCTAssertTrue(en.contains { $0.hasPrefix("- The iOS build is fixed") })
    }

    func testAMonolingualBodyComesThroughWhole() {
        let one = "## What changed\n\n- One thing.\n- Another thing."
        XCTAssertEqual(UpdateSheet.lines(one, for: .zh), ["What changed", "- One thing.", "- Another thing."])
    }

    func testMarkdownMarksAreStripped() {
        let bold = "**中文** 见 **NX2Apple** 的设置。"
        XCTAssertEqual(UpdateSheet.lines(bold, for: .zh), ["见 NX2Apple 的设置。"])
    }
}
