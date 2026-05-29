// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 01 — Perplexity evaluation (Aurora / NLP)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Benchmarks four .NET implementations of the same NLP pipeline
// (softmax -> cross-entropy -> mean -> exp) to show how SIMD via
// TensorPrimitives accelerates the same algorithm progressively.
//
// Python equivalent: python/perplexity.py
//   numpy: probs = np.exp(logits - logits.max(axis=1, keepdims=True))
//          probs /= probs.sum(axis=1, keepdims=True)
//          nll = -np.log(probs[np.arange(n), targets])
//          ppl = np.exp(nll.mean())
//
// Usage:
//   dotnet run -c Release                              # synthetic, GPT-2 vocab
//   dotnet run -c Release -- --vocab 128256            # Llama-3 vocab
//   dotnet run -c Release -- --tokens 1000000          # 1M tokens
//   dotnet run -c Release -- --real logits.bin targets.bin
// ============================================================

using System.Diagnostics;
using System.Numerics.Tensors;

Console.OutputEncoding = System.Text.Encoding.UTF8;

int  vocab    = ParseArg(args, "--vocab",  50257);
int  nTokens  = ParseArg(args, "--tokens", 100_000);
string? logitsPath  = GetArg(args, "--real");
string? targetsPath = args.Length >= 3 && args[0] == "--real" ? args[2] : null;

float[] logits;
int[]   targets;

if (logitsPath != null)
{
    Console.WriteLine($"Loading real logits from: {logitsPath}");
    logits   = PerplexityBenchmark.LoadFloat32(logitsPath);
    targets  = PerplexityBenchmark.LoadInt32(targetsPath ?? logitsPath.Replace("logits", "targets"));
    nTokens  = targets.Length;
    vocab    = logits.Length / nTokens;
    Console.WriteLine($"Loaded {nTokens:N0} tokens x {vocab:N0} vocab = {logits.Length:N0} float32s ({logits.Length * 4L / 1_048_576} MB)\n");
}
else
{
    Console.WriteLine("=== Generating synthetic logits ===");
    Console.WriteLine($"  Vocab size : {vocab:N0}");
    Console.WriteLine($"  Tokens     : {nTokens:N0}");
    Console.WriteLine($"  Memory     : {(long)nTokens * vocab * 4L / 1_048_576:N0} MB");
    Console.WriteLine("  Distribution: gaussian sigma=5 (matches real LLM output stats)\n");

    var sw  = Stopwatch.StartNew();
    var rng = new Random(42);
    logits  = new float[(long)nTokens * vocab];
    targets = new int[nTokens];

    // Python equivalent: logits = np.random.randn(n, vocab) * 5
    for (long i = 0; i < logits.LongLength; i++)
    {
        double u1 = 1.0 - rng.NextDouble();
        double u2 = 1.0 - rng.NextDouble();
        logits[i] = (float)(5.0 * Math.Sqrt(-2.0 * Math.Log(u1)) * Math.Cos(2.0 * Math.PI * u2));
    }
    for (int i = 0; i < nTokens; i++) targets[i] = rng.Next(vocab);
    Console.WriteLine($"Generated in {sw.Elapsed.TotalSeconds:F1}s\n");
}

// Warm-up: prime JIT and CPU caches before timing
PerplexityBenchmark.WarmUp(logits, targets, vocab);

Console.WriteLine("=== Pipeline: softmax -> log(p[target]) -> mean -> exp(NLL) ===\n");

// Python equivalent for all four: numpy computes the same pipeline in one vectorized call.
// The four .NET variants show the progression from scalar to fully SIMD code.
double pplScalar     = Bench("Scalar C#                  ", () => PerplexityBenchmark.Scalar(logits, targets, vocab));
double pplFusedSpan  = Bench("Fused Span<T>              ", () => PerplexityBenchmark.FusedSpan(logits, targets, vocab));
double pplTensorPrim = Bench("TensorPrimitives.SoftMax   ", () => PerplexityBenchmark.TensorPrimitives(logits, targets, vocab));
double pplLogSoftmax = Bench("LogSoftmax fused (.NET 10) ", () => PerplexityBenchmark.LogSoftmaxFused(logits, targets, vocab));

Console.WriteLine($"\n=== Result agreement check ===");
Console.WriteLine($"  Scalar         : PPL = {pplScalar:F4}");
Console.WriteLine($"  Fused Span     : PPL = {pplFusedSpan:F4}");
Console.WriteLine($"  TensorPrimitive: PPL = {pplTensorPrim:F4}");
Console.WriteLine($"  LogSoftmax     : PPL = {pplLogSoftmax:F4}");

// ---- Helpers ----------------------------------------------------------------

static double Bench(string label, Func<double> fn)
{
    var sw  = Stopwatch.StartNew();
    double ppl = fn();
    sw.Stop();
    Console.WriteLine($"  {label}  {sw.Elapsed.TotalSeconds,7:F2} s   ->  ppl={ppl,8:F2}");
    return ppl;
}

static int ParseArg(string[] args, string key, int def)
{
    for (int i = 0; i < args.Length - 1; i++)
        if (args[i] == key && int.TryParse(args[i + 1], out int v)) return v;
    return def;
}

static string? GetArg(string[] args, string key)
{
    for (int i = 0; i < args.Length - 1; i++)
        if (args[i] == key) return args[i + 1];
    return null;
}
