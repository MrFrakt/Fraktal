using System.Security.Cryptography;
using System.Text.Json;
using RockwellAutomation.LogixDesigner;
using RockwellAutomation.LogixDesigner.Logging;

const string usage =
    "Usage: Fraktal.Ab.OfflineProbe <project.ACD|L5K|L5X> [--export <new-file.ACD|L5X>]\n" +
    "       Fraktal.Ab.OfflineProbe --create-seed <controller> <majorRevision> <name> <seed.ACD> [--export <seed.L5X>]";

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
