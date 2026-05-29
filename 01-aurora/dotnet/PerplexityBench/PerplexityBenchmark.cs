// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 01 — Perplexity evaluation (Aurora / NLP)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Four implementations of the perplexity pipeline — replaces:
//   Python: numpy / torch softmax + cross-entropy
//
// The four variants demonstrate the .NET SIMD progression:
//   A. Scalar      — pure C# loops, no SIMD
//   B. FusedSpan   — Span<T> slicing, same math, better cache locality
//   C. TensorPrim  — TensorPrimitives.SoftMax (AVX-512 SIMD)
//   D. LogSoftmax  — fused LogSumExp avoids materialising full softmax;
//                    uses Max + Subtract + Exp + Sum — all SIMD in .NET 10
//
// All four produce identical perplexity (float32 precision).
// ============================================================

using System.Numerics.Tensors;

static class PerplexityBenchmark
{
    // Warm up the JIT and CPU caches before timing.
    public static void WarmUp(float[] logits, int[] targets, int vocab)
    {
        var subL = logits.AsSpan(0, Math.Min(vocab * 100, logits.Length)).ToArray();
        var subT = targets.AsSpan(0, Math.Min(100, targets.Length)).ToArray();
        for (int i = 0; i < 3; i++)
        {
            _ = Scalar(subL, subT, vocab);
            _ = TensorPrimitives(subL, subT, vocab);
            _ = LogSoftmaxFused(subL, subT, vocab);
        }
    }

    // Variant A: pure scalar — equivalent to a naive Python loop (no numpy).
    // Numerically stable: subtract max before exp (same as torch.log_softmax).
    public static double Scalar(float[] logits, int[] targets, int vocab)
    {
        double sumNll = 0.0;
        int n = targets.Length;

        for (int t = 0; t < n; t++)
        {
            long off = (long)t * vocab;
            float max = logits[off];
            for (int i = 1; i < vocab; i++)
                if (logits[off + i] > max) max = logits[off + i];

            double sumExp = 0.0;
            for (int i = 0; i < vocab; i++)
                sumExp += Math.Exp(logits[off + i] - max);

            sumNll += -(logits[off + targets[t]] - max - Math.Log(sumExp));
        }
        return Math.Exp(sumNll / n);
    }

    // Variant B: Span<T> row slicing — same math as A, better cache locality.
    // Python equivalent: logits[t] — numpy already does row views without copy.
    public static double FusedSpan(float[] logits, int[] targets, int vocab)
    {
        double sumNll = 0.0;
        int n = targets.Length;
        var span = logits.AsSpan();

        for (int t = 0; t < n; t++)
        {
            var row = span.Slice(t * vocab, vocab);
            float max = row[0];
            for (int i = 1; i < row.Length; i++)
                if (row[i] > max) max = row[i];

            double sumExp = 0.0;
            for (int i = 0; i < row.Length; i++)
                sumExp += Math.Exp(row[i] - max);

            sumNll += -(row[targets[t]] - max - Math.Log(sumExp));
        }
        return Math.Exp(sumNll / n);
    }

    // Variant C: TensorPrimitives.SoftMax — SIMD-accelerated.
    // Python equivalent: probs = torch.softmax(logits[t], dim=0)
    public static double TensorPrimitives(float[] logits, int[] targets, int vocab)
    {
        double sumNll = 0.0;
        int n = targets.Length;
        var probs = new float[vocab];

        for (int t = 0; t < n; t++)
        {
            System.Numerics.Tensors.TensorPrimitives.SoftMax<float>(logits.AsSpan(t * vocab, vocab), probs);
            sumNll += -Math.Log(Math.Max(probs[targets[t]], 1e-30f));
        }
        return Math.Exp(sumNll / n);
    }

    // Variant D: Fused LogSumExp — avoids materialising the full softmax vector.
    // Uses the identity: log p[i] = x[i] - max - log(sum exp(x_j - max))
    // Max, Subtract, Exp, Sum are each SIMD fused in .NET 10 TensorPrimitives.
    // Python equivalent: torch.nn.functional.log_softmax(logits[t], dim=0)[targets[t]]
    public static double LogSoftmaxFused(float[] logits, int[] targets, int vocab)
    {
        double sumNll = 0.0;
        int n = targets.Length;
        var shifted = new float[vocab];

        for (int t = 0; t < n; t++)
        {
            var row  = logits.AsSpan(t * vocab, vocab);
            float max = System.Numerics.Tensors.TensorPrimitives.Max<float>(row);
            System.Numerics.Tensors.TensorPrimitives.Subtract<float>(row, max, shifted);
            System.Numerics.Tensors.TensorPrimitives.Exp<float>(shifted, shifted);
            float sumExp = System.Numerics.Tensors.TensorPrimitives.Sum<float>(shifted);
            sumNll += -((row[targets[t]] - max) - Math.Log(sumExp));
        }
        return Math.Exp(sumNll / n);
    }

    // ---- File loaders for real logits/targets from binary files ----

    public static float[] LoadFloat32(string path)
    {
        using var fs = File.OpenRead(path);
        var arr = new float[fs.Length / 4];
        var buf = new byte[1 << 20];
        long pos = 0;
        int read;
        while ((read = fs.Read(buf)) > 0)
        {
            Buffer.BlockCopy(buf, 0, arr, (int)(pos * 4), read);
            pos += read / 4;
        }
        return arr;
    }

    public static int[] LoadInt32(string path)
    {
        using var fs = File.OpenRead(path);
        var arr = new int[fs.Length / 4];
        var buf = new byte[1 << 20];
        long pos = 0;
        int read;
        while ((read = fs.Read(buf)) > 0)
        {
            Buffer.BlockCopy(buf, 0, arr, (int)(pos * 4), read);
            pos += read / 4;
        }
        return arr;
    }
}
