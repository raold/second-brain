import Foundation

/// Minimal MCP server (JSON-RPC over stdio) so Claude Code, Claude Desktop or any MCP client
/// can search the vault, ask Apple Intelligence, and file documents through the same engine.
struct MCPServer {
    let app: App

    static let tools: [[String: Any]] = [
        tool("search_second_brain", "Recherche hybride (mots-clés + sens) dans le Second Brain. Renvoie les passages et chemins.",
             ["query": str("Ce qu'il faut chercher"), "limit": ["type": "integer", "description": "Nombre de résultats (10)"]], ["query"]),
        tool("ask_apple_intelligence", "Pose une question au modèle Apple Intelligence on-device, qui répond à partir des notes avec citations.",
             ["question": str("La question")], ["question"]),
        tool("find_files", "Trouve fichiers et dossiers par nom via Spotlight, y compris audio/vidéo.",
             ["name": str("Fragment du nom")], ["name"]),
        tool("organize_plan", "Propose (sans rien déplacer) un dossier de destination pour chaque fichier, via Apple Intelligence.",
             ["paths": ["type": "array", "items": ["type": "string"], "description": "Fichiers ou dossiers (vide = racine + Inbox)"]], []),
        tool("move_item", "Déplace un fichier/dossier dans un dossier du coffre et met à jour les liens. Annulable avec `brain undo`.",
             ["source": str("Chemin relatif au coffre ou absolu"), "destination_folder": str("Dossier relatif au coffre")],
             ["source", "destination_folder"]),
        tool("reindex", "Met à jour l'index (fichiers nouveaux ou modifiés).", [:], []),
    ]

    static func str(_ d: String) -> [String: Any] { ["type": "string", "description": d] }
    static func tool(_ name: String, _ desc: String, _ props: [String: Any], _ req: [String]) -> [String: Any] {
        ["name": name, "description": desc, "inputSchema": ["type": "object", "properties": props, "required": req]]
    }

    func run() async {
        while let line = readLine(strippingNewline: true) {
            guard let data = line.data(using: .utf8),
                  let msg = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let method = msg["method"] as? String else { continue }
            let id = msg["id"]
            let params = msg["params"] as? [String: Any] ?? [:]
            guard id != nil else { continue } // notifications
            switch method {
            case "initialize":
                reply(id, ["protocolVersion": (params["protocolVersion"] as? String) ?? "2025-06-18",
                           "capabilities": ["tools": [:]],
                           "serverInfo": ["name": "apple-brain", "version": "1.0.0"]])
            case "ping": reply(id, [:])
            case "tools/list": reply(id, ["tools": Self.tools])
            case "tools/call":
                let name = params["name"] as? String ?? ""
                let args = params["arguments"] as? [String: Any] ?? [:]
                do {
                    let text = try await call(name, args)
                    reply(id, ["content": [["type": "text", "text": text]]])
                } catch {
                    reply(id, ["content": [["type": "text", "text": "Erreur : \(error)"]], "isError": true])
                }
            default:
                send(["jsonrpc": "2.0", "id": id!, "error": ["code": -32601, "message": "unknown method \(method)"]])
            }
        }
    }

    func call(_ name: String, _ a: [String: Any]) async throws -> String {
        switch name {
        case "search_second_brain":
            let hits = try app.searcher().searchFiles(a["query"] as? String ?? "", limit: a["limit"] as? Int ?? 10)
            return App.format(hits)
        case "ask_apple_intelligence":
            let r = try await Assistant(searcher: app.searcher()).ask(a["question"] as? String ?? "")
            return r.answer + "\n\nSources :\n" + r.sources.enumerated().map { "[\($0 + 1)] \($1.path)" }.joined(separator: "\n")
        case "find_files":
            return App.spotlight(a["name"] as? String ?? "").joined(separator: "\n")
        case "organize_plan":
            let items = Organizer.sources(from: a["paths"] as? [String] ?? [])
            let plan = try await Organizer(searcher: app.searcher()).plan(items)
            return String(decoding: try JSONEncoder.pretty.encode(plan), as: UTF8.self)
        case "move_item":
            let src = a["source"] as? String ?? ""
            let url = src.hasPrefix("/") ? URL(fileURLWithPath: src) : Config.abs(src)
            let m = try Organizer.move(url, toFolder: a["destination_folder"] as? String ?? "",
                                       batch: "mcp-" + ISO8601DateFormatter().string(from: Date()))
            return "Déplacé vers \(Config.rel(URL(fileURLWithPath: m.to))). Liens mis à jour : \(m.rewritten.count)."
        case "reindex":
            let r = try await app.index()
            return "\(r.added) fichiers (ré)indexés, \(r.removed) retirés."
        default: throw BrainError("outil inconnu \(name)")
        }
    }

    func reply(_ id: Any?, _ result: [String: Any]) { send(["jsonrpc": "2.0", "id": id!, "result": result]) }

    func send(_ obj: [String: Any]) {
        guard var d = try? JSONSerialization.data(withJSONObject: obj) else { return }
        d.append(0x0A)
        FileHandle.standardOutput.write(d)
    }
}

extension JSONEncoder {
    static var pretty: JSONEncoder {
        let e = JSONEncoder()
        e.outputFormatting = [.prettyPrinted, .withoutEscapingSlashes, .sortedKeys]
        return e
    }
}
