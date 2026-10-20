import assert from 'node:assert/strict';
import test from 'node:test';
import { useGuidedDemoStore } from '../src/store/useGuidedDemoStore';
import { useLpbfEngineeringStore } from '../src/store/useLpbfEngineeringStore';
import { useLpbfWorkflowStore } from '../src/store/useLpbfWorkflowStore';

test('entering the run step selects Screening without submitting a job', () => {
  const before = useLpbfEngineeringStore.getState();
  const stage = useLpbfWorkflowStore.getState().stage;
  try {
    useLpbfEngineeringStore.setState({ mode: 'standard' });
    useGuidedDemoStore.setState({ active: true, step: 1 });
    useGuidedDemoStore.getState().next();
    assert.equal(useGuidedDemoStore.getState().step, 2);
    assert.equal(useLpbfEngineeringStore.getState().mode, 'screening');
    assert.equal(useLpbfEngineeringStore.getState().job, before.job);
    assert.equal(useLpbfEngineeringStore.getState().busy, before.busy);
    useLpbfEngineeringStore.setState({ mode: 'standard' });
    useGuidedDemoStore.getState().goTo(3);
    useGuidedDemoStore.getState().back();
    assert.equal(useLpbfEngineeringStore.getState().mode, 'screening');
  } finally {
    useLpbfEngineeringStore.setState(before);
    useLpbfWorkflowStore.setState({ stage });
    useGuidedDemoStore.setState({ active: false, step: 1 });
  }
});

function navigationEnvironment(run: (events: CustomEvent[], timers: (() => void)[], mount: () => void) => void) {
  const mode = useLpbfEngineeringStore.getState().mode;
  const stage = useLpbfWorkflowStore.getState().stage;
  const saved = ['window', 'document', 'setTimeout'].map(key => [key, Object.getOwnPropertyDescriptor(globalThis, key)] as const);
  const events: CustomEvent[] = [];
  const timers: (() => void)[] = [];
  let mounted = false;
  const location = { href: 'http://localhost:3021/?lpbfStage=material&lpbfSubTab=legacy#home' };
  Object.defineProperty(globalThis, 'window', { configurable: true, value: {
    location,
    history: { replaceState: (_state: unknown, _title: string, next: URL) => { location.href = String(next); } },
    dispatchEvent: (event: CustomEvent) => { events.push(event); return true; },
  } });
  Object.defineProperty(globalThis, 'document', { configurable: true, value: { querySelector: () => mounted ? {} : null } });
  Object.defineProperty(globalThis, 'setTimeout', { configurable: true, value: (callback: () => void) => { timers.push(callback); return 1; } });
  try { run(events, timers, () => { mounted = true; }); }
  finally {
    for (const [key, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor);
      else Reflect.deleteProperty(globalThis, key);
    }
    useGuidedDemoStore.setState({ active: false, step: 1 });
    useLpbfEngineeringStore.setState({ mode });
    useLpbfWorkflowStore.setState({ stage });
  }
}

test('run-step navigation reaches Thermal Simulation before the workspace mounts', () => {
  navigationEnvironment(events => {
    useLpbfWorkflowStore.setState({ stage: 'material' });
    useGuidedDemoStore.setState({ active: true, step: 1 });
    useGuidedDemoStore.getState().next();
    assert.deepEqual(events[0].detail, { tabId: '3d-distortion-lab', lpbfStage: 'thermal' });
    assert.equal(useLpbfWorkflowStore.getState().stage, 'thermal');
    const url = new URL(window.location.href);
    assert.equal(url.searchParams.get('lpbfStage'), 'thermal');
    assert.equal(url.searchParams.has('lpbfSubTab'), false);
  });
});

test('a delayed workspace mount cannot return an exited tour to an old stage', () => {
  navigationEnvironment((events, timers, mount) => {
    useGuidedDemoStore.setState({ active: true, step: 1 });
    useGuidedDemoStore.getState().goTo(2);
    useGuidedDemoStore.setState({ active: false });
    const sent = events.length;
    mount();
    for (const callback of timers.splice(0)) callback();
    assert.equal(events.length, sent);
  });
});

test('a delayed workspace mount cannot return the tour to a previous step', () => {
  navigationEnvironment((events, timers, mount) => {
    useGuidedDemoStore.setState({ active: true, step: 1 });
    useGuidedDemoStore.getState().goTo(2);
    useGuidedDemoStore.getState().goTo(3);
    const sent = events.length;
    mount();
    for (const callback of timers.splice(0)) callback();
    const retried = events.slice(sent);
    assert.equal(retried.length, 1);
    assert.equal(retried[0].detail.lpbfStage, 'melt-pool');
    assert.equal(useLpbfWorkflowStore.getState().stage, 'melt-pool');
  });
});
