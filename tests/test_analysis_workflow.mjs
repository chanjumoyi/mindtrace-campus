import assert from 'node:assert/strict';
import test from 'node:test';
import { runTrackedAnalysis } from '../local/frontend/analysis-workflow.mjs';

test('tracked analysis completes the public task state machine', async () => {
  const events = [];
  const api = async (path, options) => {
    const body = JSON.parse(options.body);
    events.push({ path, body });
    if (path === '/tasks') return { id: 'task-1', status: 'PENDING' };
    return { id: 'task-1', ...body };
  };

  const result = await runTrackedAnalysis({
    api,
    taskType: 'SANDPLAY_ANALYSIS',
    title: '心理沙盘结构化观察',
    requestRef: 'sandplay:test',
    invoke: async () => {
      events.push({ invoke: true });
      return { callId: 'call-1', data: { mock: true } };
    }
  });

  assert.equal(result.task.status, 'SUCCEEDED');
  assert.equal(result.gateway.callId, 'call-1');
  assert.deepEqual(events.map(event => event.body?.status || (event.invoke ? 'INVOKE' : 'CREATE')), [
    'CREATE',
    'RUNNING',
    'INVOKE',
    'SUCCEEDED'
  ]);
  assert.equal(events[3].body.resultRef, 'call-1');
});

test('tracked analysis marks the task failed without storing sensitive error text', async () => {
  const events = [];
  const api = async (path, options) => {
    const body = JSON.parse(options.body);
    events.push({ path, body });
    if (path === '/tasks') return { id: 'task-2', status: 'PENDING' };
    return { id: 'task-2', ...body };
  };
  const failure = Object.assign(new Error('Bearer secret-value was rejected'), { code: 'HTTP 502' });

  await assert.rejects(() => runTrackedAnalysis({
    api,
    taskType: 'HTP_ANALYSIS',
    title: '房树人客观观察',
    requestRef: 'file:file-1',
    invoke: async () => { throw failure; }
  }), error => error === failure && error.taskId === 'task-2');

  const failed = events.at(-1).body;
  assert.equal(failed.status, 'FAILED');
  assert.equal(failed.errorCode, 'HTTP_502');
  assert.equal(failed.errorMessage.includes('secret-value'), false);
});

test('task transition failure does not hide the original analysis error', async () => {
  const original = new Error('agent unavailable');
  const trackingFailure = new Error('task backend unavailable');
  let transitionCount = 0;
  const api = async (path) => {
    if (path === '/tasks') return { id: 'task-3' };
    transitionCount += 1;
    if (transitionCount === 2) throw trackingFailure;
    return { id: 'task-3', status: 'RUNNING' };
  };

  await assert.rejects(() => runTrackedAnalysis({
    api,
    taskType: 'SANDPLAY_ANALYSIS',
    title: '心理沙盘结构化观察',
    requestRef: 'sandplay:test-3',
    invoke: async () => { throw original; }
  }), error => error === original && error.taskTrackingError === trackingFailure);
});
test('running transition failure is converted into a failed tracked task', async () => {
  const runningFailure = Object.assign(new Error('cannot start task'), { code: 'HTTP_503' });
  const statuses = [];
  let invoked = false;
  const api = async (path, options) => {
    if (path === '/tasks') return { id: 'task-4' };
    const body = JSON.parse(options.body);
    statuses.push(body.status);
    if (body.status === 'RUNNING') throw runningFailure;
    return { id: 'task-4', ...body };
  };

  await assert.rejects(() => runTrackedAnalysis({
    api,
    taskType: 'HTP_ANALYSIS',
    title: '房树人客观观察',
    requestRef: 'file:file-4',
    invoke: async () => { invoked = true; }
  }), error => error === runningFailure && error.taskId === 'task-4');

  assert.deepEqual(statuses, ['RUNNING', 'FAILED']);
  assert.equal(invoked, false);
});