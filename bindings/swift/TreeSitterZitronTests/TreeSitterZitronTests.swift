import XCTest
import SwiftTreeSitter
import TreeSitterZitron

final class TreeSitterZitronTests: XCTestCase {
    func testCanLoadGrammar() throws {
        let parser = Parser()
        let language = Language(language: tree_sitter_zitron())
        XCTAssertNoThrow(try parser.setLanguage(language),
                         "Error loading Zitron Parser grammar")
    }
}
