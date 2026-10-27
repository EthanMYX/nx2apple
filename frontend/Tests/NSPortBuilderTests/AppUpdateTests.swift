import XCTest
@testable import NSPortBuilder

/// The update check's three outcomes must be distinguishable: a newer release with a download, a
/// newer release whose download this build cannot name, and genuinely being current.
///
/// The middle one used to be reported as "已是最新" (issue: an installed 0.4.6 said it was current
/// while 0.4.8 was out). A build that looks for one exact asset name and does not find it has not
/// established that it is up to date — it has established that it cannot tell, and saying "up to
/// date" leaves that install stuck for ever.
final class AppUpdateTests: XCTestCase {
    func testAVersionComparisonReadsTheNumbers() {
        XCTAssertTrue(BuildModel.isNewer("v0.4.8", than: "0.4.6"))
        XCTAssertTrue(BuildModel.isNewer("v0.4.10", than: "0.4.8"), "0.4.10 is newer than 0.4.8, not older")
        XCTAssertFalse(BuildModel.isNewer("v0.4.8", than: "0.4.8"))
        XCTAssertFalse(BuildModel.isNewer("v0.4.6", than: "0.4.8"))
    }

    /// The asset names this app will accept, oldest first. A release that carries any of them can
    /// update every install back to 0.4.5; one that carries none leaves those installs stuck, which
    /// is why checkAppUpdate has to say so rather than report "up to date".
    func testTheAssetNamesCoverEveryInstallThatCanStillUpdate() {
        let names = BuildModel.appAssetNames
        XCTAssertTrue(names.contains("NX2Apple-macOS-arm64.zip"), "the current name")
        XCTAssertTrue(names.contains("nxnative-macOS-arm64.zip"), "installs from before the rename to NX2Apple")
        XCTAssertTrue(names.contains("NS-Port-Builder-macOS-arm64.zip"), "installs from before the rename to nxnative")
    }
}
