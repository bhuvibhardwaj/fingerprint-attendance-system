using System.Text.Json;
using SecuGen.FDxSDKPro.Windows;

var command = args.Length > 0 ? args[0].ToLowerInvariant() : "help";
var options = ParseOptions(args.Skip(1));

try
{
    switch (command)
    {
        case "capture":
            ExecuteCapture(options);
            break;
        case "match":
            ExecuteMatch(options);
            break;
        case "health":
            ExecuteHealth();
            break;
        default:
            WriteJson(new { success = false, message = "Unknown command. Use capture, match, or health." });
            Environment.ExitCode = 1;
            break;
    }
}
catch (Exception ex)
{
    WriteJson(new
    {
        success = false,
        message = ex.Message,
        detail = ex.ToString()
    });
    Environment.ExitCode = 1;
}

static void ExecuteHealth()
{
    using var manager = new SGFingerPrintManager();
    var error = manager.EnumerateDevice();
    WriteJson(new
    {
        success = error == (int)SGFPMError.ERROR_NONE,
        enumerated = manager.NumberOfDevice,
        errorCode = error
    });
}

static void ExecuteCapture(Dictionary<string, string> options)
{
    var timeoutMs = ReadInt(options, "timeout", 10000);
    var minimumQuality = ReadInt(options, "quality", 50);

    using var manager = OpenManager();
    var info = new SGFPMDeviceInfoParam();
    var infoError = manager.GetDeviceInfo(info);
    if (infoError != (int)SGFPMError.ERROR_NONE)
    {
        throw new InvalidOperationException($"GetDeviceInfo failed with error {infoError}.");
    }

    var image = new byte[info.ImageWidth * info.ImageHeight];
    var template = new byte[400];
    var startedAt = Environment.TickCount64;
    int quality = 0;

    manager.EnableSmartCapture(true);
    manager.BeginGetImage();
    try
    {
        while (Environment.TickCount64 - startedAt <= timeoutMs)
        {
            var captureError = manager.GetImage(image);
            if (captureError != (int)SGFPMError.ERROR_NONE)
            {
                continue;
            }

            manager.GetImageQuality(info.ImageWidth, info.ImageHeight, image, ref quality);
            if (quality < minimumQuality)
            {
                continue;
            }

            var templateError = manager.CreateTemplate(null, image, template);
            if (templateError != (int)SGFPMError.ERROR_NONE)
            {
                throw new InvalidOperationException($"CreateTemplate failed with error {templateError}.");
            }

            WriteJson(new
            {
                success = true,
                template = Convert.ToBase64String(template),
                quality,
                imageWidth = info.ImageWidth,
                imageHeight = info.ImageHeight,
                deviceId = info.DeviceID,
                serialNumber = DecodeSerial(info.DeviceSN)
            });
            return;
        }
    }
    finally
    {
        manager.EndGetImage();
    }

    throw new TimeoutException($"Fingerprint capture timed out after {timeoutMs} ms.");
}

static void ExecuteMatch(Dictionary<string, string> options)
{
    if (!options.TryGetValue("template1", out var template1Base64) || string.IsNullOrWhiteSpace(template1Base64))
    {
        throw new ArgumentException("template1 is required.");
    }

    if (!options.TryGetValue("template2", out var template2Base64) || string.IsNullOrWhiteSpace(template2Base64))
    {
        throw new ArgumentException("template2 is required.");
    }

    var securityLevelIndex = ReadInt(options, "security-level", 3);

    using var manager = OpenManager();
    var template1 = Convert.FromBase64String(template1Base64);
    var template2 = Convert.FromBase64String(template2Base64);
    var securityLevel = (SGFPMSecurityLevel)securityLevelIndex;
    var matched = false;
    var score = 0;

    var matchError = manager.MatchTemplate(template1, template2, securityLevel, ref matched);
    if (matchError != (int)SGFPMError.ERROR_NONE)
    {
        throw new InvalidOperationException($"MatchTemplate failed with error {matchError}.");
    }

    var scoreError = manager.GetMatchingScore(template1, template2, ref score);
    if (scoreError != (int)SGFPMError.ERROR_NONE)
    {
        throw new InvalidOperationException($"GetMatchingScore failed with error {scoreError}.");
    }

    WriteJson(new
    {
        success = true,
        matched,
        score,
        securityLevel = securityLevelIndex
    });
}

static SGFingerPrintManager OpenManager()
{
    var manager = new SGFingerPrintManager();
    var initError = manager.Init(SGFPMDeviceName.DEV_AUTO);
    if (initError != (int)SGFPMError.ERROR_NONE)
    {
        manager.Dispose();
        throw new InvalidOperationException($"Init failed with error {initError}.");
    }

    var openError = manager.OpenDevice((int)SGFPMPortAddr.USB_AUTO_DETECT);
    if (openError != (int)SGFPMError.ERROR_NONE)
    {
        manager.Dispose();
        throw new InvalidOperationException($"OpenDevice failed with error {openError}.");
    }

    return manager;
}

static Dictionary<string, string> ParseOptions(IEnumerable<string> values)
{
    var parsed = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
    string? pendingKey = null;

    foreach (var value in values)
    {
        if (value.StartsWith("--"))
        {
            pendingKey = value[2..];
            if (!parsed.ContainsKey(pendingKey))
            {
                parsed[pendingKey] = string.Empty;
            }
            continue;
        }

        if (pendingKey is not null)
        {
            parsed[pendingKey] = value;
            pendingKey = null;
        }
    }

    return parsed;
}

static int ReadInt(Dictionary<string, string> options, string key, int fallback)
{
    return options.TryGetValue(key, out var value) && int.TryParse(value, out var parsed) ? parsed : fallback;
}

static string DecodeSerial(byte[] serialBytes)
{
    return System.Text.Encoding.ASCII.GetString(serialBytes).TrimEnd('\0');
}

static void WriteJson(object payload)
{
    Console.WriteLine(JsonSerializer.Serialize(payload));
}
