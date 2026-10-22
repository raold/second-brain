import Foundation
import FoundationModels

@Generable
struct SearchKeywords {
    @Guide(description: "Les notions clés de la question et leurs synonymes, en français (un ou deux mots chacun)", .count(3...6))
    var francais: [String]
    @Guide(description: "The same key notions translated into English (one or two words each)", .count(3...6))
    var english: [String]
}

/// Retrieval-augmented answers from Apple Intelligence's on-device model.
struct Assistant {
    let searcher: Searcher
    static let contextBudget = 5200   // tokens of excerpts; the model's window is 8192

    static func checkModel() throws {
        switch SystemLanguageModel.default.availability {
        case .available: return
        case .unavailable(.appleIntelligenceNotEnabled):
            throw BrainError("Apple Intelligence est désactivé : Réglages Système › Apple Intelligence et Siri.")
        case .unavailable(.modelNotReady):
            throw BrainError("Le modèle Apple Intelligence se télécharge encore, réessaie dans quelques minutes.")
        case .unavailable(let r):
            throw BrainError("Apple Intelligence indisponible (\(r)).")
        }
    }

    static func model(permissive: Bool) -> SystemLanguageModel {
        permissive ? SystemLanguageModel(guardrails: .permissiveContentTransformations) : .default
    }

    /// Asks the model for extra search terms, so "date limite" also matches "avant le 10/12".
    func expand(_ question: String) async -> [String] {
        // Notes mix French and English (e.g. TDAH / ADHD), so ask for both languages.
        let s = LanguageModelSession(instructions: "Tu extrais les notions clés d'une question pour une recherche dans des notes. Ne réponds pas à la question.")
        guard let r = try? await s.respond(to: "Question : \(question)", generating: SearchKeywords.self,
                                           options: GenerationOptions(temperature: 0)) else { return [] }
        return r.content.francais + r.content.english
    }

    struct Answer: Codable {
        var answer: String
        var sources: [Hit]
    }

    func ask(_ question: String, expand doExpand: Bool = true, stream: ((String) -> Void)? = nil) async throws -> Answer {
        try Self.checkModel()
        let extra = doExpand ? await expand(question) : []
        if !extra.isEmpty { eprint("🔎 \(extra.joined(separator: ", "))") }
        let hits = try searcher.search(question + " " + extra.joined(separator: " "), extraTerms: extra, limit: 40)

        // Pack as many excerpts as fit the context budget, best first, at most 3 per file.
        var used: [Hit] = []
        var perFile: [String: Int] = [:]
        var block = ""
        for h in hits where perFile[h.path, default: 0] < 3 {
            perFile[h.path, default: 0] += 1
            let label = h.heading.isEmpty ? h.path : "\(h.path) › \(h.heading)"
            let piece = "[\(used.count + 1)] \(label)\n\(h.text)\n\n"
            let n = (try? await SystemLanguageModel.default.tokenCount(for: Prompt(block + piece))) ?? (block + piece).count / 3
            if n > Self.contextBudget { if used.isEmpty { continue } else { break } }
            block += piece
            used.append(h)
        }

        let instructions = """
        Tu es l'assistant du Second Brain (coffre Obsidian) de l'utilisateur.
        Réponds en français, uniquement à partir des EXTRAITS fournis. N'invente rien.
        Si les extraits ne contiennent pas la réponse, dis-le clairement et indique les notes les plus proches.
        Cite tes sources avec leur numéro entre crochets, par exemple [2]. Sois concis et précis (dates, chiffres, noms).
        """
        let prompt = "EXTRAITS :\n\n\(block)QUESTION : \(question)"
        let answer: String
        do {
            answer = try await respond(prompt, instructions: instructions, permissive: false, stream: stream)
        } catch where Self.isGuardrail(error) {
            // Health notes (ADHD, anxiety…) can trip the default filter; retry in the permissive mode.
            answer = try await respond(prompt, instructions: instructions, permissive: true, stream: stream)
        }
        return Answer(answer: answer, sources: used)
    }

    static func isGuardrail(_ error: Error) -> Bool {
        if let e = error as? LanguageModelError, case .guardrailViolation = e { return true }
        if let e = error as? LanguageModelSession.GenerationError, case .guardrailViolation = e { return true }
        return false
    }

    private func respond(_ prompt: String, instructions: String, permissive: Bool,
                         stream: ((String) -> Void)?) async throws -> String {
        let session = LanguageModelSession(model: Self.model(permissive: permissive), instructions: instructions)
        let opts = GenerationOptions(temperature: 0.2, maximumResponseTokens: 900)
        guard let stream else { return try await session.respond(to: prompt, options: opts).content }
        var printed = ""
        for try await snap in session.streamResponse(to: prompt, options: opts) {
            let s = snap.content
            if s.hasPrefix(printed) { stream(String(s.dropFirst(printed.count))) } else { stream("\n" + s) }
            printed = s
        }
        return printed
    }
}
