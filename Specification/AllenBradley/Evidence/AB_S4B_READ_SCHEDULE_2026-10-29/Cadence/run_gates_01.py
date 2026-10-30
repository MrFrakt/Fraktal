from pathlib import Path
import subprocess,sys
W=Path(__file__).parent;R=Path('C:/Users/SoftIndVM/Fraktal');H=R/'FraktalCore/HMI'
D='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/dart-sdk/bin/dart.exe'
F='C:/work/fraktal-toolchains/flutter-3.47.5/bin/cache/flutter_tools.snapshot'
commands=[('locked_dependencies_01',[D,F,'pub','get','--enforce-lockfile'],H),
 ('full_hmi_01',[D,F,'test','--no-pub','--reporter','expanded'],H),
 ('analyze_01',[D,F,'analyze','--no-pub'],H),
 ('windows_profile_01',[D,F,'build','windows','--profile','--no-pub'],H),
 ('plc_transfer_01',[sys.executable,str(W/'verify_plc_bindings_01.py')],R),
 ('configuration_stage_tests_01',[sys.executable,str(W/'test_configuration_stage_01.py')],R),
 ('prepare_peer_01',[sys.executable,str(W/'prepare_peer_qualification_01.py')],R),
 ('peer_qualification_01',[sys.executable,str(W/'qualify_peer_01.py')],R)]
for label,command,cwd in commands:
 print(label,flush=True)
 code=subprocess.run([sys.executable,str(W/'run_logged.py'),label,*command],cwd=cwd).returncode
 if code:raise SystemExit(code)
