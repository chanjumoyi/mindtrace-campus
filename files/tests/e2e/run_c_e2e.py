#!/usr/bin/env python3
"""Live C acceptance test. Requires a running local stack; touches no A/B endpoints."""
from __future__ import annotations
import json, os, sys, time, uuid
from urllib.error import HTTPError
from urllib.request import Request, urlopen
BASE = os.getenv('XINJI_BASE_URL','http://127.0.0.1:8080').rstrip('/')

def call(method, path, body=None, token=None, headers=None, expected=(200,)):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode()
    h = {'Accept':'application/json'}
    if data is not None: h['Content-Type']='application/json'
    if token: h['Authorization']='Bearer '+token
    h.update(headers or {})
    req=Request(BASE+path,data=data,headers=h,method=method)
    try:
        with urlopen(req,timeout=10) as r: status=r.status; raw=r.read()
    except HTTPError as e: status=e.code; raw=e.read(); response_headers=e.headers
    else: response_headers=r.headers
    payload=json.loads(raw.decode() or '{}')
    if status not in expected: raise AssertionError(f'{method} {path}: HTTP {status}: {payload}')
    return status,payload,response_headers

def login(user,password):
    return call('POST','/api/v1/auth/login',{'username':user,'password':password})[1]['data']['accessToken']

def main():
    call('GET','/actuator/health')
    student=login(os.getenv('XINJI_STUDENT_USER','student_demo'),os.getenv('XINJI_STUDENT_PASSWORD','demo123'))
    admin=login(os.getenv('XINJI_ADMIN_USER','admin_demo'),os.getenv('XINJI_ADMIN_PASSWORD','admin123'))
    call('GET','/api/v1/audit-logs',token=student,expected=(403,))
    call('GET','/api/v1/audit-logs',token=admin)
    key='e2e-'+uuid.uuid4().hex
    req={'moduleCode':'COMMON','operation':'echo','input':{'source':'c-e2e'},'timeoutMs':1000}
    _,first,_=call('POST','/api/v1/ai/invoke',req,student,{'Idempotency-Key':key})
    _,second,_=call('POST','/api/v1/ai/invoke',req,student,{'Idempotency-Key':key})
    assert first['data']['replayed'] is False and second['data']['replayed'] is True
    call_id=first['data']['callId']
    _,attempts,_=call('GET',f'/api/v1/ai/call-logs/{call_id}/attempts',token=student)
    assert len(attempts['data']) >= 1

    # Recursive canonical JSON hashing: key order changes replay; semantic changes conflict.
    reordered={'timeoutMs':1000,'input':{'source':'c-e2e'},'operation':'echo','moduleCode':'COMMON'}
    _,replayed,_=call('POST','/api/v1/ai/invoke',reordered,student,{'Idempotency-Key':key})
    assert replayed['data']['replayed'] is True
    changed={'moduleCode':'COMMON','operation':'echo','input':{'source':'changed'},'timeoutMs':1000}
    call('POST','/api/v1/ai/invoke',changed,student,{'Idempotency-Key':key},expected=(409,))

    # The infrastructure-only mock fails twice, so the gateway must succeed on attempt 3.
    retry_key='retry-'+uuid.uuid4().hex
    retry_req={'moduleCode':'COMMON','operation':'simulate-error','input':{},'timeoutMs':2000}
    _,retried,_=call('POST','/api/v1/ai/invoke',retry_req,student,{'Idempotency-Key':retry_key})
    assert retried['data']['attempts'] == 3
    _,retry_attempts,_=call('GET',f"/api/v1/ai/call-logs/{retried['data']['callId']}/attempts",token=student)
    assert len(retry_attempts['data']) == 3 and retry_attempts['data'][0]['retryable'] is True

    # Request-specific hard deadline must surface as 504 instead of waiting for the mock's delayed response.
    timeout_key='timeout-'+uuid.uuid4().hex
    timeout_req={'moduleCode':'COMMON','operation':'simulate-timeout','input':{},'timeoutMs':300}
    started=time.monotonic()
    _,timeout_payload,_=call('POST','/api/v1/ai/invoke',timeout_req,student,{'Idempotency-Key':timeout_key},expected=(504,))
    assert timeout_payload['code'] == 'AGENT_TIMEOUT' and time.monotonic()-started < 2.0

    service=os.getenv('XINJI_SERVICE_TOKEN','')
    if service:
        key='svc-'+uuid.uuid4().hex
        call('POST','/api/v1/ai/invoke',req,service,{'Idempotency-Key':key})
        call('GET','/api/v1/audit-logs',token=service,expected=(403,))
    print('C live E2E: PASS')
    return 0
if __name__=='__main__': sys.exit(main())
