import Foundation
import SQLite3

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

/// Minimal SQLite wrapper: files, chunks (+ embedding blob) and an FTS5 mirror.
final class Store {
    private var db: OpaquePointer?

    init(_ url: URL = Config.dbURL) throws {
        guard sqlite3_open(url.path, &db) == SQLITE_OK else { throw BrainError("cannot open \(url.path)") }
        sqlite3_busy_timeout(db, 5000)
        try exec("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS files(id INTEGER PRIMARY KEY, path TEXT UNIQUE, mtime REAL, size INTEGER, kind TEXT);
        CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, file_id INTEGER, ord INTEGER, heading TEXT, text TEXT, vec BLOB);
        CREATE INDEX IF NOT EXISTS chunks_file ON chunks(file_id);
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(title, path, heading, text, tokenize='unicode61 remove_diacritics 2');
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value BLOB);
        """)
    }

    deinit { sqlite3_close(db) }

    func exec(_ sql: String) throws {
        var err: UnsafeMutablePointer<CChar>?
        if sqlite3_exec(db, sql, nil, nil, &err) != SQLITE_OK {
            let msg = err.map { String(cString: $0) } ?? "?"
            sqlite3_free(err)
            throw BrainError("sqlite: \(msg)")
        }
    }

    /// Runs `sql` with positional bindings, calling `row` for each result row.
    func query(_ sql: String, _ args: [Any?] = [], row: ((Row) -> Void)? = nil) throws {
        var st: OpaquePointer?
        guard sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK else {
            throw BrainError("sqlite prepare: \(String(cString: sqlite3_errmsg(db))) — \(sql)")
        }
        defer { sqlite3_finalize(st) }
        for (i, a) in args.enumerated() {
            let idx = Int32(i + 1)
            switch a {
            case nil: sqlite3_bind_null(st, idx)
            case let v as Int: sqlite3_bind_int64(st, idx, Int64(v))
            case let v as Int64: sqlite3_bind_int64(st, idx, v)
            case let v as Double: sqlite3_bind_double(st, idx, v)
            case let v as String: sqlite3_bind_text(st, idx, v, -1, SQLITE_TRANSIENT)
            case let v as Data:
                _ = v.withUnsafeBytes { sqlite3_bind_blob(st, idx, $0.baseAddress, Int32(v.count), SQLITE_TRANSIENT) }
            default: throw BrainError("unsupported binding \(String(describing: a))")
            }
        }
        while true {
            let rc = sqlite3_step(st)
            if rc == SQLITE_ROW { row?(Row(st: st)) } else if rc == SQLITE_DONE { break } else {
                throw BrainError("sqlite step: \(String(cString: sqlite3_errmsg(db)))")
            }
        }
    }

    var lastInsertId: Int64 { sqlite3_last_insert_rowid(db) }

    struct Row {
        let st: OpaquePointer?
        func int(_ i: Int32) -> Int64 { sqlite3_column_int64(st, i) }
        func double(_ i: Int32) -> Double { sqlite3_column_double(st, i) }
        func string(_ i: Int32) -> String {
            guard let c = sqlite3_column_text(st, i) else { return "" }
            return String(cString: c)
        }
        func data(_ i: Int32) -> Data {
            guard let p = sqlite3_column_blob(st, i) else { return Data() }
            return Data(bytes: p, count: Int(sqlite3_column_bytes(st, i)))
        }
    }

    func transaction(_ body: () throws -> Void) throws {
        try exec("BEGIN")
        do { try body(); try exec("COMMIT") } catch { try? exec("ROLLBACK"); throw error }
    }

    func deleteFile(id: Int64) throws {
        try query("DELETE FROM chunks_fts WHERE rowid IN (SELECT id FROM chunks WHERE file_id=?)", [id])
        try query("DELETE FROM chunks WHERE file_id=?", [id])
        try query("DELETE FROM files WHERE id=?", [id])
    }

    func setMeta(_ key: String, _ value: Data) throws {
        try query("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", [key, value])
    }

    func meta(_ key: String) throws -> Data? {
        var out: Data?
        try query("SELECT value FROM meta WHERE key=?", [key]) { out = $0.data(0) }
        return out
    }
}

extension Array where Element == Float {
    var data: Data { withUnsafeBufferPointer { Data(buffer: $0) } }
    init(data: Data) {
        self = data.withUnsafeBytes { Array($0.bindMemory(to: Float.self)) }
    }
}
