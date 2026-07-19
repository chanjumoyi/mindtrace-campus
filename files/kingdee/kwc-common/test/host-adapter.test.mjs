import test from 'node:test';
import assert from 'node:assert/strict';
import { KingdeeKwcHostAdapter } from '../dist/kingdee-host-adapter.js';

test('Kingdee host adapter maps tenant bridge without leaking platform APIs', async () => {
  const events = [];
  const adapter = new KingdeeKwcHostAdapter({
    getLocale: () => 'zh-CN',
    getAccessToken: () => 'token',
    getCurrentUser: () => ({ id: 7, username: 'demo', displayName: '演示用户', roles: ['student'], permissions: ['ai:invoke'] }),
    openPage: path => events.push(['navigate', path]),
    showMessage: (type, message) => events.push([type, message]),
    confirm: () => true,
    fireEvent: (name, payload) => events.push([name, payload])
  });
  assert.equal(await adapter.getAccessToken(), 'token');
  assert.equal((await adapter.getCurrentUser()).id, '7');
  adapter.navigate('/home');
  adapter.emit('ready', { ok: true });
  assert.deepEqual(events, [['navigate', '/home'], ['ready', { ok: true }]]);
});
