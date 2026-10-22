import Foundation
import NaturalLanguage

/// Apple's on-device contextual embedding (NaturalLanguage), mean-pooled and L2-normalised.
final class Embedder {
    let model: NLContextualEmbedding
    var dimension: Int { model.dimension }

    init() async throws {
        guard let m = NLContextualEmbedding(language: .french) else {
            throw BrainError("NLContextualEmbedding indisponible sur ce Mac")
        }
        if !m.hasAvailableAssets {
            eprint("Téléchargement du modèle d'embedding Apple…")
            _ = try await m.requestAssets()
        }
        try m.load()
        model = m
    }

    func embed(_ text: String) -> [Float] {
        // The model reads at most 256 tokens; ~1200 characters covers a chunk.
        let t = String(text.prefix(1200))
        var sum = [Float](repeating: 0, count: model.dimension)
        guard !t.isEmpty, let r = try? model.embeddingResult(for: t, language: nil) else { return sum }
        var n: Float = 0
        r.enumerateTokenVectors(in: t.startIndex..<t.endIndex) { v, _ in
            for i in 0..<min(v.count, sum.count) { sum[i] += Float(v[i]) }
            n += 1
            return true
        }
        if n > 0 { for i in sum.indices { sum[i] /= n } }
        return sum
    }
}

enum Vec {
    static func normalize(_ v: inout [Float]) {
        var s: Float = 0
        for x in v { s += x * x }
        let n = s.squareRoot()
        if n > 0 { for i in v.indices { v[i] /= n } }
    }

    static func dot(_ a: [Float], _ b: [Float]) -> Float {
        var s: Float = 0
        for i in 0..<min(a.count, b.count) { s += a[i] * b[i] }
        return s
    }

    /// Mean-centred unit vector: removes the shared direction that makes raw
    /// contextual embeddings all look alike (cosine ≈ 0.8 for unrelated text).
    static func centered(_ v: [Float], mean: [Float]) -> [Float] {
        var c = v
        if mean.count == c.count { for i in c.indices { c[i] -= mean[i] } }
        normalize(&c)
        return c
    }
}
