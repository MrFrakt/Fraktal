// Fraktal/TIA engineering driver — Part IV §5.4.
//
// One TIA Portal Openness session per invocation runs a PLAN: a text file with one
// command per line (or a single command given on the command line). Starting TIA
// Portal costs tens of seconds, so a gate that creates a project, imports sources,
// compiles and downloads does all of it in one session.
//
// Every observable decision is written to stdout as one JSON object per line, so a
// run is its own evidence record: what was imported, every compiler message, and
// every pre/post-download question TIA asked together with the answer given.
//
// Safety properties (Part IV §2.8 / AGENTS.md "controller-changing operations"):
//   * `download` refuses unless --confirm-target <ip> equals the configured CPU
//     address, so a plan can never download to a controller it did not name.
//   * Security-relevant download questions (unencrypted sensitive data, protection
//     level change, passwords) are answered only by an explicit flag; otherwise the
//     download is left to fail and the question is logged.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Security;
using System.Text;
using Microsoft.Win32;
using Siemens.Engineering;
using Siemens.Engineering.Compiler;
using Siemens.Engineering.Connection;
using Siemens.Engineering.Download;
using Siemens.Engineering.Download.Configurations;
using Siemens.Engineering.HW;
using Siemens.Engineering.HW.Features;
using Siemens.Engineering.Online;
using Siemens.Engineering.SW;
using Siemens.Engineering.SW.Blocks;
using Siemens.Engineering.SW.ExternalSources;
using Siemens.Engineering.SW.Types;

namespace Fraktal.Tia.Cli
{
    internal static class Program
    {
        private const string PortalKey = @"SOFTWARE\Siemens\Automation\Openness\20.0\PublicAPI\20.0.0.0";

        private static int Main(string[] args)
        {
            AppDomain.CurrentDomain.AssemblyResolve += ResolveOpenness;
            try
            {
                return Run(args);
            }
            catch (Exception ex)
            {
                ReportFatal(ex);
                return 2;
            }
        }

        // Main must not mention a Siemens type: the JIT would load Siemens.Engineering
        // while compiling Main, before ResolveOpenness is registered. Anything that
        // touches the API lives in methods Main calls.
        [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
        private static void ReportFatal(Exception ex)
        {
            Log.Emit("fatal", ("type", ex.GetType().FullName), ("message", Flatten(ex)));
            // Measured on V20: a NEW headless instance also passes the Openness
            // firewall; an exe whose hash is not whitelisted waits for a prompt
            // nobody answers and fails with "The operation has timed out".
            if (ex is EngineeringSecurityException && ex.Message.IndexOf("timed out", StringComparison.OrdinalIgnoreCase) >= 0)
                Log.Emit("hint", ("message", "Openness firewall: whitelist this exact build (Enable-TiaOpenness.ps1 -WhitelistExe, elevated); a rebuild changes its hash"),
                    ("exe", Assembly.GetEntryAssembly()?.Location));
        }

        // Siemens: never ship Siemens.Engineering.dll beside the tool; load it from
        // the installed Portal so the API always matches the engineering system.
        private static Assembly ResolveOpenness(object sender, ResolveEventArgs e)
        {
            var name = new AssemblyName(e.Name).Name;
            if (!name.StartsWith("Siemens.Engineering", StringComparison.Ordinal)) return null;
            using (var key = Registry.LocalMachine.OpenSubKey(PortalKey))
            {
                var path = key?.GetValue(name) as string;
                if (path == null)
                {
                    var dir = Path.GetDirectoryName((key?.GetValue("Siemens.Engineering") as string) ?? "");
                    path = Path.Combine(dir ?? "", name + ".dll");
                }
                return File.Exists(path) ? Assembly.LoadFrom(path) : null;
            }
        }

        private static int Run(string[] args)
        {
            if (args.Length == 0 || args[0] == "help" || args[0] == "--help")
            {
                Console.WriteLine(Usage);
                return 0;
            }

            var global = Args.Parse(args);
            var steps = new List<Args>();
            if (global.Command == "plan")
            {
                var file = global.Positional(0, "plan file");
                foreach (var raw in File.ReadAllLines(file))
                {
                    var line = raw.Trim();
                    if (line.Length == 0 || line.StartsWith("#", StringComparison.Ordinal)) continue;
                    // A leading '?' marks a step whose failure is recorded but does not
                    // stop the plan (e.g. import, so compile still reports every error).
                    var tolerant = line.StartsWith("?", StringComparison.Ordinal);
                    var step = Args.Parse(Args.Split(Expand(tolerant ? line.Substring(1).Trim() : line, global)));
                    step.Tolerant = tolerant;
                    steps.Add(step);
                }
            }
            else
            {
                steps.Add(global);
            }

            if (steps.All(s => s.Command == "processes"))
            {
                foreach (var p in TiaPortal.GetProcesses())
                    Log.Emit("process", ("id", p.Id), ("mode", p.Mode.ToString()), ("project", p.ProjectPath?.FullName));
                return 0;
            }

            var session = new Session(global);
            var failures = 0;
            try
            {
                foreach (var step in steps)
                {
                    Log.Emit("step", ("command", step.Command), ("args", step.ToString()));
                    int rc;
                    try
                    {
                        rc = session.Execute(step);
                    }
                    catch (Exception ex) when (step.Tolerant)
                    {
                        // A tolerant step's exception is evidence, not the end of the run.
                        Log.Emit("step-exception", ("command", step.Command), ("message", Flatten(ex)));
                        rc = 10;
                    }
                    if (rc != 0)
                    {
                        Log.Emit("step-failed", ("command", step.Command), ("rc", rc), ("continue", step.Tolerant));
                        if (!step.Tolerant) return rc;
                        failures++;
                    }
                }
                Log.Emit("plan-complete", ("steps", steps.Count), ("tolerated-failures", failures));
                return failures == 0 ? 0 : 9;
            }
            finally
            {
                session.Dispose();
            }
        }

        // ${name} in a plan line is replaced by --set name=value from the outer
        // command line, so one plan serves several targets without editing.
        private static string Expand(string line, Args global)
        {
            foreach (var kv in global.Sets)
                line = line.Replace("${" + kv.Key + "}", kv.Value);
            if (line.Contains("${"))
                throw new ArgumentException("Unresolved plan variable in: " + line);
            return line;
        }

        // Openness puts the useful text (e.g. the SCL line and error of a failed
        // source generation) in DetailMessageData, not in Message.
        internal static string Flatten(Exception ex)
        {
            var sb = new StringBuilder();
            for (var e = ex; e != null; e = e.InnerException)
            {
                if (sb.Length > 0) sb.Append(" <- ");
                sb.Append(e.GetType().Name).Append(": ").Append(e.Message);
                if (e is EngineeringException ee)
                {
                    foreach (var d in ee.DetailMessageData ?? Enumerable.Empty<ExceptionMessageData>())
                        sb.Append(" | ").Append(d.Text).Append(string.IsNullOrEmpty(d.DetailText) ? "" : " :: " + d.DetailText);
                }
            }
            return sb.ToString();
        }

        private const string Usage = @"Fraktal.Tia.Cli — TIA Portal V20 Openness driver for Fraktal/TIA (Part IV §5.4)

  Fraktal.Tia.Cli processes
  Fraktal.Tia.Cli <command> [options]          one command, one TIA session
  Fraktal.Tia.Cli plan <file> [--set k=v ...]  one command per line, one session

Session options (first command or plan line): --ui  --attach
Commands:
  create-project --dir D --name N [--replace]
  open-project   --path P.ap20
  add-device     --order ""OrderNumber:6ES7 214-1AG40-0XB0/V4.7"" --name PLC_1 [--station S]
  set-ip         --plc PLC_1 --ip 192.168.0.10 [--mask 255.255.255.0] [--item <interface>]   (Ethernet nodes only)
  import-sources --plc PLC_1 --dir D [--keep-on-error]      (*.udt, *.scl, *.db in name order)
  import-xml     --plc PLC_1 --file F.xml [--kind block|type|tags]
  delete-blocks  --plc PLC_1                                  (program blocks + types + sources)
  compile        --plc PLC_1 [--hw]
  interfaces     --plc PLC_1 [--scan]
  download       --plc PLC_1 --pc-interface ""name"" [--pc-number 1] [--target ""1 X1""]
                 --confirm-target 192.168.0.10 [--software-only]
                 [--accept-unencrypted-sensitive] [--plc-password-env VAR] [--plc-user U]
                 [--user-management keep|update|reset] [--accept-lower-protection] [--trust-plc PLC]
  online-state   --plc PLC_1 --pc-interface ""name"" [--target ""1 X1""] [--plc-user U --plc-password-env VAR]
  export         --plc PLC_1 --out D [--scl]                  SimaticML XML (+ SCL sources)
  hw-attributes  --plc PLC_1 [--filter fragment] [--probe a,b]  dump CPU device-item attributes (+ unlisted names)
  cax-export     --plc PLC_1 --out F.aml                      hardware configuration as AutomationML
  set-hw-attribute --plc PLC_1 [--item name] --attr A --value V [--type int|uint|long|bool|string]  (--type: write without reading)
  list-blocks    --plc PLC_1
  set-block-number --plc PLC_1 --name B --number N
  create-block   --plc PLC_1 --name B --lang GRAPH|SCL|FBD|LAD [--number N]   (an empty FB; export it for the format)
  project-get    [--filter fragment]                           public properties of the open project
  project-set    --prop P --value V                            e.g. IsSimulationDuringBlockCompilationEnabled
  master-secret  --plc PLC_1 --mode none|protect            (protect reads FRAKTAL_TIA_MASTER_SECRET)
  service-get    --plc PLC_1 [--item name] --service TypeName [--path A.B]   dump properties
  service-set    --plc PLC_1 [--item name] --service TypeName --prop A.B.P --value V
  download / online-state ... [--legacy true|false]          PG/PC protocol: legacy or TLS
                 [--trust-plc PLC_1]                          trust THIS PLC's TLS certificate (logged)
  service-call   --plc PLC_1 [--item name] --service TypeName --method M   (parameterless)
  block-attribute --plc PLC_1 --name B [--filter f | --attr A --value V]
  webserver-user --plc PLC_1 --name N --permissions ReadTag,ModifyTag --password-env VAR
  webserver-certificate --plc PLC_1 [--item I]     (create once from the WebServer template; kept after)
  umac-user --plc PLC_1 --list
            | (--anonymous | --name N --password-env VAR) [--role R --rights id1,id2] [--system-roles id1,id2]
                                                          (the custom role gets exactly these rights)
  ?<command> ...                                             (plan line) record failure, continue
  import-sources ... [--only 00_,10_]                         restrict to file-name prefixes
  save
";
    }

    /// <summary>One TIA Portal instance, one open project.</summary>
    internal sealed class Session : IDisposable
    {
        private readonly TiaPortal _tia;
        private readonly bool _attached;
        private Project _project;

        public Session(Args first)
        {
            if (first.Flag("attach"))
            {
                var process = TiaPortal.GetProcesses().FirstOrDefault()
                              ?? throw new InvalidOperationException("--attach: no running TIA Portal process.");
                _tia = process.Attach();
                _attached = true;
                _project = _tia.Projects.FirstOrDefault();
                Log.Emit("tia", ("mode", "attached"), ("pid", process.Id));
            }
            else
            {
                var mode = first.Flag("ui") ? TiaPortalMode.WithUserInterface : TiaPortalMode.WithoutUserInterface;
                _tia = new TiaPortal(mode);
                Log.Emit("tia", ("mode", mode.ToString()));
            }
            // TIA's message boxes arrive as events in Openness; record them (the default
            // answer stands — a plan never clicks "yes" on a question it has not seen).
            _tia.Confirmation += (s, e) => Log.Emit("tia-confirmation", ("caption", e.Caption), ("text", e.Text),
                ("detail", e.DetailText), ("choices", e.Choices.ToString()), ("result", e.Result.ToString()));
            _tia.Notification += (s, e) => Log.Emit("tia-notification", ("caption", e.Caption), ("text", e.Text), ("detail", e.DetailText));
        }

        public void Dispose()
        {
            if (!_attached)
            {
                try { _project?.Close(); } catch (Exception ex) { Log.Emit("close-warning", ("message", ex.Message)); }
                _tia.Dispose();
            }
        }

        public int Execute(Args a)
        {
            switch (a.Command)
            {
                case "create-project": return CreateProject(a);
                case "open-project": return OpenProject(a);
                case "add-device": return AddDevice(a);
                case "set-ip": return SetIp(a);
                case "import-sources": return ImportSources(a);
                case "import-xml": return ImportXml(a);
                case "delete-blocks": return DeleteBlocks(a);
                case "compile": return Compile(a);
                case "interfaces": return Interfaces(a);
                case "download": return Download(a);
                case "online-state": return OnlineState(a);
                case "export": return Export(a);
                case "hw-attributes": return HwAttributes(a);
                case "set-hw-attribute": return SetHwAttribute(a);
                case "list-blocks": return ListBlocks(a);
                case "set-block-number": return SetBlockNumber(a);
                case "create-block": return CreateBlock(a);
                case "project-get": return ProjectGet(a);
                case "project-set": return ProjectSet(a);
                case "master-secret": return MasterSecret(a);
                case "service-get": return ServiceGet(a);
                case "service-set": return ServiceSet(a);
                case "service-call": return ServiceCall(a);
                case "block-attribute": return BlockAttribute(a);
                case "webserver-user": return WebserverUser(a);
                case "webserver-certificate": return WebserverCertificate(a);
                case "umac-user": return UmacUser(a);
                case "cax-export": return CaxExport(a);
                case "save": Project.Save(); Log.Emit("saved", ("path", Project.Path.FullName)); return 0;
                default:
                    Log.Emit("unknown-command", ("command", a.Command));
                    return 64;
            }
        }

        private Project Project => _project ?? throw new InvalidOperationException("No project open (create-project / open-project first).");

        private int CreateProject(Args a)
        {
            var dir = new DirectoryInfo(a.Require("dir"));
            var name = a.Require("name");
            var target = new DirectoryInfo(Path.Combine(dir.FullName, name));
            if (target.Exists)
            {
                if (!a.Flag("replace")) throw new IOException("Project folder exists (use --replace): " + target.FullName);
                target.Delete(true);
            }
            dir.Create();
            _project = _tia.Projects.Create(dir, name);
            Log.Emit("project-created", ("path", _project.Path.FullName));
            return 0;
        }

        private int OpenProject(Args a)
        {
            _project = _tia.Projects.Open(new FileInfo(a.Require("path")));
            Log.Emit("project-opened", ("path", _project.Path.FullName));
            return 0;
        }

        private int AddDevice(Args a)
        {
            var order = a.Require("order");
            var name = a.Require("name");
            var station = a.Get("station", name + "_Station");
            var device = Project.Devices.CreateWithItem(order, name, station);
            Log.Emit("device-added", ("station", device.Name), ("order", order), ("plc", name));
            return 0;
        }

        private int SetIp(Args a)
        {
            var cpu = Cpu(a);
            var found = EthernetNode(cpu, a.Get("item", null));
            if (found == null)
            {
                Log.Emit("ip-set-failed", ("reason", "no Ethernet interface under " + cpu.Name));
                return 3;
            }
            var (item, node) = found.Value;
            node.SetAttribute("Address", a.Require("ip"));
            if (a.Has("mask")) node.SetAttribute("SubnetMask", a.Get("mask", null));
            Log.Emit("ip-set", ("interface", item.Name), ("address", node.GetAttribute("Address")), ("mask", node.GetAttribute("SubnetMask")));
            return 0;
        }

        // The CPU's Ethernet node: the first one, or the one on the named interface.
        // A CPU with a PROFIBUS port (1516-3 PN/DP) has a DP node too, whose Address is
        // the DP address - set-ip and the download target check must never pick it.
        private static (DeviceItem, Node)? EthernetNode(DeviceItem cpu, string itemName)
        {
            foreach (var item in Walk(cpu))
            {
                if (itemName != null && item.Name != itemName) continue;
                var ni = item.GetService<NetworkInterface>();
                if (ni == null) continue;
                foreach (var node in ni.Nodes)
                    if (node.NodeType == NetType.Ethernet) return (item, node);
            }
            return null;
        }

        // Order matters: types before the blocks that use them, global data before the
        // code that reads it, instance DBs after their FBs. Files are imported in
        // ordinal name order, so the numbered prefix (00_, 10_, ...) IS the dependency
        // order — one rule, visible in the directory listing.
        private int ImportSources(Args a)
        {
            var plc = Plc(a);
            var dir = new DirectoryInfo(a.Require("dir"));
            var only = a.Get("only", null)?.Split(',');
            var files = dir.GetFiles().Where(f => IsSource(f.Extension))
                .Where(f => only == null || only.Any(o => f.Name.StartsWith(o, StringComparison.OrdinalIgnoreCase)))
                .OrderBy(f => f.Name, StringComparer.Ordinal).ToList();
            var option = a.Flag("keep-on-error") ? GenerateBlockOption.KeepOnError : GenerateBlockOption.None;
            var failures = 0;
            foreach (var file in files)
            {
                var existing = plc.ExternalSourceGroup.ExternalSources.Find(file.Name);
                existing?.Delete();
                var source = plc.ExternalSourceGroup.ExternalSources.CreateFromFile(file.Name, file.FullName);
                try
                {
                    source.GenerateBlocksFromSource(option);
                    Log.Emit("source-generated", ("file", file.Name), ("sha256", Hash(file)));
                }
                catch (Exception ex)
                {
                    failures++;
                    Log.Emit("source-failed", ("file", file.Name), ("message", Program.Flatten(ex)));
                }
            }
            return failures == 0 ? 0 : 4;
        }

        private static bool IsSource(string ext) => ClassOrder(ext) < 9;

        private static int ClassOrder(string ext)
        {
            switch (ext.ToLowerInvariant())
            {
                case ".udt": return 0;
                case ".scl": return 1;
                case ".db": return 2;
                default: return 9;
            }
        }

        private int ImportXml(Args a)
        {
            var plc = Plc(a);
            var file = new FileInfo(a.Require("file"));
            switch (a.Get("kind", "block"))
            {
                case "type":
                    foreach (var t in plc.TypeGroup.Types.Import(file, ImportOptions.Override))
                        Log.Emit("type-imported", ("name", t.Name));
                    break;
                case "tags":
                    foreach (var t in plc.TagTableGroup.TagTables.Import(file, ImportOptions.Override))
                        Log.Emit("tagtable-imported", ("name", t.Name));
                    break;
                default:
                    foreach (var b in plc.BlockGroup.Blocks.Import(file, ImportOptions.Override))
                        Log.Emit("block-imported", ("name", b.Name), ("language", b.ProgrammingLanguage.ToString()));
                    break;
            }
            return 0;
        }

        private int DeleteBlocks(Args a)
        {
            var plc = Plc(a);
            foreach (var b in plc.BlockGroup.Blocks.ToList()) { Log.Emit("block-deleted", ("name", b.Name)); b.Delete(); }
            foreach (var g in plc.BlockGroup.Groups.ToList()) { Log.Emit("group-deleted", ("name", g.Name)); g.Delete(); }
            foreach (var t in plc.TypeGroup.Types.ToList()) { Log.Emit("type-deleted", ("name", t.Name)); t.Delete(); }
            foreach (var s in plc.ExternalSourceGroup.ExternalSources.ToList()) s.Delete();
            return 0;
        }

        private int Compile(Args a)
        {
            var cpu = Cpu(a);
            ICompilable target = a.Flag("hw")
                ? cpu.GetService<ICompilable>()
                : Plc(a).GetService<ICompilable>();
            var result = target.Compile();
            Log.Emit("compile", ("state", result.State.ToString()), ("errors", result.ErrorCount), ("warnings", result.WarningCount));
            EmitMessages(result.Messages, 0);
            return result.ErrorCount == 0 ? 0 : 5;
        }

        private static void EmitMessages(CompilerResultMessageComposition messages, int depth)
        {
            foreach (var m in messages)
            {
                if (m.State != CompilerResultState.Success || depth < 2 || m.ErrorCount + m.WarningCount > 0)
                    Log.Emit("compile-message", ("depth", depth), ("state", m.State.ToString()), ("path", m.Path), ("text", m.Description));
                EmitMessages(m.Messages, depth + 1);
            }
        }

        private int Interfaces(Args a)
        {
            var dp = Cpu(a).GetService<DownloadProvider>();
            foreach (var mode in dp.Configuration.Modes)
                foreach (var pc in mode.PcInterfaces)
                {
                    Log.Emit("pc-interface", ("mode", mode.Name), ("name", pc.Name), ("number", pc.Number),
                        ("targets", string.Join("|", pc.TargetInterfaces.Select(t => t.Name))));
                    if (!a.Flag("scan")) continue;
                    try
                    {
                        foreach (var dev in pc.GetAccessibleDevices())
                            Log.Emit("accessible-device", ("pc", pc.Name), ("attributes", Attributes(dev)));
                    }
                    catch (Exception ex)
                    {
                        Log.Emit("scan-failed", ("pc", pc.Name), ("message", Program.Flatten(ex)));
                    }
                }
            return 0;
        }

        private ConnectionConfiguration _legitimationOwner;
        private OnlineConfigurationDelegate _legitimation;

        private void Unsubscribe()
        {
            if (_legitimationOwner == null) return;
            try { _legitimationOwner.OnlineLegitimation -= _legitimation; }
            catch (Exception ex) { Log.Emit("unsubscribe-warning", ("message", Program.Flatten(ex))); }
            _legitimationOwner = null;
            _legitimation = null;
        }

        private ConfigurationTargetInterface Target(DeviceItem cpu, ConnectionConfiguration configuration, Args a)
        {
            // --legacy true|false selects the PG/PC protocol: TLS (secure, the V4.7 /
            // V3.1 default) or legacy. Logged either way, so evidence states which was used.
            if (a.Has("legacy"))
                configuration.EnableLegacyCommunication = bool.Parse(a.Get("legacy", "false"));
            Log.Emit("connection", ("legacy", configuration.EnableLegacyCommunication), ("configured", configuration.IsConfigured));
            // One subscription at a time: a second Subscribe in the same session throws
            // (measured), so every step releases its handler when it ends (Unsubscribe).
            Unsubscribe();
            _legitimationOwner = configuration;
            _legitimation = new OnlineAnswers(a).Answer;
            configuration.OnlineLegitimation += _legitimation;
            var mode = configuration.Modes.Find(a.Get("mode", "PN/IE"))
                       ?? throw new InvalidOperationException("Connection mode not found: " + a.Get("mode", "PN/IE"));
            var pc = mode.PcInterfaces.Find(a.Require("pc-interface"), int.Parse(a.Get("pc-number", "1")))
                     ?? throw new InvalidOperationException("PC interface not found (run `interfaces`): " + a.Get("pc-interface", ""));
            var targetName = a.Get("target", null);
            var target = targetName == null ? pc.TargetInterfaces.FirstOrDefault() : pc.TargetInterfaces.Find(targetName);
            return target ?? throw new InvalidOperationException("Target interface not found on " + cpu.Name);
        }

        private int Download(Args a)
        {
            var cpu = Cpu(a);
            var configured = ConfiguredIp(cpu);
            var confirm = a.Require("confirm-target");
            if (!string.Equals(configured, confirm, StringComparison.Ordinal))
            {
                Log.Emit("download-refused", ("reason", "confirm-target does not match the configured CPU address"),
                    ("configured", configured), ("confirm", confirm));
                return 6;
            }

            var dp = cpu.GetService<DownloadProvider>();
            var target = Target(cpu, dp.Configuration, a);
            var options = a.Flag("software-only") ? DownloadOptions.Software : DownloadOptions.Hardware | DownloadOptions.Software;
            var answers = new DownloadAnswers(a);
            Log.Emit("download-start", ("plc", cpu.Name), ("target", target.Name), ("address", configured), ("options", options.ToString()));
            try
            {
                var result = dp.Download(target, answers.Pre, answers.Post, options);
                Log.Emit("download", ("state", result.State.ToString()), ("errors", result.ErrorCount), ("warnings", result.WarningCount));
                EmitDownloadMessages(result.Messages, 0);
                return result.ErrorCount == 0 ? 0 : 7;
            }
            finally
            {
                Unsubscribe();
            }
        }

        private static void EmitDownloadMessages(DownloadResultMessageComposition messages, int depth)
        {
            foreach (var m in messages)
            {
                Log.Emit("download-message", ("depth", depth), ("state", m.State.ToString()), ("text", m.Message));
                EmitDownloadMessages(m.Messages, depth + 1);
            }
        }

        private int OnlineState(Args a)
        {
            var cpu = Cpu(a);
            var op = cpu.GetService<OnlineProvider>();
            op.Configuration.ApplyConfiguration(Target(cpu, op.Configuration, a));
            try
            {
                var state = op.GoOnline();
                Log.Emit("online", ("state", state.ToString()));
                return state == Siemens.Engineering.Online.OnlineState.Online ? 0 : 8;
            }
            finally
            {
                // A failed GoOnline can leave the provider half-online; the next attempt
                // in the same plan would then fail with "not permitted in online mode".
                try { op.GoOffline(); } catch (Exception ex) { Log.Emit("offline-warning", ("message", ex.Message)); }
                Unsubscribe();
            }
        }

        private int Export(Args a)
        {
            var plc = Plc(a);
            var outDir = Directory.CreateDirectory(a.Require("out"));
            var xmlDir = Directory.CreateDirectory(Path.Combine(outDir.FullName, "xml"));
            var generators = new List<IGenerateSource>();
            foreach (var b in AllBlocks(plc.BlockGroup))
            {
                if (!b.IsConsistent)
                {
                    Log.Emit("export-skipped", ("name", b.Name), ("reason", "inconsistent (compile it first)"));
                    continue;
                }
                var file = new FileInfo(Path.Combine(xmlDir.FullName, b.Name + ".xml"));
                if (file.Exists) file.Delete();
                b.Export(file, ExportOptions.WithDefaults);
                Log.Emit("exported", ("name", b.Name), ("language", b.ProgrammingLanguage.ToString()), ("sha256", Hash(file)));
                if (b is IGenerateSource g && b.ProgrammingLanguage == ProgrammingLanguage.SCL) generators.Add(g);
                if (b is IGenerateSource gd && b is DataBlock) generators.Add(gd);
            }
            foreach (var t in plc.TypeGroup.Types)
            {
                if (!t.IsConsistent)
                {
                    Log.Emit("export-skipped", ("name", t.Name), ("reason", "inconsistent (compile it first)"));
                    continue;
                }
                var file = new FileInfo(Path.Combine(xmlDir.FullName, t.Name + ".type.xml"));
                if (file.Exists) file.Delete();
                t.Export(file, ExportOptions.WithDefaults);
                if (t is IGenerateSource g) generators.Add(g);
            }
            if (a.Flag("scl"))
            {
                var sclDir = Directory.CreateDirectory(Path.Combine(outDir.FullName, "scl"));
                foreach (var g in generators)
                {
                    var name = ((IEngineeringObject)g).GetAttribute("Name") as string;
                    var ext = g is PlcType ? ".udt" : g is DataBlock ? ".db" : ".scl";
                    var file = new FileInfo(Path.Combine(sclDir.FullName, name + ext));
                    if (file.Exists) file.Delete();
                    plc.ExternalSourceGroup.GenerateSource(new[] { g }, file, GenerateOptions.None);
                    Log.Emit("source-exported", ("name", name), ("sha256", Hash(file)));
                }
            }
            return 0;
        }

        // Hardware attributes are discovered, not guessed: dump them (optionally
        // filtered by a name fragment) before setting one.
        // GetAttributeInfos() does not list every attribute (WebserverCertificate is
        // readable and writable on a 1214C yet absent from it, measured), so --probe
        // names extra attributes to try on every item.
        private int HwAttributes(Args a)
        {
            var filter = a.Get("filter", null);
            var probes = a.Get("probe", "").Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();
            foreach (var item in Walk(Cpu(a)))
            {
                var listed = new HashSet<string>(StringComparer.Ordinal);
                foreach (var info in item.GetAttributeInfos())
                {
                    listed.Add(info.Name);
                    if (filter != null && info.Name.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
                    object value;
                    try { value = item.GetAttribute(info.Name); } catch (Exception ex) { value = "<" + ex.GetType().Name + ">"; }
                    Log.Emit("hw-attribute", ("item", item.Name), ("attr", info.Name), ("value", value), ("access", info.AccessMode.ToString()));
                }
                foreach (var name in probes.Where(n => !listed.Contains(n)))
                {
                    try { Log.Emit("hw-attribute-hidden", ("item", item.Name), ("attr", name), ("value", item.GetAttribute(name))); }
                    catch (Exception ex)
                    {
                        // the reason matters on the CPU item: "not supported" differs from
                        // "exists but not readable in this state"
                        if (item.Name == a.Get("plc", "PLC_1"))
                            Log.Emit("hw-attribute-probe-failed", ("item", item.Name), ("attr", name), ("message", ex.Message));
                    }
                }
            }
            return 0;
        }

        // Hardware configuration as AutomationML (CAx). It carries attributes the
        // Openness parameter documentation does not list for a family, so it is how a
        // setting's name is found instead of guessed.
        private int CaxExport(Args a)
        {
            IEngineeringObject device = Cpu(a);
            while (device != null && !(device is Device)) device = device.Parent;
            var file = new FileInfo(a.Require("out"));
            var log = new FileInfo(Path.ChangeExtension(file.FullName, ".log"));
            if (file.Exists) file.Delete();
            if (log.Exists) log.Delete();
            var ok = Project.GetService<Siemens.Engineering.Cax.CaxProvider>().Export((Device)device, file, log);
            file.Refresh();
            Log.Emit("cax-export", ("ok", ok), ("file", file.FullName), ("bytes", file.Exists ? file.Length : 0), ("log", log.FullName));
            return ok ? 0 : 12;
        }

        private int SetHwAttribute(Args a)
        {
            var cpu = Cpu(a);
            var itemName = a.Get("item", cpu.Name);
            var item = Walk(cpu).FirstOrDefault(i => i.Name == itemName)
                       ?? throw new InvalidOperationException("Device item not found: " + itemName);
            var attr = a.Require("attr");
            if (a.Has("type"))
            {
                // Some attributes have a setter but no getter: WebserverCertificateType
                // on a 1214C V4.7 answers "get_WebserverCertificateType is not supported"
                // (measured). --type writes without reading first.
                var text = a.Require("value");
                object typed;
                switch (a.Require("type"))
                {
                    case "int": typed = int.Parse(text, System.Globalization.CultureInfo.InvariantCulture); break;
                    case "uint": typed = uint.Parse(text, System.Globalization.CultureInfo.InvariantCulture); break;
                    case "long": typed = long.Parse(text, System.Globalization.CultureInfo.InvariantCulture); break;
                    case "bool": typed = bool.Parse(text); break;
                    case "string": typed = text; break;
                    default: throw new ArgumentException("--type int|uint|long|bool|string");
                }
                item.SetAttribute(attr, typed);
                object now;
                try { now = item.GetAttribute(attr); } catch (Exception) { now = "<write-only>"; }
                Log.Emit("hw-attribute-set", ("item", item.Name), ("attr", attr), ("was", "<unread>"), ("written", typed), ("now", now));
                return 0;
            }
            var current = item.GetAttribute(attr);
            var value = ConvertLike(current, a.Require("value"));
            item.SetAttribute(attr, value);
            Log.Emit("hw-attribute-set", ("item", item.Name), ("attr", attr), ("was", current), ("now", item.GetAttribute(attr)));
            return 0;
        }

        private static object ConvertLike(object current, string text)
        {
            if (current is bool) return bool.Parse(text);
            if (current is Enum) return Enum.Parse(current.GetType(), text);
            if (current == null || current is string) return text;
            return Convert.ChangeType(text, current.GetType(), System.Globalization.CultureInfo.InvariantCulture);
        }

        private int ListBlocks(Args a)
        {
            foreach (var b in AllBlocks(Plc(a).BlockGroup))
                Log.Emit("block", ("name", b.Name), ("number", b.Number), ("kind", b.GetType().Name), ("language", b.ProgrammingLanguage.ToString()));
            return 0;
        }

        // The bench harvest reads one test-only DB by number (Part IV §4.3), so the
        // number is pinned instead of left to automatic assignment.
        // An empty FB in a given language. Its export is the authoritative sample of
        // that language's SimaticML (GRAPH: Part IV s.3.5, S11) - a generator is
        // written against what TIA itself emits, never against a guess.
        private int CreateBlock(Args a)
        {
            var plc = Plc(a);
            var name = a.Require("name");
            if (AllBlocks(plc.BlockGroup).Any(b => b.Name == name))
                throw new InvalidOperationException("Block exists: " + name);
            var lang = (ProgrammingLanguage)Enum.Parse(typeof(ProgrammingLanguage), a.Require("lang"));
            var auto = !a.Has("number");
            var fb = plc.BlockGroup.Blocks.CreateFB(name, auto, auto ? 0 : int.Parse(a.Require("number")), lang);
            Log.Emit("block-created", ("name", fb.Name), ("number", fb.Number), ("language", fb.ProgrammingLanguage.ToString()));
            return 0;
        }

        // Project-level settings are plain properties of the project object (e.g.
        // IsSimulationDuringBlockCompilationEnabled, needed before any block can be
        // downloaded to S7-PLCSIM - measured). Reached by reflection, like services,
        // so a new setting needs a plan line, not a new (re-whitelisted) build.
        private int ProjectGet(Args a)
        {
            var filter = a.Get("filter", null);
            foreach (var p in Project.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                if (p.GetIndexParameters().Length > 0) continue;
                if (filter != null && p.Name.IndexOf(filter, StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (!(p.PropertyType.IsPrimitive || p.PropertyType.IsEnum || p.PropertyType == typeof(string))) continue;
                object value;
                try { value = p.GetValue(Project); } catch (Exception ex) { value = "<" + (ex.InnerException ?? ex).GetType().Name + ">"; }
                Log.Emit("project-property", ("prop", p.Name), ("value", value), ("writable", p.CanWrite));
            }
            return 0;
        }

        private int ProjectSet(Args a)
        {
            var name = a.Require("prop");
            var prop = Project.GetType().GetProperty(name)
                       ?? throw new InvalidOperationException("No project property " + name);
            var before = prop.GetValue(Project);
            var text = a.Require("value");
            var value = prop.PropertyType.IsEnum ? Enum.Parse(prop.PropertyType, text)
                : prop.PropertyType == typeof(bool) ? (object)bool.Parse(text)
                : Convert.ChangeType(text, prop.PropertyType, System.Globalization.CultureInfo.InvariantCulture);
            prop.SetValue(Project, value);
            Log.Emit("project-set", ("prop", name), ("was", before), ("now", prop.GetValue(Project)));
            return 0;
        }

        private int SetBlockNumber(Args a)
        {
            var name = a.Require("name");
            var block = AllBlocks(Plc(a).BlockGroup).FirstOrDefault(b => b.Name == name)
                        ?? throw new InvalidOperationException("Block not found: " + name);
            block.SetAttribute("AutoNumber", false);
            block.SetAttribute("Number", int.Parse(a.Require("number")));
            Log.Emit("block-number", ("name", block.Name), ("number", block.Number));
            return 0;
        }

        // Protection of confidential PLC configuration data (the "PLC master secret").
        // TIA V20 refuses to compile an S7-1200 V4.7 / S7-1500 V3.1+ project left in
        // the default WithoutPassword state. `none` switches the protection off (an
        // isolated bench only — declare it in the evidence); `protect` sets a password
        // read from FRAKTAL_TIA_MASTER_SECRET so it never appears in a plan or a log.
        private int MasterSecret(Args a)
        {
            var cpu = Cpu(a);
            var svc = cpu.GetService<PlcMasterSecretConfigurator>()
                      ?? throw new InvalidOperationException("CPU offers no PlcMasterSecretConfigurator: " + cpu.Name);
            var before = svc.MasterSecretConfiguration;
            switch (a.Require("mode"))
            {
                case "none":
                    if (before != MasterSecretConfiguration.None) svc.Unprotect();
                    break;
                case "protect":
                    svc.Protect(SecretFromEnvironment("FRAKTAL_TIA_MASTER_SECRET"));
                    break;
                default:
                    throw new ArgumentException("master-secret --mode none|protect");
            }
            Log.Emit("master-secret", ("was", before.ToString()), ("now", svc.MasterSecretConfiguration.ToString()));
            return 0;
        }

        // ---- generic service access ------------------------------------------
        // Each new hardware setting in Openness tends to live on its own service
        // (PlcAccessControlConfigurationProvider, PlcAccessLevelProvider, ...). Reaching
        // them by reflection means a new setting needs a plan line, not a new build —
        // and a new build needs a new Openness-firewall approval.
        private object Service(Args a)
        {
            var cpu = Cpu(a);
            var itemName = a.Get("item", cpu.Name);
            var item = Walk(cpu).FirstOrDefault(i => i.Name == itemName)
                       ?? throw new InvalidOperationException("Device item not found: " + itemName);
            var typeName = a.Require("service");
            var type = typeof(DeviceItem).Assembly.GetTypes()
                           .FirstOrDefault(t => t.Name == typeName && typeof(IEngineeringService).IsAssignableFrom(t))
                       ?? throw new InvalidOperationException("No Openness service type named " + typeName);
            var getService = typeof(IEngineeringServiceProvider).GetMethod("GetService").MakeGenericMethod(type);
            return getService.Invoke(item, null)
                   ?? throw new InvalidOperationException(typeName + " is not offered by " + item.Name);
        }

        // A dotted path walks nested objects: --path Configuration lists the
        // ConnectionConfiguration of a DownloadProvider; --prop A.B sets B on A.
        private static object Descend(object root, string path)
        {
            var o = root;
            if (string.IsNullOrEmpty(path)) return o;
            foreach (var part in path.Split('.'))
            {
                var p = o.GetType().GetProperty(part) ?? throw new InvalidOperationException("No property " + part + " on " + o.GetType().Name);
                o = p.GetValue(o) ?? throw new InvalidOperationException(part + " is null");
            }
            return o;
        }

        private int ServiceGet(Args a)
        {
            var svc = Service(a);
            var target = Descend(svc, a.Get("path", null));
            foreach (var p in target.GetType().GetProperties(BindingFlags.Public | BindingFlags.Instance))
            {
                if (p.GetIndexParameters().Length > 0) continue;
                object value;
                try { value = p.GetValue(target); } catch (Exception ex) { value = "<" + (ex.InnerException ?? ex).GetType().Name + ">"; }
                var options = p.PropertyType.IsEnum ? string.Join("|", Enum.GetNames(p.PropertyType)) : null;
                Log.Emit("service-property", ("service", svc.GetType().Name), ("object", target.GetType().Name), ("prop", p.Name), ("value", value), ("writable", p.CanWrite), ("options", options));
            }
            return 0;
        }

        private int ServiceSet(Args a)
        {
            var svc = Service(a);
            var full = a.Require("prop");
            var dot = full.LastIndexOf('.');
            var owner = Descend(svc, dot < 0 ? null : full.Substring(0, dot));
            var name = dot < 0 ? full : full.Substring(dot + 1);
            var prop = owner.GetType().GetProperty(name)
                       ?? throw new InvalidOperationException("No property " + full);
            var before = prop.GetValue(owner);
            var text = a.Require("value");
            var value = prop.PropertyType.IsEnum ? Enum.Parse(prop.PropertyType, text)
                : prop.PropertyType == typeof(bool) ? (object)bool.Parse(text)
                : Convert.ChangeType(text, prop.PropertyType, System.Globalization.CultureInfo.InvariantCulture);
            prop.SetValue(owner, value);
            Log.Emit("service-set", ("service", svc.GetType().Name), ("prop", full), ("was", before), ("now", prop.GetValue(owner)));
            return 0;
        }

        private int ServiceCall(Args a)
        {
            var svc = Service(a);
            var name = a.Require("method");
            var method = svc.GetType().GetMethods().FirstOrDefault(m => m.Name == name && m.GetParameters().Length == 0)
                         ?? throw new InvalidOperationException("No parameterless method " + name);
            var result = method.Invoke(svc, null);
            Log.Emit("service-call", ("service", svc.GetType().Name), ("method", name), ("result", result));
            return 0;
        }

        private int BlockAttribute(Args a)
        {
            var name = a.Require("name");
            var block = (IEngineeringObject)AllBlocks(Plc(a).BlockGroup).FirstOrDefault(b => b.Name == name)
                        ?? throw new InvalidOperationException("Block not found: " + name);
            if (a.Has("attr") && a.Has("value"))
            {
                var attr = a.Require("attr");
                var current = block.GetAttribute(attr);
                block.SetAttribute(attr, ConvertLike(current, a.Require("value")));
                Log.Emit("block-attribute-set", ("block", name), ("attr", attr), ("was", current), ("now", block.GetAttribute(attr)));
                return 0;
            }
            foreach (var info in block.GetAttributeInfos())
            {
                if (a.Has("filter") && info.Name.IndexOf(a.Get("filter", ""), StringComparison.OrdinalIgnoreCase) < 0) continue;
                object v;
                try { v = block.GetAttribute(info.Name); } catch (Exception ex) { v = "<" + ex.GetType().Name + ">"; }
                Log.Emit("block-attribute", ("block", name), ("attr", info.Name), ("value", v), ("access", info.AccessMode.ToString()));
            }
            return 0;
        }

        // Web API / web server user (Part IV §11.1a). The password comes only from the
        // environment variable named by --password-env, so it never appears in a plan,
        // a command line or a log. Permissions are WebserverUserPermissions names,
        // comma-separated (they are bit values: ReadTag=2, ModifyTag=4, ...).
        private int WebserverUser(Args a)
        {
            var cpu = Cpu(a);
            var svc = cpu.GetService<WebserverUserManagement>()
                      ?? throw new InvalidOperationException("CPU offers no WebserverUserManagement: " + cpu.Name);
            var name = a.Require("name");
            long bits = 0;
            foreach (var p in a.Require("permissions").Split(','))
                bits |= Convert.ToInt64(Enum.Parse(typeof(WebserverUserPermissions), p.Trim()));
            var permissions = (WebserverUserPermissions)Enum.ToObject(typeof(WebserverUserPermissions), bits);
            var password = SecretFromEnvironment(a.Require("password-env"));
            var user = svc.WebserverUsers.Find(name);
            if (user == null)
            {
                user = svc.WebserverUsers.Create(name, permissions, password);
                Log.Emit("webserver-user", ("name", name), ("action", "created"), ("permissions", user.Permissions.ToString()));
            }
            else
            {
                user.Permissions = permissions;
                user.SetPassword(password);
                Log.Emit("webserver-user", ("name", name), ("action", "updated"), ("permissions", user.Permissions.ToString()));
            }
            return 0;
        }

        // Secrets enter only through an environment variable named on the command line,
        // so they never appear in a plan, an argument list or a log.
        internal static SecureString SecretFromEnvironment(string envName)
        {
            var secret = Environment.GetEnvironmentVariable(envName);
            if (string.IsNullOrEmpty(secret))
                throw new InvalidOperationException("environment variable " + envName + " is empty");
            var s = new SecureString();
            foreach (var ch in secret) s.AppendChar(ch);
            s.MakeReadOnly();
            return s;
        }

        // A service may hang off the project, the device, the CPU item or its software,
        // and which one differs by family; search them in that order and log the owner.
        private T FindService<T>(DeviceItem cpu) where T : class, IEngineeringService
        {
            IEngineeringObject device = cpu;
            while (device != null && !(device is Device)) device = device.Parent;
            var owners = new (string, object)[]
            {
                ("project", Project), ("device", device), ("cpu", cpu),
                ("software", cpu.GetService<SoftwareContainer>()?.Software),
            };
            foreach (var (where, owner) in owners)
            {
                var found = (owner as IEngineeringServiceProvider)?.GetService<T>();
                if (found == null) continue;
                Log.Emit("service-found", ("service", typeof(T).Name), ("owner", where));
                return found;
            }
            throw new InvalidOperationException(typeof(T).Name + " is not offered for " + cpu.Name);
        }

        // UMAC user for the Web API (Part IV §11.1a). An S7-1200 V4.7 has no classic
        // web-user list: web (and OPC UA) users are project users whose roles carry
        // per-device function rights. --list prints what the device offers and changes
        // nothing; otherwise the user (or the anonymous user), one custom role and
        // EXACTLY the named rights (by identifier, never by a fuzzy match) are made to
        // exist - any other right on that role for this device is removed (least
        // privilege) - plus any named system roles.
        private int UmacUser(Args a)
        {
            var cpu = Cpu(a);
            var umac = FindService<Siemens.Engineering.Umac.UmacConfigurator>(cpu);
            var device = FindService<Siemens.Engineering.Umac.UmacDevice>(cpu);
            if (a.Flag("list"))
            {
                foreach (var r in device.AvailableDeviceFunctionRights)
                    Log.Emit("device-function-right", ("group", r.Group), ("identifier", r.Identifier), ("name", r.Name));
                foreach (var role in umac.SystemRoles)
                {
                    string rights;
                    try { rights = string.Join("|", role.GetAssignedSystemDeviceFunctionRights(device).Select(r => r.Identifier)); }
                    catch (Exception ex) { rights = "<" + ex.GetType().Name + ">"; }
                    Log.Emit("system-role", ("identifier", role.Identifier), ("name", role.Name), ("rights", rights));
                }
                foreach (var role in umac.CustomRoles)
                    Log.Emit("custom-role", ("name", role.Name),
                             ("rights", string.Join("|", role.GetAssignedDeviceFunctionRights(device).Select(r => r.Identifier))));
                foreach (var u in umac.ProjectUsers)
                    Log.Emit("project-user", ("name", u.Name), ("active", u.IsActive), ("roles", string.Join("|", u.Roles.Select(r => r.Name))));
                object anonymous;
                try { anonymous = umac.AnonymousUser?.IsActive; } catch (Exception ex) { anonymous = "<" + ex.GetType().Name + ">"; }
                Log.Emit("anonymous-user", ("active", anonymous));
                return 0;
            }

            // The target is the anonymous user (access without login - activated, no
            // password) or a named project user whose password comes from the environment.
            Siemens.Engineering.Umac.User user;
            string action;
            if (a.Flag("anonymous"))
            {
                // AnonymousUser is null until it has been activated once (measured).
                if (umac.AnonymousUser == null || !umac.AnonymousUser.IsActive) { umac.ActivateAnonymousUser(); action = "activated"; }
                else action = "kept";
                user = umac.AnonymousUser ?? throw new InvalidOperationException("ActivateAnonymousUser left no anonymous user");
            }
            else
            {
                var name = a.Require("name");
                var password = SecretFromEnvironment(a.Require("password-env"));
                var projectUser = umac.ProjectUsers.Find(name);
                action = "updated";
                if (projectUser == null) { projectUser = umac.ProjectUsers.Create(name, password); action = "created"; }
                else projectUser.SetPassword(password);
                user = projectUser;
            }

            var customRights = "";
            if (a.Has("role"))
            {
                var roleName = a.Require("role");
                var customRole = umac.CustomRoles.Find(roleName) ?? umac.CustomRoles.Create(roleName, "Fraktal (Part IV s.11.1a)");
                var wanted = a.Require("rights").Split(',').Select(s => s.Trim()).Where(s => s.Length > 0).ToList();
                var available = device.AvailableDeviceFunctionRights.ToList();
                var assigned = customRole.GetAssignedDeviceFunctionRights(device).ToList();
                foreach (var id in wanted)
                {
                    var right = available.FirstOrDefault(r => r.Identifier == id)
                                ?? throw new InvalidOperationException("Device function right not offered: " + id + " (run umac-user --list)");
                    if (!assigned.Any(r => r.Identifier == id)) customRole.AssignDeviceFunctionRight(device, right);
                }
                foreach (var extra in assigned.Where(r => !wanted.Contains(r.Identifier)))
                    customRole.UnAssignDeviceFunctionRight(device, extra);
                if (user.Roles.Find(customRole.Name) == null) user.Roles.Add(customRole);
                customRights = string.Join("|", customRole.GetAssignedDeviceFunctionRights(device).Select(r => r.Identifier));
            }
            // System roles carry fixed rights (e.g. PLCAdministrator = the three access
            // levels); named by exact identifier, as rights are.
            foreach (var id in a.Get("system-roles", "").Split(',').Select(s => s.Trim()).Where(s => s.Length > 0))
            {
                var systemRole = umac.SystemRoles.FirstOrDefault(r => r.Identifier == id)
                                 ?? throw new InvalidOperationException("System role not offered: " + id + " (run umac-user --list)");
                if (user.Roles.Find(systemRole.Name) == null) user.Roles.Add(systemRole);
            }
            Log.Emit("umac-user", ("name", user.Name), ("action", action),
                     ("roles", string.Join("|", user.Roles.Select(r => r.Name))), ("rights", customRights));
            return 0;
        }

        // HTTPS server certificate for the web server / Web API (Part IV §11.1a). The
        // TIA editor creates one from the device's WebServer template when the web
        // server is switched on; Openness does not, so this does the same thing once.
        // An assigned certificate is KEPT: replacing it changes the fingerprint every
        // client has pinned, which must be a deliberate act, not a side effect of a build.
        private int WebserverCertificate(Args a)
        {
            var cpu = Cpu(a);
            var itemName = a.Get("item", cpu.Name);
            var item = Walk(cpu).FirstOrDefault(i => i.Name == itemName)
                       ?? throw new InvalidOperationException("Device item not found: " + itemName);
            if (item.GetAttribute("WebserverCertificate") is Siemens.Engineering.Security.Certificate current)
            {
                Log.Emit("webserver-certificate", ("action", "kept"), ("id", current.Id), ("subject", current.SubjectCommonName),
                         ("validUntil", current.ValidUntil.ToString("o")));
                return 0;
            }
            var manager = Walk(cpu).Select(i => i.GetService<Siemens.Engineering.Security.LocalCertificateManager>())
                                   .FirstOrDefault(m => m != null)
                          ?? throw new InvalidOperationException("No LocalCertificateManager offered under " + cpu.Name);
            var store = manager.LocalCertificateStore;
            var template = store.GetCertificateTemplate(Siemens.Engineering.Security.CertificateUsage.WebServer);
            Log.Emit("certificate-template", ("subject", template.SubjectCommonName), ("signature", template.Signature.ToString()),
                     ("validFrom", template.ValidFrom.ToString("o")), ("validUntil", template.ValidUntil.ToString("o")),
                     ("subjectAlternativeNames", template.SubjectAlternativeNames.Count));
            var created = store.Certificates.Create(template);
            item.SetAttribute("WebserverCertificate", created);
            Log.Emit("webserver-certificate", ("action", "created"), ("id", created.Id), ("subject", created.SubjectCommonName),
                     ("validUntil", created.ValidUntil.ToString("o")), ("privateKey", created.HasPrivateKey));
            return 0;
        }

        private static IEnumerable<PlcBlock> AllBlocks(PlcBlockGroup group)
        {
            foreach (var b in group.Blocks) yield return b;
            foreach (var g in group.Groups)
                foreach (var b in AllBlocks(g)) yield return b;
        }

        // ---- device lookup -------------------------------------------------------

        private DeviceItem Cpu(Args a)
        {
            var name = a.Get("plc", "PLC_1");
            foreach (var device in AllDevices(Project.Devices, Project.DeviceGroups))
                foreach (var item in device.DeviceItems.SelectMany(Walk))
                    if (item.Name == name && item.GetService<SoftwareContainer>()?.Software is PlcSoftware)
                        return item;
            throw new InvalidOperationException("CPU not found: " + name);
        }

        private PlcSoftware Plc(Args a) => (PlcSoftware)Cpu(a).GetService<SoftwareContainer>().Software;

        private static IEnumerable<Device> AllDevices(DeviceComposition devices, DeviceUserGroupComposition groups)
        {
            foreach (var d in devices) yield return d;
            foreach (var g in groups)
                foreach (var d in AllDevices(g.Devices, g.Groups)) yield return d;
        }

        private static IEnumerable<DeviceItem> Walk(DeviceItem item)
        {
            yield return item;
            foreach (var child in item.DeviceItems)
                foreach (var d in Walk(child)) yield return d;
        }

        private static string ConfiguredIp(DeviceItem cpu) =>
            EthernetNode(cpu, null)?.Item2.GetAttribute("Address") as string;

        private static string Attributes(IEngineeringObject o)
        {
            var parts = new List<string>();
            foreach (var info in o.GetAttributeInfos())
            {
                try { parts.Add(info.Name + "=" + o.GetAttribute(info.Name)); }
                catch (Exception) { parts.Add(info.Name + "=?"); }
            }
            return string.Join("; ", parts);
        }

        internal static string Hash(FileInfo f)
        {
            using (var sha = System.Security.Cryptography.SHA256.Create())
            using (var s = f.OpenRead())
                return BitConverter.ToString(sha.ComputeHash(s)).Replace("-", "").ToLowerInvariant();
        }
    }

    /// <summary>
    /// Answers TIA's download questions. Every question is logged with the
    /// selections offered; a selection is chosen from an explicit preference list,
    /// and the security-relevant questions are answered only by an explicit flag.
    /// </summary>
    internal sealed class DownloadAnswers
    {
        private static readonly string[] Preferred =
        {
            "StopAll", "StartModule", "ConsistentDownload", "DownloadAllBlocks",
            "StopPlcAndReinitialize", "AcceptAll", "Overwrite", "Download", "Initialize",
        };

        // Questions answered "yes" without a flag: they concern only the content of
        // the image being downloaded to the confirmed target.
        private static readonly HashSet<string> SafeChecks = new HashSet<string>(StringComparer.Ordinal)
        {
            nameof(OverwriteTargetLanguages), nameof(CheckBeforeDownload), nameof(UpgradeTargetDevice),
            nameof(OverwriteHmiData), nameof(FitHmiComponents), nameof(ReplaceDownloadedData),
        };

        // UMAC data on the CPU (users, roles, their passwords) is changed only by an
        // explicit --user-management choice; without it TIA's own default stands.
        private static readonly Dictionary<string, string> UserManagementChoices = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            { "keep", "KeepOnlineUserManagementData" },
            { "update", "UpdateUserManagementDataButKeepOnlinePassword" },
            { "reset", "DownloadAllUserManagementDataResetToProject" },
        };

        private readonly bool _acceptUnencrypted;
        private readonly bool _acceptLowerProtection;
        private readonly string _passwordEnv;
        private readonly string _userManagement;

        public DownloadAnswers(Args a)
        {
            _acceptUnencrypted = a.Flag("accept-unencrypted-sensitive");
            _acceptLowerProtection = a.Flag("accept-lower-protection");
            _passwordEnv = a.Get("plc-password-env", null);
            var um = a.Get("user-management", null);
            if (um != null && !UserManagementChoices.TryGetValue(um, out _userManagement))
                throw new ArgumentException("--user-management keep|update|reset");
        }

        public void Pre(DownloadConfiguration c) => Answer("pre", c);
        public void Post(DownloadConfiguration c) => Answer("post", c);

        private void Answer(string phase, DownloadConfiguration c)
        {
            var type = c.GetType().Name;
            var message = TryGet(c, "Message");
            switch (c)
            {
                case DownloadPasswordConfiguration pw:
                    if (_passwordEnv == null)
                    {
                        Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", "none (no --plc-password-env)"));
                        return;
                    }
                    pw.SetPassword(Session.SecretFromEnvironment(_passwordEnv));
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", "password supplied"));
                    return;
                case UserManagementDownload um:
                    var umBefore = um.CurrentSelection;
                    if (_userManagement != null)
                        um.CurrentSelection = (UserManagementPreDownloadSelections)Enum.Parse(typeof(UserManagementPreDownloadSelections), _userManagement);
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message),
                        ("offered", string.Join("|", Enum.GetNames(typeof(UserManagementPreDownloadSelections)))),
                        ("was", umBefore.ToString()), ("answer", um.CurrentSelection.ToString() + (_userManagement == null ? " (TIA default; no --user-management)" : " (flag)")));
                    return;
                case AcceptDownloadOfUnencryptedSensitiveData check:
                    check.Checked = _acceptUnencrypted;
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", _acceptUnencrypted ? "checked (flag)" : "unchecked"));
                    return;
                case DownloadCheckConfiguration check:
                    var yes = SafeChecks.Contains(type);
                    if (yes) check.Checked = true;
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", yes ? "checked" : "left " + check.Checked));
                    return;
                case ProtectionLevelChanged pl:
                    // Lowering the CPU's protection is a security decision: only by flag.
                    var plBefore = pl.CurrentSelection;
                    if (_acceptLowerProtection) pl.CurrentSelection = ProtectionLevelChangedSelections.ContinueDownloading;
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message),
                        ("offered", string.Join("|", Enum.GetNames(typeof(ProtectionLevelChangedSelections)))), ("was", plBefore.ToString()),
                        ("answer", pl.CurrentSelection.ToString() + (_acceptLowerProtection ? " (flag)" : " (no --accept-lower-protection)")));
                    return;
                case DownloadSelectionConfiguration _:
                    SelectPreferred(phase, type, message, c);
                    return;
                default:
                    Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", "unhandled"));
                    return;
            }
        }

        // Selection types are distinct enum-typed properties per question, so the
        // choice is made by reflection over CurrentSelection's enum.
        private static void SelectPreferred(string phase, string type, string message, DownloadConfiguration c)
        {
            var prop = c.GetType().GetProperty("CurrentSelection");
            if (prop == null)
            {
                Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message), ("answer", "no CurrentSelection"));
                return;
            }
            var names = Enum.GetNames(prop.PropertyType);
            var current = prop.GetValue(c)?.ToString();
            var chosen = Preferred.SelectMany(p => names.Where(n => n.StartsWith(p, StringComparison.Ordinal))).FirstOrDefault();
            if (chosen != null && chosen != current)
                prop.SetValue(c, Enum.Parse(prop.PropertyType, chosen));
            Log.Emit("download-question", ("phase", phase), ("type", type), ("message", message),
                ("offered", string.Join("|", names)), ("was", current), ("answer", chosen ?? current));
        }

        private static string TryGet(object o, string property)
        {
            try { return o.GetType().GetProperty(property)?.GetValue(o)?.ToString(); }
            catch (Exception) { return null; }
        }
    }

    /// <summary>
    /// Answers the online questions TIA raises on ConnectionConfiguration.OnlineLegitimation
    /// (TLS certificate verification, read-access password, user authentication). Unanswered,
    /// they default to "not trusted" and the connection fails with no further detail — which
    /// is how a PLC whose certificate the project does not know looks from Openness.
    /// A certificate is trusted only when --trust-plc names exactly the PLC asking, and the
    /// verification info (certificate details) is logged as evidence of what was trusted.
    /// </summary>
    internal sealed class OnlineAnswers
    {
        private readonly string _trustPlc;
        private readonly string _passwordEnv;
        private readonly string _user;

        public OnlineAnswers(Args a)
        {
            _trustPlc = a.Get("trust-plc", null);
            _passwordEnv = a.Get("plc-password-env", null);
            _user = a.Get("plc-user", null);
        }

        public void Answer(Siemens.Engineering.Online.Configurations.OnlineConfiguration c)
        {
            switch (c)
            {
                case Siemens.Engineering.Online.Configurations.TlsVerificationConfiguration tls:
                    var trust = _trustPlc != null && string.Equals(_trustPlc, tls.PlcName, StringComparison.Ordinal);
                    var before = tls.CurrentSelection;
                    if (trust) tls.CurrentSelection = Siemens.Engineering.Online.Configurations.TlsVerificationConfigurationSelection.Trusted;
                    Log.Emit("online-question", ("type", "TlsVerification"), ("plc", tls.PlcName), ("was", before.ToString()),
                        ("answer", tls.CurrentSelection.ToString()), ("verification", tls.VerificationInfo));
                    return;
                case Siemens.Engineering.Online.Configurations.OnlinePasswordConfiguration pw:
                    if (_passwordEnv != null) pw.SetPassword(Session.SecretFromEnvironment(_passwordEnv));
                    Log.Emit("online-question", ("type", pw.GetType().Name), ("answer", _passwordEnv != null ? "password supplied" : "none (no --plc-password-env)"));
                    return;
                case Siemens.Engineering.Online.Configurations.OnlineAuthenticationConfiguration auth:
                    // UMAC login (access control enabled): a project user and its password.
                    // Without a named user the answer is the anonymous user where the CPU
                    // offers one: that is what connecting with no credentials means, and it
                    // gets only the rights the project gave "access without login".
                    var types = auth.GetSupportedAuthenticationTypes().Select(t => t.CurrentUserType).ToList();
                    string answer;
                    if (_user != null && _passwordEnv != null)
                    {
                        auth.OnlineCredentials.Type = Siemens.Engineering.Online.Configurations.UserType.ProjectUser;
                        auth.OnlineCredentials.Name = _user;
                        auth.OnlineCredentials.SetPassword(Session.SecretFromEnvironment(_passwordEnv));
                        answer = "project user " + _user;
                    }
                    else if (types.Contains(Siemens.Engineering.Online.Configurations.UserType.AnonymousUser))
                    {
                        auth.OnlineCredentials.Type = Siemens.Engineering.Online.Configurations.UserType.AnonymousUser;
                        answer = "anonymous (no --plc-user)";
                    }
                    else answer = "none (no --plc-user/--plc-password-env, anonymous not offered)";
                    Log.Emit("online-question", ("type", "OnlineAuthentication"), ("supported", string.Join("|", types)),
                        ("secure", auth.IsSecureCommunication), ("answer", answer));
                    return;
                default:
                    Log.Emit("online-question", ("type", c.GetType().Name), ("answer", "unhandled"));
                    return;
            }
        }
    }

    /// <summary>Minimal argument model: command, --key value, --flag, positionals, --set k=v.</summary>
    internal sealed class Args
    {
        private readonly Dictionary<string, string> _named = new Dictionary<string, string>(StringComparer.Ordinal);
        private readonly List<string> _positional = new List<string>();
        public readonly Dictionary<string, string> Sets = new Dictionary<string, string>(StringComparer.Ordinal);
        public string Command { get; private set; }
        public bool Tolerant { get; set; }

        public static Args Parse(IReadOnlyList<string> argv)
        {
            var a = new Args { Command = argv.Count > 0 ? argv[0] : "" };
            for (var i = 1; i < argv.Count; i++)
            {
                var t = argv[i];
                if (!t.StartsWith("--", StringComparison.Ordinal)) { a._positional.Add(t); continue; }
                var key = t.Substring(2);
                var hasValue = i + 1 < argv.Count && !argv[i + 1].StartsWith("--", StringComparison.Ordinal);
                var value = hasValue ? argv[++i] : "true";
                if (key == "set")
                {
                    var eq = value.IndexOf('=');
                    if (eq <= 0) throw new ArgumentException("--set expects name=value");
                    a.Sets[value.Substring(0, eq)] = value.Substring(eq + 1);
                }
                else a._named[key] = value;
            }
            return a;
        }

        public static List<string> Split(string line)
        {
            var result = new List<string>();
            var sb = new StringBuilder();
            var quoted = false;
            foreach (var ch in line)
            {
                if (ch == '"') { quoted = !quoted; continue; }
                if (char.IsWhiteSpace(ch) && !quoted)
                {
                    if (sb.Length > 0) { result.Add(sb.ToString()); sb.Clear(); }
                    continue;
                }
                sb.Append(ch);
            }
            if (quoted) throw new ArgumentException("Unbalanced quote in: " + line);
            if (sb.Length > 0) result.Add(sb.ToString());
            return result;
        }

        public bool Has(string key) => _named.ContainsKey(key);
        public bool Flag(string key) => _named.TryGetValue(key, out var v) && v != "false";
        public string Get(string key, string fallback) => _named.TryGetValue(key, out var v) ? v : fallback;
        public string Require(string key) => _named.TryGetValue(key, out var v) ? v : throw new ArgumentException(Command + ": --" + key + " is required");
        public string Positional(int i, string what) => i < _positional.Count ? _positional[i] : throw new ArgumentException(Command + ": " + what + " is required");

        public override string ToString() =>
            // secrets are never arguments (only names of environment variables), so the
            // whole argument list is safe to log
            string.Join(" ", _positional.Concat(_named.Select(kv => "--" + kv.Key + " " + kv.Value)));
    }

    /// <summary>One JSON object per line on stdout; flushed so a crash keeps the record.</summary>
    internal static class Log
    {
        public static void Emit(string evt, params (string Key, object Value)[] fields)
        {
            var sb = new StringBuilder();
            sb.Append("{\"t\":\"").Append(DateTime.UtcNow.ToString("o")).Append("\",\"event\":").Append(Quote(evt));
            foreach (var (key, value) in fields)
            {
                sb.Append(',').Append(Quote(key)).Append(':');
                if (value is int || value is long) sb.Append(value);
                else if (value is bool b) sb.Append(b ? "true" : "false");
                else if (value == null) sb.Append("null");
                else sb.Append(Quote(value.ToString()));
            }
            sb.Append('}');
            Console.Out.WriteLine(sb.ToString());
            Console.Out.Flush();
        }

        private static string Quote(string s)
        {
            var sb = new StringBuilder("\"");
            foreach (var ch in s)
            {
                switch (ch)
                {
                    case '"': sb.Append("\\\""); break;
                    case '\\': sb.Append("\\\\"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    case '\t': sb.Append("\\t"); break;
                    default:
                        if (ch < 0x20) sb.Append("\\u").Append(((int)ch).ToString("x4"));
                        else sb.Append(ch);
                        break;
                }
            }
            return sb.Append('"').ToString();
        }
    }
}
