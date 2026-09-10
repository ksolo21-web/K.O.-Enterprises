"""Optional original-bound addition/removal pair; preserves individual mask limits."""
import itertools,math,hashlib
from pathlib import Path
import numpy as np
SCHEMA='shared-junction-pairs-1'
def module_sha256():return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()

def inspect_pairs(plan,operations,masks,views,shape,api):
    require=api.require;groups=plan.get('shared_junction_pairs',[])
    require(isinstance(groups,list),'shared_junction_pairs must be a list')
    by={o.get('id'):o for o in operations};require(len(by)==len(operations),'Operation IDs must be unique and nonempty')
    pairs={};used=set();gids=set();records=[]
    for g in groups:
        require(isinstance(g,dict) and set(g)=={'id','operation_ids','junction','predeclared_review'},'Invalid shared pair fields')
        gid=g['id'];ids=g['operation_ids'];require(isinstance(gid,str)and gid and gid not in gids,'Invalid/duplicate pair ID');gids.add(gid)
        require(isinstance(ids,list)and len(ids)==2 and all(isinstance(x,str)and x in by for x in ids)and len(set(ids))==2,'Pair needs exactly two known distinct members')
        require(not used.intersection(ids),'Operation belongs to multiple pairs');used.update(ids);ops=[by[x]for x in ids]
        require({o.get('kind')for o in ops}=={'addition','removal'},'Pair requires addition and removal');require(ops[0].get('status')==ops[1].get('status'),'Pair status mismatch')
        review=api.load(api.evidence_file(g['predeclared_review'],'shared junction review'))
        require(all(review.get(k)is True for k in ('predates_candidate','independent','not_candidate_derived','source_pair_approved')),'Pair source review provenance missing')
        require(review.get('operations')==ops and review.get('junction')==g['junction'],'Pair review must bind exact ordered operations and junction')
        require(review.get('base_source_sha256')==plan.get('base_source_sha256'),'Pair original base mismatch')
        assignment=review.get('original_assignment',{});require(assignment.get('sha256')==plan['original_assignment']['sha256'] and assignment.get('page_index')==plan['original_assignment']['page_index'],'Pair original assignment mismatch')
        api.evidence_file(assignment,'pair original assignment')
        parts=api.source_mask_parts(g['junction']);region=np.zeros(shape,bool);per=[];oi=[operations.index(o)for o in ops]
        for v in views:
            jr=api.view_region(parts,v,shape,guard=1);region|=jr
            mr=[api.view_region(api.source_mask_parts(o),v,shape,guard=1)for o in ops];over=mr[0]&mr[1]
            require(not np.any(over&~jr),'Pair overlap outside declared junction in view '+v['id'])
            per.append({'view_id':v['id'],'overlap_pixels':int(over.sum()),'outside_junction_pixels':0})
        overlap=masks[oi[0]]&masks[oi[1]];require(not np.any(overlap&~region),'Pair overlap outside declared junction union')
        pairs[frozenset(ids)]=region
        records.append({'id':gid,'operation_ids':ids,'predeclared_review':g['predeclared_review'],'base_source_sha256':plan['base_source_sha256'],'original_assignment_sha256':plan['original_assignment']['sha256'],'junction':g['junction'],'junction_parts_source':parts,'renderer_guard_2x_px':1,'overlap_pixels':int(overlap.sum()),'outside_junction_pixels':0,'per_view_overlap':per})
    for i,j in itertools.combinations(range(len(operations)),2):
        over=masks[i]&masks[j]
        if over.any():
            key=frozenset((operations[i]['id'],operations[j]['id']));require(key in pairs,'Topology correction masks overlap; declare independent local patches');require(not np.any(over&~pairs[key]),'Topology correction masks overlap outside declared junction')
    return records

def validate_pair_report(plan,report):
    """Consumed by both existing release gates; pair report cannot disappear."""
    groups=plan.get('shared_junction_pairs',[]);actual=report.get('shared_junction_review')
    if not isinstance(groups,list):return ['shared_junction_review: pair declaration must be a list']
    if not groups and actual is None:return []
    errors=[]
    def check(v,msg):
        if not v:errors.append('shared_junction_review: '+msg)
    try:
        from topology_masks import source_mask_parts
        check(isinstance(groups,list)and bool(groups),'unexpected pair report')
        check(isinstance(actual,dict)and actual.get('schema_version')==SCHEMA,'typed pair report required')
        if not isinstance(actual,dict):return errors
        check(actual.get('pair_validator_sha256')==module_sha256(),'pair report must bind current pair validator')
        records=actual.get('pairs',[]);check(isinstance(records,list)and len(records)==len(groups),'pair count')
        by={r.get('id'):r for r in records};check(len(by)==len(records),'duplicate report pair')
        check(set(by)=={g['id']for g in groups},'exact pair IDs')
        views=report['source_views'];results={r['mask_id']:r for r in report['results']}
        for g in groups:
            r=by.get(g['id'],{});ids=g['operation_ids']
            for key in ('operation_ids','predeclared_review','junction'):check(r.get(key)==g[key],'exact '+key)
            check(r.get('junction_parts_source')==source_mask_parts(g['junction']),'exact junction union')
            check(r.get('base_source_sha256')==plan['base_source_sha256']and r.get('original_assignment_sha256')==plan['original_assignment']['sha256'],'immutable original authority')
            check(type(r.get('renderer_guard_2x_px'))is int and r['renderer_guard_2x_px']==1,'unchanged guard')
            check(type(r.get('overlap_pixels'))is int and r['overlap_pixels']>=0,'overlap count')
            check(type(r.get('outside_junction_pixels'))is int and r['outside_junction_pixels']==0,'zero outside junction')
            pv=r.get('per_view_overlap',[]);check(len(pv)==len(views)and [x.get('view_id')for x in pv]==[v['id']for v in views],'exact per-view overlap inventory')
            for x in pv:check(type(x.get('overlap_pixels'))is int and x['overlap_pixels']>=0 and type(x.get('outside_junction_pixels'))is int and x['outside_junction_pixels']==0,'per-view containment')
            check(r.get('ordered_composition_bytes_equal')is True,'original-bound commutative composition')
            members=r.get('member_contributions',[]);check(len(members)==2 and [m.get('operation_id')for m in members]==ids,'exact contribution members')
            for m in members:
                check(type(m.get('isolated_changed_pixels'))is int and m['isolated_changed_pixels']>0,'positive isolated visible contribution')
                check(type(m.get('marginal_changed_pixels'))is int and m['marginal_changed_pixels']>0,'positive marginal visible contribution')
                op=results.get(m.get('operation_id'),{});check(op.get('isolated_delta_contained')is True and op.get('isolated_pixels_changed_outside_mask')==0,'own-mask containment remains mandatory')
                for k in ('added_length_outside_mask_source_pt','removed_length_outside_mask_source_pt'):check(type(op.get(k))in(int,float)and math.isfinite(op[k])and op[k]==0,'native own-mask '+k)
    except (KeyError,ValueError,TypeError,AttributeError)as e:errors.append('shared_junction_review: '+str(e))
    return errors
