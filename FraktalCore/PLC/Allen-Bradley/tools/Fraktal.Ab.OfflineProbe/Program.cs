using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string usage =
    "Usage: Fraktal.Ab.OfflineProbe <project.ACD|L5K|L5X> [--export <new-file.ACD|L5X>]\n" +
    "       Fraktal.Ab.OfflineProbe --build <project.ACD|L5K|L5X>\n" +
    "       Fraktal.Ab.OfflineProbe --build-readback <project.L5X> <new-export.L5X> <EchoController|PhysicalController>\n" +
    "       Fraktal.Ab.OfflineProbe --create-seed <controller> <majorRevision> <name> <seed.ACD> [--export <seed.L5X>]";

// Build mode compiles the project offline (Logix Designer v37+ only, per the
// SDK). It is still offline: no controller connection is made, the file is
// opened read-only and proved unchanged by hash, and the compiler diagnostics
// come back in the JSON evidence. This is the headless form of Studio's
// Verify and the gate a generated project must pass before a download.
if (args.Length == 4 && args[0] == "--build-readback")
{
    var sourcePath = Path.GetFullPath(args[1]);
    var outputPath = Path.GetFullPath(args[2]);
    if (!File.Exists(sourcePath) ||
        !Path.GetExtension(sourcePath).Equals(".L5X", StringComparison.OrdinalIgnoreCase) ||
        !Path.GetExtension(outputPath).Equals(".L5X", StringComparison.OrdinalIgnoreCase) ||
        sourcePath.Equals(outputPath, StringComparison.OrdinalIgnoreCase) ||
        File.Exists(outputPath))
    {
        Console.Error.WriteLine("Build/read-back needs an existing L5X and a different, new L5X output.");
        return 2;
    }
    if (args[3] is not ("EchoController" or "PhysicalController"))
    {
        Console.Error.WriteLine("Build/read-back supports only offline EchoController or PhysicalController targets.");
        return 2;
    }

    var sourceHash = Hash(sourcePath);
    var target = Enum.Parse<LogixProject.RequestedBuildTarget>(args[3]);
    string? diagnostic = null;
    using (var project = await LogixProject.OpenLogixProjectAsync(sourcePath, new StdOutEventLogger()))
    {
        try
        {
            await project.BuildAsync(target, CancellationToken.None);
        }
        catch (OperationFailedException error)
        {
            // Preserve rejected compiler cases too. A gate must distinguish a
            // semantic rejection from activation/service failure in the log.
            diagnostic = error.Message;
        }
        await project.SaveAsAsync(outputPath, true);
    }
    var unchanged = sourceHash.Equals(Hash(sourcePath), StringComparison.Ordinal);
    Console.WriteLine(JsonSerializer.Serialize(new
    {
        Schema = "fraktal.ab.offline-probe-build-readback",
        SchemaVersion = 1,
        Input = sourcePath,
        InputSha256 = sourceHash,
        InputUnchanged = unchanged,
        BuildTarget = args[3],
        BuildAccepted = diagnostic is null,
        Diagnostic = diagnostic,
        Export = outputPath,
        ExportSha256 = Hash(outputPath),
    }, new JsonSerializerOptions { WriteIndented = true }));
    return unchanged && diagnostic is null ? 0 : 1;
}

if (args.Length is 2 or 3 && args[0] == "--build")
{
    var buildPath = Path.GetFullPath(args[1]);
    if (!File.Exists(buildPath))
    {
        Console.Error.WriteLine($"Project does not exist: {buildPath}");
        return 2;
    }

    var buildHashBefore = Hash(buildPath);

    using (var project = await LogixProject.OpenLogixProjectAsync(buildPath, new StdOutEventLogger()))
    {
        // Compiler diagnostics stream through the event logger to stdout;
        // BuildAsync itself returns void. A build that fails still throws or
        // logs - the hash guard below proves only that the FILE is untouched.
        var target = LogixProject.RequestedBuildTarget.DefaultTarget;
        if (args.Length == 3)
        {
            target = (LogixProject.RequestedBuildTarget)Enum.Parse(
                typeof(LogixProject.RequestedBuildTarget), args[2], true);
        }
        await project.BuildAsync(target, CancellationToken.None);
    }

    var buildHashAfter = Hash(buildPath);
    if (!buildHashBefore.Equals(buildHashAfter, StringComparison.Ordinal))
    {
        Console.Error.WriteLine("The input project changed during the offline build.");
        return 1;
    }

    var buildEvidence = new
    {
        Schema = "fraktal.ab.offline-probe-build",
        SchemaVersion = 1,
        Input = buildPath,
        InputSha256 = buildHashAfter,
        InputUnchanged = true,
        BuildTarget = args.Length == 3 ? args[2] : "DefaultTarget",
        Note = "compiler diagnostics stream on stdout via the event logger",
    };
    Console.WriteLine(JsonSerializer.Serialize(buildEvidence, new JsonSerializerOptions { WriteIndented = true }));
    return 0;
}

// Seed mode makes the empty controller skeleton every fixture generator starts
// from reproducible from a clean checkout, instead of a hand-driven SDK example
// whose output only ever existed in a temporary directory. It is offline: it
// creates and saves a project file and never touches a controller.
if (args.Length > 0 && args[0] == "--create-seed")
{
    if (args.Length is not (5 or 7) || (args.Length == 7 && args[5] != "--export"))
    {
        Console.Error.WriteLine(usage);
        return 2;
    }

    var seedController = args[1];
    if (!uint.TryParse(args[2], out var seedRevision))
    {
        Console.Error.WriteLine("The major revision must be an unsigned integer.");
        return 2;
    }

    var seedName = args[3];
    var seedPath = Path.GetFullPath(args[4]);
    if (!Path.GetExtension(seedPath).Equals(".ACD", StringComparison.OrdinalIgnoreCase))
    {
        Console.Error.WriteLine("The seed project must use the .ACD extension.");
        return 2;
    }

    if (File.Exists(seedPath))
    {
        Console.Error.WriteLine($"Refusing to overwrite an existing seed: {seedPath}");
        return 2;
    }

    string? seedExportPath = null;
    if (args.Length == 7)
    {
        seedExportPath = Path.GetFullPath(args[6]);
        if (!Path.GetExtension(seedExportPath).Equals(".L5X", StringComparison.OrdinalIgnoreCase))
        {
            Console.Error.WriteLine("The seed export must use the .L5X extension.");
            return 2;
        }

        if (File.Exists(seedExportPath))
        {
            Console.Error.WriteLine($"Refusing to overwrite an existing export: {seedExportPath}");
            return 2;
        }
    }

    using (var seed = await LogixProject.CreateNewProjectAsync(
               seedPath, seedRevision, seedController, seedName, [new StdOutEventLogger()]))
    {
        if (seedExportPath is not null)
        {
            await seed.SaveAsAsync(seedExportPath, true);
        }
    }

    var seedEvidence = new
    {
        Schema = "fraktal.ab.offline-probe-seed",
        SchemaVersion = 1,
        Controller = seedController,
        MajorRevision = seedRevision,
        ControllerName = seedName,
        Seed = seedPath,
        SeedSha256 = Hash(seedPath),
        Export = seedExportPath,
        ExportSha256 = seedExportPath is null ? null : Hash(seedExportPath),
    };

    Console.WriteLine(JsonSerializer.Serialize(seedEvidence, new JsonSerializerOptions { WriteIndented = true }));
    return 0;
}

if (args.Length is not (1 or 3) || (args.Length == 3 && args[1] != "--export"))
{
    Console.Error.WriteLine(usage);
    return 2;
}

var projectPath = Path.GetFullPath(args[0]);
if (!File.Exists(projectPath))
{
    Console.Error.WriteLine($"Project does not exist: {projectPath}");
    return 2;
}

var projectExtension = Path.GetExtension(projectPath);
if (!new[] { ".ACD", ".L5K", ".L5X" }.Contains(projectExtension, StringComparer.OrdinalIgnoreCase))
{
    Console.Error.WriteLine("The input must be an ACD, L5K, or L5X project.");
    return 2;
}

string? exportPath = null;
if (args.Length == 3)
{
    exportPath = Path.GetFullPath(args[2]);
    var exportExtension = Path.GetExtension(exportPath);
    if (!new[] { ".ACD", ".L5X" }.Contains(exportExtension, StringComparer.OrdinalIgnoreCase))
    {
        Console.Error.WriteLine("The export must use the .ACD or .L5X extension.");
        return 2;
    }

    if (Path.GetFullPath(exportPath).Equals(projectPath, StringComparison.OrdinalIgnoreCase))
    {
        Console.Error.WriteLine("The export path must differ from the input project.");
        return 2;
    }

    if (File.Exists(exportPath))
    {
        Console.Error.WriteLine($"Refusing to overwrite an existing export: {exportPath}");
        return 2;
    }
}

var inputHashBefore = Hash(projectPath);
string communicationsPath;

using (var project = await LogixProject.OpenLogixProjectAsync(projectPath, new StdOutEventLogger()))
{
    communicationsPath = await project.GetCommunicationsPathAsync();
    if (exportPath is not null)
    {
        await project.SaveAsAsync(exportPath, true);
    }
}

var inputHashAfter = Hash(projectPath);
if (!inputHashBefore.Equals(inputHashAfter, StringComparison.Ordinal))
{
    Console.Error.WriteLine("The input project changed during the offline probe.");
    return 1;
}

var evidence = new
{
    Schema = "fraktal.ab.offline-probe",
    SchemaVersion = 1,
    Input = projectPath,
    InputSha256 = inputHashAfter,
    CommunicationsPath = communicationsPath,
    Export = exportPath,
    ExportSha256 = exportPath is null ? null : Hash(exportPath),
    InputUnchanged = true,
};

Console.WriteLine(JsonSerializer.Serialize(evidence, new JsonSerializerOptions { WriteIndented = true }));
return 0;

static string Hash(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream));
}
