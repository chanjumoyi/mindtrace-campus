#!/usr/bin/env sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

echo '[1/6] JavaScript 语法'
node --check local/frontend/app.js
node --check local/frontend/api.js
node --check local/frontend/components.js
node --check local/mock-agent/server.js

echo '[2/6] JSON 文件'
python3 - <<'PY'
import json
from pathlib import Path
for p in Path('.').rglob('*.json'):
    if 'node_modules' in p.parts: continue
    json.loads(p.read_text(encoding='utf-8'))
    print('OK', p)
PY

echo '[3/6] YAML 文件'
python3 - <<'PY'
from pathlib import Path
try:
    import yaml
except Exception:
    print('PyYAML 未安装：仅检查 YAML 非空与制表符。')
    for p in list(Path('.').rglob('*.yaml')) + list(Path('.').rglob('*.yml')):
        text=p.read_text(encoding='utf-8')
        assert text.strip() and '\t' not in text, p
        print('BASIC OK', p)
else:
    for p in list(Path('.').rglob('*.yaml')) + list(Path('.').rglob('*.yml')):
        yaml.safe_load(p.read_text(encoding='utf-8'))
        print('OK', p)
PY

echo '[4/6] Java 源码基本词法检查'
python3 - <<'PY'
from pathlib import Path

def check_java(path):
    s=path.read_text(encoding='utf-8')
    stack=[]; i=0; state='code'; quote=''; line=1
    pairs={')':'(',']':'[','}':'{'}
    while i < len(s):
        c=s[i]; n=s[i+1] if i+1<len(s) else ''
        if c=='\n': line+=1
        if state=='code':
            if c=='/' and n=='/': state='line'; i+=2; continue
            if c=='/' and n=='*': state='block'; i+=2; continue
            if c in ('"', "'"): state='string'; quote=c; i+=1; continue
            if c in '([{': stack.append((c,line))
            elif c in ')]}':
                if not stack or stack[-1][0] != pairs[c]: raise AssertionError(f'{path}:{line}: bracket mismatch')
                stack.pop()
        elif state=='line':
            if c=='\n': state='code'
        elif state=='block':
            if c=='*' and n=='/': state='code'; i+=2; continue
        elif state=='string':
            if c=='\\': i+=2; continue
            if c==quote: state='code'
            elif c=='\n' and quote=='"': raise AssertionError(f'{path}:{line}: newline in string literal')
        i+=1
    assert state not in ('string','block'), f'{path}: unterminated {state}'
    assert not stack, f'{path}: unclosed brackets {stack[-3:]}'

for p in Path('local/backend/src').rglob('*.java'):
    check_java(p); print('OK',p)
PY

echo '[5/6] 编译无第三方依赖的苍穹插件核心'
rm -rf /tmp/xinji-plugin-check && mkdir -p /tmp/xinji-plugin-check
javac -encoding UTF-8 -d /tmp/xinji-plugin-check kingdee/java-plugin/src/main/java/com/xinji/kingdee/FoundationPluginCore.java

echo '[6/6] Maven 测试（环境可用时）'
if command -v mvn >/dev/null 2>&1; then
  (cd local/backend && mvn test)
else
  echo 'SKIP: 当前环境没有 Maven。请在 JDK17+ / Maven3.6.3+ 环境运行 cd local/backend && mvn test'
fi

echo '静态验证完成。'
