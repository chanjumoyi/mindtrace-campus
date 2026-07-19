#!/usr/bin/env python3
"""Build a checksummed C-only delivery bundle. Platform-native exports are included only when explicitly supplied."""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'deliverables/package'
VERSION='1.1.0'

def run(*cmd, cwd=None):
    print('+',' '.join(map(str,cmd))); subprocess.run(cmd,cwd=cwd or ROOT,check=True)

def copy(src, dst):
    src=ROOT/src if isinstance(src,str) else src
    dst.parent.mkdir(parents=True,exist_ok=True)
    if src.is_dir(): shutil.copytree(src,dst,dirs_exist_ok=True)
    else: shutil.copy2(src,dst)

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--environment'); ap.add_argument('--include-native-export',action='store_true'); ap.add_argument('--skip-tests',action='store_true'); args=ap.parse_args()
    if args.include_native_export:
        if not args.environment: raise SystemExit('--environment is required with --include-native-export')
        run(sys.executable,'kingdee/deployment/preflight.py',args.environment,'--require-native-export')
    run(sys.executable,'kingdee/tools/build_c_assets.py')
    if not args.skip_tests:
        run(sys.executable,'tests/run_c_verification.py')
    OUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='xinji-c-delivery-') as td:
        stage=pathlib.Path(td)/f'xinji-c-delivery-{VERSION}'
        include=[
          'contracts/openapi.yaml','kingdee/generated-assets-manifest.json','kingdee/domain-models/common-foundation-models.yaml',
          'kingdee/domain-models/generated','kingdee/agent-tools/tool-registration.yaml','kingdee/agent-tools/schemas','kingdee/agent-tools/generated',
          'kingdee/kwc-common/dist','kingdee/kwc-common/component-manifest.json','kingdee/java-plugin/src/main/java',
          'kingdee/java-plugin/src/test','kingdee/java-plugin/scripts','kingdee/java-plugin/pom.xml',
          'kingdee/java-plugin/cosmic-template','kingdee/java-plugin/README.md','kingdee/deployment/install-package-manifest.yaml',
          'local/backend/pom.xml','local/backend/Dockerfile','local/backend/src/main/java','local/backend/src/main/resources',
          'local/backend/src/test/java','local/backend/src/test/resources',
          'kingdee/deployment/environment.template.yaml','kingdee/deployment/preflight.py','tests/e2e/run_c_e2e.py',
          'deliverables/test-report/c-static-acceptance.json','deliverables/test-report/c-verification-report.json','docs/C任务完成与苍穹部署操作手册.md','docs/C任务交付说明.md','.env.example','docker-compose.yml'
        ]
        for item in include:
            source = ROOT / item
            if source.exists():
                copy(item, stage / item)
            elif not args.skip_tests or 'test-report' not in item:
                raise FileNotFoundError(source)
        kwc_zip=OUT/'xinji-kwc-common-1.0.0.zip'
        if kwc_zip.exists(): copy(kwc_zip,stage/'artifacts'/kwc_zip.name)
        # Compile a Java 8 class bundle without assuming a tenant SDK.
        classes=stage/'artifacts/plugin-core-classes'; classes.mkdir(parents=True,exist_ok=True)
        run('javac','--release','8','-d',str(classes),str(ROOT/'kingdee/java-plugin/src/main/java/com/xinji/kingdee/FoundationPluginCore.java'))
        jar=stage/'artifacts'/f'xinji-kingdee-plugin-core-{VERSION}.jar'
        run('jar','cf',str(jar),'-C',str(classes),'.')
        shutil.rmtree(classes)
        if args.environment:
            copy(pathlib.Path(args.environment).resolve(),stage/'deployment/environment.local.yaml')
        if args.include_native_export:
            import yaml
            env=yaml.safe_load(pathlib.Path(args.environment).read_text(encoding='utf-8'))
            native=pathlib.Path(env['productPackage']['nativeExportFile']).resolve()
            copy(native,stage/'tenant-native-assets'/native.name)
        files=sorted(p for p in stage.rglob('*') if p.is_file())
        manifest={str(p.relative_to(stage)):digest(p) for p in files}
        (stage/'MANIFEST.sha256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        out=OUT/f'xinji-c-delivery-{VERSION}.zip'
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
            for p in sorted(stage.rglob('*')):
                if p.is_file(): z.write(p,p.relative_to(stage.parent))
        print(out)
    return 0
if __name__=='__main__': sys.exit(main())
