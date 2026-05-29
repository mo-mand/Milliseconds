// ============================================================
// milliseconds.dev — .NET vs Python performance benchmarks
// Project : 08 — QR code generation
// Author  : Mo Mand  |  https://milliseconds.dev
//
// QRCoder-based QR generator — replaces:
//   Python: qrcode.QRCode(error_correction=ERROR_CORRECT_M, border=0)
//
// Key differences from the Python version:
//   - QRCoder's ModuleMatrix includes a 4-module quiet zone on each side;
//     we strip it to match qrcode's border=0 output
//   - A single QRCodeGenerator instance is reused across all inputs
//   - All computation is in managed C# with zero Python object overhead
//
// Validation note:
//   ISO 18004 allows different mask pattern selection strategies. QRCoder
//   and qrcode may pick different masks (both valid), so dark-module counts
//   are compared with a 5% tolerance rather than exact equality.
// ============================================================

using QRCoder;

class QrAnalyzer
{
    // QRCoder wraps the raw matrix with a 4-module quiet zone on every side.
    // Python's qrcode with border=0 does not include this border.
    private const int QuietZone = 4;

    private readonly QRCodeGenerator _gen = new QRCodeGenerator();

    public readonly record struct Result(long DarkModules, int Size);

    // Generate a QR code for `text` and count dark modules, excluding the quiet zone.
    // Python equivalent:
    //   qr.clear(); qr.add_data(text); qr.make(fit=True)
    //   matrix = qr.get_matrix()
    //   dark = sum(cell for row in matrix for cell in row)
    public Result Analyze(string text)
    {
        var data     = _gen.CreateQrCode(text, QRCodeGenerator.ECCLevel.M);
        int fullSize = data.ModuleMatrix.Count;
        int size     = fullSize - 2 * QuietZone;

        long dark = 0;
        for (int r = QuietZone; r < fullSize - QuietZone; r++)
        {
            var row = data.ModuleMatrix[r];
            for (int c = QuietZone; c < fullSize - QuietZone; c++)
                if (row[c]) dark++;
        }

        return new Result(dark, size);
    }
}
