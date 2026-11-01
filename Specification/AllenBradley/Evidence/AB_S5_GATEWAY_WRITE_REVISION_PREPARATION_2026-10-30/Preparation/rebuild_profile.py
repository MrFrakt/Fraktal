from pathlib import Path
D=Path(__file__).parent
script=D/'build_gateway_profile_03.py'
exec(compile(script.read_text().replace('qualification_app_03','qualification_app_04'),str(script),'exec'))
