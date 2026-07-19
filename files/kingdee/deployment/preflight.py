#!/usr/bin/env python3
from __future__ import annotations
import argparse, pathlib, sys, yaml
REQUIRED = {
 ('tenant','tenantId'), ('tenant','platformVersion'), ('kwc','version'),
 ('javaPlugin','sdkVersion'), ('javaPlugin','gatewayBaseUrl'), ('agentPlatform','version')
}
def main():
    parser=argparse.ArgumentParser(description='Validate C Kingdee deployment environment facts')
    parser.add_argument('config', nargs='?', default='kingdee/deployment/environment.local.yaml')
    parser.add_argument('--require-native-export', action='store_true')
    args=parser.parse_args(); path=pathlib.Path(args.config)
    if not path.exists(): print(f'ERROR: missing {path}; copy environment.template.yaml first'); return 2
    data=yaml.safe_load(path.read_text(encoding='utf-8')) or {}; errors=[]
    for section,key in sorted(REQUIRED):
        value=(data.get(section) or {}).get(key)
        if value is None or not str(value).strip() or 'FILL' in str(value): errors.append(f'{section}.{key}')
    url=str((data.get('javaPlugin') or {}).get('gatewayBaseUrl',''))
    if url and not url.startswith('https://'): errors.append('javaPlugin.gatewayBaseUrl must use https in tenant deployment')
    native=(data.get('productPackage') or {}).get('nativeExportFile','')
    if args.require_native_export and ('FILL' in str(native) or not pathlib.Path(native).exists()): errors.append('productPackage.nativeExportFile')
    if errors:
        print('PREFLIGHT FAILED:'); [print(' - '+e) for e in errors]; return 1
    print('PREFLIGHT PASS'); return 0
if __name__=='__main__': sys.exit(main())
