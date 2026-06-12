// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 12 — Image processing (resize + blur + grayscale)
// Author  : Mo Mand  |  https://milliseconds.dev
//
// Pipeline per image:
//   load JPEG → resize 256×256 (Lanczos3) → Gaussian blur (σ=2)
//   → grayscale → encode JPEG (q=85) → sum pixel values (checksum)
//
// Python equivalent: python/process.py
// ============================================================

using System.Diagnostics;
using System.Text.Json;
using SixLabors.ImageSharp;
using SixLabors.ImageSharp.Formats.Jpeg;
using SixLabors.ImageSharp.PixelFormats;
using SixLabors.ImageSharp.Processing;

bool   jsonMode  = Array.Exists(args, a => a == "--json");
string[] pathArgs = Array.FindAll(args, a => !a.StartsWith("--"));

string dataDir = pathArgs.Length > 0
    ? pathArgs[0]
    : Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "data", "images_1k");

if (!Directory.Exists(dataDir))
{
    Console.Error.WriteLine($"Directory not found: {dataDir}");
    Environment.Exit(1);
}

var files = Directory.GetFiles(dataDir, "*.jpg", SearchOption.TopDirectoryOnly);
Array.Sort(files);

if (files.Length == 0)
{
    Console.Error.WriteLine($"No .jpg files in {dataDir}");
    Environment.Exit(1);
}

// Pre-load all bytes so disk I/O doesn't skew timing
var raw = new byte[files.Length][];
for (int i = 0; i < files.Length; i++)
    raw[i] = File.ReadAllBytes(files[i]);

if (!jsonMode)
    Console.WriteLine($"Images  : {raw.Length:N0}");

var encoder = new JpegEncoder { Quality = 85 };
long checksum = 0;

var sw = Stopwatch.StartNew();

for (int i = 0; i < raw.Length; i++)
{
    using var img = Image.Load<Rgba32>(raw[i]);

    img.Mutate(ctx => ctx
        .Resize(new ResizeOptions
        {
            Size    = new Size(256, 256),
            Sampler = KnownResamplers.Lanczos3,
            Mode    = ResizeMode.Stretch,
        })
        .GaussianBlur(2f)
        .Grayscale());

    // Checksum: sum of the R channel (= G = B after grayscale)
    img.ProcessPixelRows(accessor =>
    {
        for (int y = 0; y < accessor.Height; y++)
        {
            var row = accessor.GetRowSpan(y);
            for (int x = 0; x < row.Length; x++)
                checksum += row[x].R;
        }
    });

    using var buf = new MemoryStream();
    img.Save(buf, encoder);
}

sw.Stop();
long elapsedMs = sw.ElapsedMilliseconds;

if (jsonMode)
{
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        images     = raw.Length,
        elapsed_ms = (double)elapsedMs,
        checksum,
    }));
}
else
{
    Console.WriteLine($"Elapsed : {elapsedMs:N0} ms  ({(double)elapsedMs / raw.Length:F2} ms/image)");
    Console.WriteLine($"Checksum: {checksum:N0}");
}
