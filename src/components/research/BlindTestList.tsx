import React, { useEffect, useState } from 'react';
import type { BlindList } from '../../data/lpbfUserBlind';
import { blindClient, describeBlindError } from '../../services/lpbfUserBlindClient';
import { buttonClass, Empty } from './ResearchControls';

export function BlindTestListView({ list, error, onLoad, onRefresh, activeKey = null }: { list: BlindList | null; error: string | null; onLoad: (freezeKey: string) => void; onRefresh: () => void; activeKey?: string | null }) {
  return <section aria-labelledby="blind-your-tests-h" className="space-y-3" data-testid="blind-your-tests">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <h3 id="blind-your-tests-h" className="text-base font-semibold text-slate-100">Your tests</h3>
      <button type="button" className={buttonClass} onClick={onRefresh}>Refresh the list</button>
    </div>
    {error && <p role="alert" className="text-xs text-rose-200">{error}</p>}
    {!list && !error && <p className="text-xs text-slate-400">Loading the list from the worker...</p>}
    {list && list.entries.length === 0 && <Empty>No blind test is stored on this computer yet.</Empty>}
    {list && list.entries.length > 0 && <div className="max-w-full overflow-auto" tabIndex={0} role="region" aria-label="Your tests (scrollable)">
      <table className="w-full whitespace-nowrap text-xs text-slate-300 [&_td]:pr-3 [&_th]:pr-3 [&_th]:text-left">
        <caption className="sr-only">Blind tests stored on this computer</caption>
        <thead><tr><th scope="col">Block</th><th scope="col">Alloy</th><th scope="col">Created</th><th scope="col">Conditions</th><th scope="col">State</th><th scope="col">Attempts</th><th scope="col">Latest served status</th><th scope="col">Latest blindness</th><th scope="col"><span className="sr-only">Open</span></th></tr></thead>
        <tbody>{list.entries.map(e => <tr key={e.freezeKey} aria-current={activeKey === e.freezeKey ? 'true' : undefined}>
          <td>{e.blockLabel ?? 'unreadable record'}</td><td>{e.alloy ?? ''}</td><td>{e.createdAt ?? ''}</td><td>{e.counts?.conditions ?? ''}</td><td>{e.state}</td><td>{e.attempts ?? ''}</td>
          <td>{e.latestStatus?.served ?? 'none yet'}</td><td>{e.latestStatus?.blindness ?? 'none yet'}</td>
          <td>{e.state !== 'unreadable' && <button type="button" className={buttonClass} onClick={() => onLoad(e.freezeKey)}>Open {e.blockLabel ?? e.freezeKey.slice(0, 8)}</button>}</td>
        </tr>)}</tbody>
      </table>
    </div>}
    {list && list.total > list.entries.length && <p className="text-xs text-slate-500">Showing {list.entries.length} of {list.total} tests.</p>}
    {list && !list.ledgerOk && <p role="alert" className="text-xs text-rose-200">The ledger of this store did not verify. Treat the order of events as unconfirmed.</p>}
  </section>;
}

/** Loads the list from the worker, so tests are found again after browser storage was cleared. */
export function BlindTestList({ onLoad, onListed, refreshKey = 0, activeKey = null }: { onLoad: (freezeKey: string) => void; onListed?: (list: BlindList) => void; refreshKey?: number; activeKey?: string | null }) {
  const [list, setList] = useState<BlindList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    blindClient.list(0, 50).then(l => { if (live) { setList(l); setError(null); onListed?.(l); } }).catch(e => { if (live) setError(describeBlindError(e)); });
    return () => { live = false; };
  }, [refreshKey, tick]);
  return <BlindTestListView list={list} error={error} onLoad={onLoad} onRefresh={() => setTick(t => t + 1)} activeKey={activeKey} />;
}

export default BlindTestList;
