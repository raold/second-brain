// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "apple-brain",
    platforms: [.macOS("27.0")],
    targets: [
        .executableTarget(
            name: "brain",
            path: "Sources/brain",
            swiftSettings: [.swiftLanguageMode(.v5)],
            linkerSettings: [.linkedLibrary("sqlite3")]
        )
    ]
)
