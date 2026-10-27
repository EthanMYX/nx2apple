import XCTest
@testable import NSPortBuilder

/// Launch options beyond the app's own list: the basic / advanced split.
final class LaunchOptionsTests: XCTestCase {
    private var temporary: URL!

    override func setUpWithError() throws {
        temporary = FileManager.default.temporaryDirectory.appendingPathComponent("nxnative-launch-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: temporary, withIntermediateDirectories: true)
    }

    override func tearDownWithError() throws { try FileManager.default.removeItem(at: temporary) }

    /// A Mac app with a launcher.json of the given rows.
    private func app(_ rows: String) throws -> String {
        let app = temporary.appendingPathComponent("Game.app")
        let dm = app.appendingPathComponent("Contents/Resources/dm")
        try FileManager.default.createDirectory(at: dm, withIntermediateDirectories: true)
        try #"{"game": "01007EF00011E000", "settings": [\#(rows)]}"#.write(to: dm.appendingPathComponent("launcher.json"), atomically: true, encoding: .utf8)
        return app.path
    }

    private let scale = #"{"env": "DM_RENDER_SCALE", "kind": "range", "label": "Render scale", "note": "", "default": "1.0", "section": "Game", "min": 0.5, "max": 1.0, "step": 0.05}"#
    private let hud = #"{"env": "DM_METAL_HUD", "kind": "toggle", "label": "Metal HUD", "note": "", "default": "0", "section": "Performance", "on": "1", "off": "0"}"#

    func testBasicRowsFirstTheRestAdvancedUnlessTheListSaysOtherwise() throws {
        let list = try XCTUnwrap(LaunchSetting.read(app: try app([scale, hud].joined(separator: ","))))
        XCTAssertEqual(list.filter(\.isBasic).map(\.env), ["DM_RENDER_SCALE"])
        XCTAssertEqual(list.filter { !$0.isBasic }.map(\.env), ["DM_METAL_HUD"])
        let leveled = hud.replacingOccurrences(of: #""off": "0"}"#, with: #""off": "0", "level": "basic"}"#)
        XCTAssertTrue(try XCTUnwrap(LaunchSetting.read(app: try app(leveled))).first!.isBasic, "a level in launcher.json (seedds/nxnative#399) wins over the default split")
    }
}
