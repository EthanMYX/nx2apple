import SwiftUI

@main
struct NSPortBuilderApp: App {
    var body: some Scene {
        WindowGroup("NX2Apple") { ContentView() }
            .windowStyle(.hiddenTitleBar)
            .defaultSize(width: 1280, height: 900)
            .windowResizability(.automatic)
    }
}
