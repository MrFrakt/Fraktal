from pathlib import Path
W=Path(__file__).parent
source=(W/'summarize_runtime_01.py').read_text(encoding='utf-8')
before="optional('paired_replay_01.json')"
assert source.count(before)==1
source=source.replace(before,"optional('paired_replay_03.json')")
before="save('runtime_summary_01.json',summary)"
assert source.count(before)==1
source=source.replace(before,"summary['partialFixtureProof']=dict(fullFixturePassed=False,completedCases=25,expectedCases=41,partialReplayFile='paired_replay_03.json',failure='part snapshot changed during every bounded read',desktopStageReached=False)\n"+before)
exec(compile(source,str(W/'summarize_runtime_01.py'),'exec'),{'__file__':__file__})
