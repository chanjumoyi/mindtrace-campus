#!/usr/bin/env python3
from pathlib import Path
import json, subprocess, sys, time, unittest, yaml
ROOT=Path(__file__).resolve().parents[1]
start=time.time()
loader=unittest.TestLoader(); suite=unittest.TestSuite()
for folder in ('tests/contract','tests/security'): suite.addTests(loader.discover(str(ROOT/folder), pattern='test_*.py'))
result=unittest.TextTestRunner(verbosity=2).run(suite)
report={
 'suite':'C static acceptance','passed':result.wasSuccessful(),'testsRun':result.testsRun,
 'failures':len(result.failures),'errors':len(result.errors),'durationMs':round((time.time()-start)*1000),
 'liveE2EExecuted':False,'note':'Live E2E is executed separately against a running Docker/tenant environment.'
}
out=ROOT/'deliverables/test-report/c-static-acceptance.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(out)
sys.exit(0 if result.wasSuccessful() else 1)
