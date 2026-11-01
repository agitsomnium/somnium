
import test from 'node:test';
import assert from 'node:assert/strict';
import { downloadMaterial } from './materialDownload.js';

const FILE = { id: 'm1', lessonId: 'L1', path: '/files/m1.pdf', filename: 'm1.pdf' };

function deferred() {
  let resolve, reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

function makeDeps(overrides = {}) {
  const state = {
    access: { userId: 'u1', epoch: 1, canLearn: true, lessonAvailable: true },
    materials: [{ id: 'm1' }],
    blob: { size: 10 },
    calls: { list: 0, download: 0, offer: 0 },
    offered: [],
  };
  const deps = {
    access: () => ({ ...state.access }),
    listMaterials: async () => { state.calls.list++; return state.materials; },
    download: async () => { state.calls.download++; return state.blob; },
    offer: (blob, filename) => { state.calls.offer++; state.offered.push({ blob, filename }); },
    ...overrides,
  };
  return { deps, state };
}

test('offers when authorized throughout', async () => {
  const { deps, state } = makeDeps();
  const result = await downloadMaterial(FILE, deps);
  assert.equal(result, true);
  assert.equal(state.calls.offer, 1);
  assert.deepEqual(state.offered[0], { blob: state.blob, filename: 'm1.pdf' });
});

test('neutral 30s refresh with new object, same permission, still offers once', async () => {
  const d = deferred();
  const started = deferred();
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; started.resolve(); return d.promise; };
  const p = downloadMaterial(FILE, deps);
  await started.promise;
  // Simulate a neutral background refresh: brand-new access object, same epoch/permissions.
  state.access = { userId: 'u1', epoch: 1, canLearn: true, lessonAvailable: true };
  d.resolve(state.blob);
  assert.equal(await p, true);
  assert.equal(state.calls.offer, 1);
});

test('permission revoked while downloading suppresses offer', async () => {
  const d = deferred();
  const started = deferred();
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; started.resolve(); return d.promise; };
  const p = downloadMaterial(FILE, deps);
  await started.promise;
  state.access = { ...state.access, canLearn: false };
  d.resolve(state.blob);
  assert.equal(await p, false);
  assert.equal(state.calls.offer, 0);
});

test('logout/relogin same id but epoch changed suppresses offer', async () => {
  const d = deferred();
  const started = deferred();
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; started.resolve(); return d.promise; };
  const p = downloadMaterial(FILE, deps);
  await started.promise;
  state.access = { userId: 'u1', epoch: 2, canLearn: true, lessonAvailable: true };
  d.resolve(state.blob);
  assert.equal(await p, false);
  assert.equal(state.calls.offer, 0);
});

test('account change suppresses offer', async () => {
  const d = deferred();
  const started = deferred();
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; started.resolve(); return d.promise; };
  const p = downloadMaterial(FILE, deps);
  await started.promise;
  state.access = { userId: 'u2', epoch: 1, canLearn: true, lessonAvailable: true };
  d.resolve(state.blob);
  assert.equal(await p, false);
  assert.equal(state.calls.offer, 0);
});

test('lesson revoked but other access remains suppresses offer', async () => {
  const d = deferred();
  const started = deferred();
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; started.resolve(); return d.promise; };
  const p = downloadMaterial(FILE, deps);
  await started.promise;
  state.access = { ...state.access, lessonAvailable: false };
  d.resolve(state.blob);
  assert.equal(await p, false);
  assert.equal(state.calls.offer, 0);
});

test('server list without file never calls download', async () => {
  const { deps, state } = makeDeps();
  state.materials = [{ id: 'other' }];
  await assert.rejects(downloadMaterial(FILE, deps), /현재 내려받을 수 없는 자료입니다\./);
  assert.equal(state.calls.download, 0);
  assert.equal(state.calls.offer, 0);
});

test('storage error propagates and no offer', async () => {
  const { deps, state } = makeDeps();
  deps.download = async () => { state.calls.download++; throw new Error('storage full'); };
  await assert.rejects(downloadMaterial(FILE, deps), /storage full/);
  assert.equal(state.calls.offer, 0);
});

test('initially unauthorized makes no backend calls', async () => {
  const { deps, state } = makeDeps();
  state.access = { userId: '', epoch: 1, canLearn: true, lessonAvailable: true };
  await assert.rejects(downloadMaterial(FILE, deps), /현재 자료 이용 권한이 없습니다\./);
  assert.equal(state.calls.list, 0);
  assert.equal(state.calls.download, 0);
  assert.equal(state.calls.offer, 0);
});

test('initially !canLearn makes no backend calls', async () => {
  const { deps, state } = makeDeps();
  state.access = { ...state.access, canLearn: false };
  await assert.rejects(downloadMaterial(FILE, deps), /현재 자료 이용 권한이 없습니다\./);
  assert.equal(state.calls.list, 0);
  assert.equal(state.calls.download, 0);
});

test('initially !lessonAvailable makes no backend calls', async () => {
  const { deps, state } = makeDeps();
  state.access = { ...state.access, lessonAvailable: false };
  await assert.rejects(downloadMaterial(FILE, deps), /현재 자료 이용 권한이 없습니다\./);
  assert.equal(state.calls.list, 0);
  assert.equal(state.calls.download, 0);
});

test('network error from listMaterials propagates', async () => {
  const { deps, state } = makeDeps();
  deps.listMaterials = async () => { state.calls.list++; throw new Error('network down'); };
  await assert.rejects(downloadMaterial(FILE, deps), /network down/);
  assert.equal(state.calls.download, 0);
  assert.equal(state.calls.offer, 0);
});
