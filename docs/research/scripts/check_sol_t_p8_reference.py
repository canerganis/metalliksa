#!/usr/bin/env python3
"""Finite SOL-T P8 input-arm before/after catalogue; source-only independent oracle.

python -I docs/research/scripts/check_sol_t_p8_reference.py --check
No served imports, solved outputs, measured rows, network, or writes.
Local PDF archive prerequisite for the companion source check: lawful copies
matching papers/INDEX.md; repository clones do not include those PDFs.
Reference request: 200 W, .8 m/s, 80 um, T0=293.15 K, nominal IR properties.
Decimal affine antiderivatives, not runtime trapezoids. Budget: 5e-14 relative
+ 1e-18 absolute for binary64/Decimal rounding only, never physical tolerance.
The catalogue is pre-deduplication: source arm aliases remain individually visible.
"""
from __future__ import annotations
import argparse, ast, copy, hashlib, importlib.util, json, math
from decimal import Decimal, localcontext
from pathlib import Path
import sys
sys.dont_write_bytecode = True  # --check must not create local import bytecode.
ROOT=Path(__file__).resolve().parents[3]
SNAPSHOT=ROOT/'docs/research/sol_t_p8_reference.json'
D=lambda x:Decimal(str(x))
# This helper is a source-only analytic oracle, never a served module.
spec=importlib.util.spec_from_file_location('sol_t_decimal_oracle',Path(__file__).with_name('check_sol_t_dependencies.py'))
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)

def literal(n):
    if isinstance(n,ast.Name) and n.id=='IN625_LATENT_HEAT_J_KG':return 290000
    if isinstance(n,ast.Dict):return {literal(k):literal(v) for k,v in zip(n.keys,n.values)}
    if isinstance(n,(ast.List,ast.Tuple)):return [literal(v) for v in n.elts]
    return oracle.literal(n)

def source_table(path,name):
    tree=ast.parse((ROOT/path).read_text(encoding='utf8'))
    return literal(next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)))

def float_tree(x):
    if isinstance(x,Decimal):return float(x)
    if isinstance(x,dict):return {k:float_tree(v) for k,v in x.items()}
    if isinstance(x,list):return [float_tree(v) for v in x]
    return x

def viscosity(tref,alloy):
    if alloy=='alsi10mg':return D(10)**(-D('.8022')+D('658.34')/tref)*D('.001')
    if alloy=='in718':return D('.196')*(D(5848)/tref).exp()*D('.001')
    return D('.007') if alloy=='ss316l' else None

def tuple_for(aid,endpoints,ledger,thermal):
    ts,tl=map(D,endpoints[aid]);p=thermal[aid]
    if aid in ledger:
        s=oracle.reductions(ledger,endpoints)[aid];k,cp,rho=s['K'],s['cp'],s['rho']
    else:k,cp,rho=map(D,(p['thermal_conductivity_melt_W_mK'],p['specific_heat_melt_J_kgK'],p['density_kg_m3']))
    return dict(Ts=ts,Tl=tl,K=k,cp=cp,rho=rho,alpha=k/(rho*cp),A=D(p['absorptivity_IR']))

def primary(aid,ends,ledger,thermal):
    ti=aid=='ti6al4v';p=thermal[aid];n=ledger[aid]['numeric'];t=tuple_for(aid,ends,ledger,thermal)
    # Tref is a derived audit echo of the flow evaluation coordinate, not a new runtime request field.
    s={**{k:v for k,v in t.items() if k!='Ts'},'deltaT':D(500),'Tref':t['Tl']+250,'mu':D('.005') if ti else viscosity(t['Tl']+250,aid),
       'kl':D(p['thermal_conductivity_liquid_W_mK']),'cpl':D(p['specific_heat_liquid_J_kgK']),
       'rhol':D(p['density_liquid_kg_m3']),'slope':D('-.00019') if ti else D(p['d_gamma_dT_N_mK'])}
    rows={'nominal':s}
    def add(name,**patch):
        q={**s,**patch};q['alpha']=q['K']/(q['rho']*q['cp']);q['Tref']=q['Tl']+q['deltaT']/2
        if not ti and 'mu' not in patch:q['mu']=viscosity(q['Tref'],aid)
        rows[name]=q
    for a in (['.26','.33'] if ti else ['.28','.4','.14']):add(f'absorptance_{float(a):g}',A=D(a))
    if ti:
        def front(name,**patch):
            kl=patch.get('kl',s['kl']);cp=patch.get('cpl',s['cpl']);rho=patch.get('rhol',s['rhol']);ts=t['Ts']
            kf=n['k_s_linear_W_mK'];cf=n['cp_s_linear_J_kgK']
            add(name,K=(D(kf['slope'])*ts+D(kf['intercept'])+kl)/2,
                cp=(D(cf['slope'])*ts+D(cf['intercept'])+cp)/2,rho=(s['rho']+rho)/2,**patch)
        front('melt_front_means')
        for key,vals in [('kl',[28.7,33.4]),('cpl',[831,1126]),('rhol',[3920,4123])]:
            for v in vals:front(f'melt_front_{key}_{v:g}',**{key:D(v)})
        add('enthalpy_cp',cp=s['cp']+D(290000)/(s['Tl']-D('293.15')))
        add('srv',K=D('18.25'),cp=D(728),rho=D(4430))
        for v in [3360,3760]:add(f'vapour_{v}')
    else:
        reductions=oracle.reductions(ledger,ends)[aid]
        for state in ['HT_low','HT','AB_unrelaxed']:
            q=reductions['states'][state];add(f'state_{state}',K=q['K'],cp=q['cp'])
        q=reductions['linear_last_100K'];add('linear_last_100K',K=q['K'],cp=q['cp'])
        add('cp_fetni_end',cp=reductions['cp_fetni_end'])
        for v in ['863.15','872.15']:
            other={**ends,aid:[ends[aid][0],D(v)]};q=oracle.reductions(ledger,other)[aid]
            add(f'liquidus_{v}',Tl=D(v),K=q['K'],cp=q['cp'])
        for v in [2620,2715]:add(f'rho_s_{v}',rho=D(v))
        kn=n['k_s_nodes_W_mK']['AB'];cn=n['cp_s_nodes_J_kgK']['AB']
        for tag,rhol in [('assael',D(2603)-D('.241')*s['Tl']),('adc12',D(2492)-D('.2652')*(s['Tl']-865))]:
            add(f'melt_front_{tag}',K=(D(kn[-1][1])+64)/2,cp=(D(cn[-1][1])+1180)/2,rho=(D(2696)+rhol)/2,rhol=rhol,cpl=D(1180))
        for v in [397000,500000]:add(f'enthalpy_cp_{v}',cp=s['cp']+D(v)/(s['Tl']-D('293.15')))
        add('srv',K=D('107.5'),cp=D(1045),rho=D(2680));add('vapour_o8')
    # These source arms change other inputs but inherit the endpoint-sensitive inputs catalogued here.
    for v in [.95,1.05]:add(f'power_{v:g}');add(f'beam_{v:g}')
    for v in ['O1','O3']:add(f'onset_{v}')
    for v in ([-.00014,-.00024] if ti else [-.0786e-3,-.244e-3]):add(f'slope_{v:g}',slope=D(v))
    if ti:add('viscosity_mohr',mu=D('.004'));add('slope_viscosity_gan',slope=D('-.00026'),mu=D('.00266'))
    for v in [250,1000]:add(f'deltaT_{v}',deltaT=D(v))
    for v in [.5,2]:add(f'length_{v:g}')
    add('accommodation_effective_0.82')
    return rows

def secondary(aid,ends,thermal):
    # The actual secondary IN625 declaration deliberately has empty properties.
    # Do not manufacture a filled secondary manifest from the served context tuple.
    empty=aid=='in625';p=thermal[aid]
    tl=None if empty else D(ends[aid][1]);k=None if empty else D(p['thermal_conductivity_melt_W_mK']);cp=None if empty else D(p['specific_heat_melt_J_kgK']);rho=None if empty else D(p['density_kg_m3'])
    s=dict(Tl=tl,K=k,cp=cp,rho=rho,alpha=None if empty else k/(cp*rho),A=None if empty else D(p['absorptivity_IR']),
           Tref=None if empty else tl+250,deltaT=D(500),mu=None if empty else viscosity(tl+250,aid))
    rows={'nominal':s}
    def add(name,**patch):
        q={**s,**patch}
        if 'deltaT' in patch and tl is not None:
            q['Tref']=tl+q['deltaT']/2
            if aid=='in718':q['mu']=viscosity(q['Tref'],aid)
        rows[name]=q
    optics={'in625':[.28,.4],'in718':[.28,.38],'ss316l':[.28,.31]}[aid]
    for v in optics:add(f'absorptance_{v:g}',A=D(v))
    for v in [.95,1.05]:add(f'power_{v:g}');add(f'beam_{v:g}')
    for v in [250,1000]:add(f'deltaT_{v}',deltaT=D(v))
    for v in [.5,2]:add(f'length_{v:g}')
    if aid=='in718':add('slope_commercial_mills')
    add('accommodation_effective_0.82')
    if aid=='in625':add('vapour_melt_in625_raoult')
    return rows

def source_arm_ids(tree, aid):
    """Enumerate declarations from AST control flow, without executing served code.

    Only add/front names, branch predicates and finite loop iterables are read.
    Unknown numeric patches may remain opaque; using one in a name/condition fails.
    """
    unknown = object()
    env = dict(alloy=aid, ti=aid=='ti6al4v')
    names = []
    def expr(n):
        if isinstance(n, ast.Constant): return n.value
        if isinstance(n, ast.Name): return env.get(n.id, unknown)
        if isinstance(n, (ast.Tuple, ast.List)): return [expr(v) for v in n.elts]
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            value=expr(n.operand); return -value if value is not unknown else unknown
        if isinstance(n, ast.IfExp): return expr(n.body if condition(n.test) else n.orelse)
        if isinstance(n, ast.Compare) and len(n.ops)==1 and isinstance(n.ops[0], ast.Eq):
            left,right=expr(n.left),expr(n.comparators[0])
            if left is unknown or right is unknown: raise ValueError('Unknown arm branch')
            return left==right
        if isinstance(n, ast.JoinedStr):
            parts=[]
            for v in n.values:
                if isinstance(v, ast.Constant): parts.append(v.value); continue
                value=expr(v.value)
                if value is unknown: raise ValueError('Unknown arm name expression')
                parts.append(format(value,expr(v.format_spec) if v.format_spec else ''))
            return ''.join(parts)
        return unknown
    def condition(n):
        value=expr(n)
        if type(value) is not bool: raise ValueError('Unsupported arm branch')
        return value
    def bind(target,value):
        if isinstance(target,ast.Name): env[target.id]=value
        elif isinstance(target,(ast.Tuple,ast.List)) and isinstance(value,list) and len(target.elts)==len(value):
            for t,v in zip(target.elts,value): bind(t,v)
        else: raise ValueError('Unsupported arm loop binding')
    def has_declaration(nodes):
        return any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ('add','front')
                   for node in nodes for n in ast.walk(node) if not isinstance(node,ast.FunctionDef))
    def walk(nodes):
        for n in nodes:
            if isinstance(n,ast.FunctionDef): continue
            if isinstance(n,ast.If) and has_declaration([n]): walk(n.body if condition(n.test) else n.orelse)
            elif isinstance(n,ast.For) and has_declaration([n]):
                values=expr(n.iter)
                if not isinstance(values,list): raise ValueError('Unsupported arm iterable')
                for value in values: bind(n.target,value);walk(n.body)
            elif isinstance(n,ast.Expr) and isinstance(n.value,ast.Call):
                call=n.value
                if isinstance(call.func,ast.Name) and call.func.id in ('add','front'):
                    name=expr(call.args[0])
                    if not isinstance(name,str): raise ValueError('Unsupported arm ID')
                    names.append(name)
    primary_alloy=aid in ('ti6al4v','alsi10mg')
    func=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and
              n.name==('arms' if primary_alloy else 'secondary_manifests'))
    if primary_alloy:
        initial=next(n.value for n in func.body if isinstance(n,ast.Assign) and
                     any(isinstance(t,ast.Name) and t.id=='result' for t in n.targets))
        names.append(expr(initial)[0][0])
        wrapper=next(n for n in func.body if isinstance(n,ast.If) and isinstance(n.test,ast.Name) and n.test.id=='ti')
        front=next(n for n in wrapper.body if isinstance(n,ast.FunctionDef) and n.name=='front')
        forwarded=[n for n in ast.walk(front) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='add']
        if len(forwarded)!=1 or not isinstance(forwarded[0].args[0],ast.Name) or forwarded[0].args[0].id!='name':
            raise ValueError('Front wrapper no longer forwards its arm ID')
        walk(func.body)
    else:
        loop=next(n for n in func.body if isinstance(n,ast.For))
        choices=expr(loop.iter)
        matches=[v for v in choices if v[0]==aid]
        if len(matches)!=1: raise ValueError('Missing secondary source alloy')
        bind(loop.target,matches[0]);walk(loop.body)
    if len(set(names))!=len(names): raise ValueError('Duplicate source arm ID')
    return set(names)

def validate_arm_ids(catalogue,tree):
    for category,alloys in (('primaryArms',{'ti6al4v','alsi10mg'}),('secondaryArms',{'in718','ss316l','in625'})):
        if set(catalogue[category])!=alloys: raise ValueError('Catalogue alloy coverage changed')
        for aid in alloys:
            source=source_arm_ids(tree,aid);recorded=set(catalogue[category][aid])
            if source!=recorded: raise ValueError(f'{aid}: source/catalogue arm IDs differ: missing={sorted(source-recorded)}, extra={sorted(recorded-source)}')

def build():
    records=json.loads((ROOT/'docs/research/sol_t_admission_records.json').read_text(encoding='utf8'))
    old={r['id']:[D(v)+D('273.15') for v in r['baseline_C']] for r in records['records']};new={r['id']:r['endpoint_K'] for r in records['records']}
    ledger=oracle.table('PROPERTY_LEDGER');thermal=oracle.table('_THERMAL');thermal['in625']=source_table('python/lpbf_thermal_solver.py','SECONDARY_THERMOPHYSICAL_DB')['Inconel 625']
    paths=['python/four_alloy_materials.py','python/lpbf_thermal_solver.py','python/lpbf_research_context.py','python/lpbf_research_manifest.py','docs/research/scripts/check_sol_t_dependencies.py']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in paths}
    out=dict(schema='sol-t-p8-input-reference-v1',referenceRequest={'power_W':200,'speed_m_s':.8,'beamDiameter_m':.00008,'preheat_K':293.15,'propertyContext':'nominal IR; Al AB'},
       scope='Every pre-deduplication source arm endpoint-sensitive input, not solved quantities, source labels, arbitrary user options or module outcome. Primary Tref is derived audit echo. Secondary IN625 deliberate nulls retained.',
       sourceCanonicalSha256=hashes,defaultTuples={},primaryArms={},secondaryArms={})
    for aid in old:
        out['defaultTuples'][aid]={'before':tuple_for(aid,old,ledger,thermal),'after':tuple_for(aid,new,ledger,thermal)}
        dest=out['primaryArms'] if aid in ledger else out['secondaryArms']
        before=primary(aid,old,ledger,thermal) if aid in ledger else secondary(aid,old,thermal)
        after=primary(aid,new,ledger,thermal) if aid in ledger else secondary(aid,new,thermal)
        dest[aid]={name:{'before':before[name],'after':after[name],'changedInputs':[k for k in before[name] if before[name][k]!=after[name][k]]} for name in before}
    return float_tree(out)

def compare(a,b,path='root'):
    if type(a)!=type(b) and not isinstance(a,(int,float)) or type(a)!=type(b) and not isinstance(b,(int,float)):raise ValueError(path+':type changed')
    if isinstance(a,dict):
        if set(a)!=set(b):raise ValueError(path+':keys changed')
        for k in a:compare(a[k],b[k],path+'/'+k)
    elif isinstance(a,list):
        if len(a)!=len(b):raise ValueError(path+':length changed')
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+f'/{i}')
    elif isinstance(a,(int,float)) and not isinstance(a,bool):
        if not math.isfinite(a) or abs(a-b)>abs(b)*5e-14+1e-18:raise ValueError(path+':number changed')
    elif a!=b:raise ValueError(path+':value changed')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check',required=True,action='store_true');p.parse_args()
    expected=json.loads(SNAPSHOT.read_text(encoding='utf8'));actual=build();compare(actual,expected)
    tree=ast.parse((ROOT/'python/lpbf_research_manifest.py').read_text(encoding='utf8'))
    validate_arm_ids(expected,tree)
    # Independent response to changed threshold and catalogue edits, not self equality only.
    bad=copy.deepcopy(expected);bad['primaryArms']['ti6al4v']['melt_front_kl_28.7']['after']['K']+=1
    try:compare(actual,bad)
    except ValueError:pass
    else:raise ValueError('missed altered Ti arm input')
    bad=copy.deepcopy(expected);bad['secondaryArms']['in625']['nominal']['after']['Tl']=1623.15
    try:compare(actual,bad)
    except ValueError:pass
    else:raise ValueError('missed forbidden IN625 secondary fill')
    # Reconcile source names independently of copied numeric arm algebra/hashes.
    bad=copy.deepcopy(tree)
    call=next(n for n in ast.walk(bad) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and
              n.func.id=='add' and n.args and isinstance(n.args[0],ast.Constant) and n.args[0].value=='srv')
    call.args[0].value='new_unreconciled_source_arm'
    try:validate_arm_ids(expected,bad)
    except ValueError:pass
    else:raise ValueError('missed source arm ID change')
    bad=copy.deepcopy(expected);del bad['primaryArms']['ti6al4v']['nominal']
    try:validate_arm_ids(bad,tree)
    except ValueError:pass
    else:raise ValueError('missed missing catalogue arm')
    count=sum(len(v) for category in ('primaryArms','secondaryArms') for v in actual[category].values())
    moved=sum(len(row['changedInputs']) for category in ('primaryArms','secondaryArms') for rows in actual[category].values() for row in rows.values())
    print(f'PASS: 5 default tuples; {count} AST-enumerated pre-deduplication input arms; {moved} changed arm leaves; 4 negative controls')
    print('Scope: finite reference inputs only; no installed served result, physical validity or bands claim')
if __name__=='__main__':
    try:
        with localcontext() as ctx:ctx.prec=40;main()
    except (ValueError,KeyError,OSError,StopIteration) as exc:print('FAIL: '+str(exc),file=sys.stderr);sys.exit(1)
