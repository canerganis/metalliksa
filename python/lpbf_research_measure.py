"""Manual D-12 research-only measurements, not a benchmark or runtime dependency.

Run with the pinned Windows Python: python -B python/lpbf_research_measure.py.
The cap probe injects source-distinct synthetic duplicates; it changes no real
declared manifest. No served solver or measured target is called. Stdout is JSON.
"""
from __future__ import annotations
import copy
import json
import statistics
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import lpbf_research_arm as arm
import lpbf_research_cache as cache
import lpbf_research_codes as codes
import lpbf_research_models as models


def request(alloy, stage='band'):
    return dict(schemaVersion=models.REQUEST_SCHEMA_VERSION,supersedeKey='p8-research:melt-pool',
                clientRequestId='d12-measurement',stage=stage,timeBudgetMs=None,
                process=dict(material=alloy,laserPower_W=200.,scanSpeed_mm_s=800.,beamDiameter_um=80.,
                             preheatTemp_C=20.,laserWavelength='IR_1064nm',absorptionModel='flat-plate'),
                propertyContext={'kind':'nominal'})


class TimedEngine(arm.Engine):
    def __init__(self, cap=False):
        self.cap=cap
        self.samples={}

    def manifest(self,module,context,options):
        plan=super().manifest(module,context,options)
        if self.cap and module in models.BAND_ORDER:
            plan=copy.deepcopy(plan)
            while len(plan['arms'])<80:
                row=copy.deepcopy(plan['arms'][0]);index=len(plan['arms'])
                row['armId']=f'd12-synthetic:{module}:{index}'
                row['inputs']=({**row['inputs'],'syntheticCapSourceId':row['armId']} if isinstance(row['inputs'],dict)
                               else {'syntheticCapSourceId':row['armId'],'tuple':row['inputs']})
                row['descriptor'].update(armId=row['armId'],label='Synthetic source-distinct cap probe',aliasArmIds=[])
                plan['arms'].append(row)
        return plan

    def evaluate_arm(self,module,context,options,spec,upstream):
        start=time.perf_counter()
        try:return super().evaluate_arm(module,context,options,spec,upstream)
        finally:self.samples.setdefault(module,[]).append((time.perf_counter()-start)*1000)


def percentile(values,p):
    ordered=sorted(values)
    return ordered[round((len(ordered)-1)*p)]


def measure(alloy,cap=False):
    engine=TimedEngine(cap);logs=[]
    deps=replace(models.default_dependencies(),engine=engine,cache=cache.ResearchLRU(),log=logs.append)
    stages={}
    for stage in ('nominal','band'):
        deps.cache.clear()
        for temperature in ('cold','warm'):
            start=time.perf_counter();stdout,exit_code=models.run(json.dumps(request(alloy,stage)),deps)
            elapsed=(time.perf_counter()-start)*1000;r=json.loads(stdout)
            stages[stage+'_'+temperature]=dict(ms=elapsed,responseBytes=len(stdout.encode('utf-8')),
                success=r['success'],reasonCode=r.get('reasonCode'),exitCode=exit_code)
            print(f'D12 {alloy} cap={cap} {stage}_{temperature}: {elapsed:.1f} ms, {r.get("reasonCode")}',file=sys.stderr,flush=True)
    # Read the complete result once from the warm cache without bypassing numeric work.
    req=request(alloy);ctx=models.research_context.resolve(req,deps.properties)
    complete=models._respond(deps,json.dumps(req),time.perf_counter())
    req.update(sender='blind-freeze',supersedeKey='p8-research:blind:'+'a'*16,
               relay=dict(kind=codes.RELAY_KIND,previewSha256='a'*64,conditionOrdinal=0))
    subset=models.blind_relay_subset(req,ctx,complete['requestKey'],complete['identity'],complete['digests'],complete['researchModels'],complete['labels'])
    relay_chars=len(codes.canonical_json(subset))
    # Confirm the real transport refuses an oversized relay without changing its cap.
    relay_stdout,_=models.run(json.dumps(req),deps);relay_response=json.loads(relay_stdout)
    chunks=[];chunk_deps=replace(deps,cache=cache.ResearchLRU());chunk_request=request(alloy)
    chunk_request['timeBudgetMs']=1500
    previous=None
    fallback_ms=None
    for _ in range(500):
        start=time.perf_counter();stdout,_=models.run(json.dumps(chunk_request),chunk_deps)
        r=json.loads(stdout);chunks.append((time.perf_counter()-start)*1000)
        if not r.get('success') or r.get('progress',{}).get('complete'):break
        done=r.get('progress',{}).get('armsDone')
        print(f'D12 chunk {alloy} cap={cap}: {done}/{r.get("progress",{}).get("armsTotal")}',file=sys.stderr,flush=True)
        if done==previous:
            fallback=request(alloy);start=time.perf_counter()
            stdout,_=models.run(json.dumps(fallback),chunk_deps)
            fallback_ms=(time.perf_counter()-start)*1000
            r=json.loads(stdout)
            break
        previous=done
    start=time.perf_counter();describe,_=models.run(json.dumps(request(alloy,'describe')),deps)
    describe_ms=(time.perf_counter()-start)*1000
    band=complete['researchModels']
    cache_bytes=sum(len(cache.canonical(deps.cache.get(key)).encode('utf-8')) for key in deps.cache.keys())
    if any('arm failed:' in line or 'module assembly failed:' in line for line in logs):
        raise RuntimeError('invalid timing probe: an evaluator error occurred; do not use these timings')
    return dict(alloy=alloy,capProbe=cap,stages=stages,
        perArmMs={m:dict(n=len(v),p50=statistics.median(v),p95=percentile(v,.95),max=max(v)) for m,v in engine.samples.items()},
        manifests={m:len(band[m].get('band',{}).get('manifest',[])) for m in models.BAND_ORDER},
        completeResponseBytes=len(codes.canonical_json(complete).encode('utf-8')),
        relayCharacters=relay_chars,relayCap=codes.RELAY_SUBSET_MAX_CHARS,relayResponseReason=relay_response.get('reasonCode'),
        relayResponseCause=relay_response.get('cause'),cacheEntries=len(deps.cache),cacheBytes=cache_bytes,
        chunkCount=len(chunks),chunkMs=dict(p50=statistics.median(chunks),p95=percentile(chunks,.95),max=max(chunks)),
        chunkComplete=r.get('progress',{}).get('complete'),stalledFallbackMs=fallback_ms,
        describeMs=describe_ms,describeSuccess=json.loads(describe)['success'],
        logs=list(dict.fromkeys(logs)))


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--cap-adhoc':
        deps=replace(models.default_dependencies(),engine=TimedEngine(cap=True))
        stdout,exit_code=models.run(json.dumps(request(sys.argv[2])),deps)
        r=json.loads(stdout)
        print(json.dumps(dict(success=r['success'],reasonCode=r.get('reasonCode'),exitCode=exit_code)))
        return
    output=Path(sys.argv[2]) if len(sys.argv)==3 and sys.argv[1]=='--output' else None
    if output is not None:output.write_text('',encoding='utf-8')
    def emit(value):
        line=json.dumps(value,sort_keys=True)
        print(line,flush=True)
        if output is not None:
            with output.open('a',encoding='utf-8') as stream:stream.write(line+'\n')
    results=[]
    for alloy in ('ti6al4v','alsi10mg'):
        results.append(measure(alloy))
        emit(results[-1])
    for alloy in ('ti6al4v','alsi10mg'):
        results.append(measure(alloy,cap=True))
        emit(results[-1])
    # A real clean ad-hoc process, without a preloaded interpreter or persistent cache.
    for alloy in ('ti6al4v','alsi10mg'):
        start=time.perf_counter()
        proc=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('lpbf_research_models.py'))],
                            input=json.dumps(request(alloy)),capture_output=True,text=True,timeout=180)
        r=json.loads(proc.stdout)
        emit(dict(adhocAlloy=alloy,ms=(time.perf_counter()-start)*1000,exitCode=proc.returncode,
                  success=r['success'],reasonCode=r.get('reasonCode')))
    for alloy in ('ti6al4v','alsi10mg'):
        start=time.perf_counter()
        proc=subprocess.run([sys.executable,'-B',str(Path(__file__)),'--cap-adhoc',alloy],capture_output=True,text=True,timeout=180)
        r=json.loads(proc.stdout)
        emit(dict(adhocCapAlloy=alloy,ms=(time.perf_counter()-start)*1000,**r))


if __name__=='__main__':main()
