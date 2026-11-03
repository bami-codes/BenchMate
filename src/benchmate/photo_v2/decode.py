"""Literal-code decoding. No nominal design, preferred-value filtering or fitting."""
from collections import Counter, defaultdict
from itertools import product
import re

DIGITS = {c:i for i,c in enumerate(('black','brown','red','orange','yellow','green','blue','violet','gray','white'))}
MULT = {**{c:10.**i for c,i in DIGITS.items()},'gold':.1,'silver':.01}
TOL = {'brown':.01,'red':.02,'green':.005,'blue':.0025,'violet':.001,'gray':.0005,'gold':.05,'silver':.1,'none':.2}
TCR = {'black':250,'brown':100,'red':50,'orange':15,'yellow':25,'green':20,'blue':10,'violet':5,'gray':1}
CAP_TOL = {'F':.01,'G':.02,'H':.03,'J':.05,'K':.1,'M':.2}


def resistor(colors):
    """Return all valid full-sequence orientations; E24/E96 never exclude a code."""
    colors = ['gray' if c=='grey' else c for c in colors]
    if len(colors) not in (4,5,6): return []
    result=[]
    for direction,seq in [('forward',colors),('reverse',colors[::-1])]:
        n = 2 if len(seq)==4 else 3
        if any(c not in DIGITS for c in seq[:n]) or seq[0]=='black': continue
        if seq[n] not in MULT or seq[n+1] not in TOL: continue
        if len(seq)==6 and seq[-1] not in TCR: continue
        digits=int(''.join(str(DIGITS[c]) for c in seq[:n]))
        row={'kind':'R','value_si':digits*MULT[seq[n]],'tolerance_fraction':TOL[seq[n+1]],
             'direction':direction,'literal_colors':seq,'rule':str(len(seq))+'-band',
             'preferred_series_used_to_select':False}
        if len(seq)==6:row['TCR_ppm_per_K']=TCR[seq[-1]]
        result.append(row)
    return result


def capacitor(text, kind='unknown'):
    """Common pF code; voltage is a conditional marking convention, never a rating proof."""
    text=text.strip().replace('µ','u').replace('μ','u')
    direct=re.fullmatch(r'(\d+(?:\.\d+)?)\s*(p|n|u|m)?[fF]',text)
    if direct:
        unit={None:1.,'p':1e-12,'n':1e-9,'u':1e-6,'m':1e-3}[direct[2]]
        return [{'kind':'C','value_si':float(direct[1])*unit,'literal':text,'rule':'explicit-unit','conditional_component_kind':kind!='C'}]
    m=re.fullmatch(r'(\d{3})([DFGHJKM])?(?:([ /]*)(\d{2,4})(V)?)?',text.upper())
    if not m:return []
    code,tol,separator,voltage,vunit=m.groups()
    # Bare digits inside a transistor/resistor label are not a capacitor reading.
    strong=bool(tol and voltage or vunit or separator)
    if kind not in ('C','unknown','other') and not strong:return []
    if voltage and not (tol or separator or vunit):return []
    exponent=int(code[2]);exponent={8:-2,9:-1}.get(exponent,exponent)
    row={'kind':'C','value_si':int(code[:2])*10.**exponent*1e-12,'literal':text,
         'rule':'common-three-digit-pF-code','conditional_component_kind':kind!='C'}
    if tol in CAP_TOL:row['tolerance_fraction']=CAP_TOL[tol]
    if tol=='D':row['tolerance_absolute_f']=.5e-12
    if voltage:
        row.update(voltage_v_candidate=float(voltage),voltage_verified=False,
                   voltage_basis='Conditional common marking convention; manufacturer rating not established')
    return [row]


def decode_surface(surface, *, flipped=False):
    bands=list(surface.get('bands',[]));axis=surface.get('band_axis','unknown')
    if flipped and axis=='horizontal':bands=bands[::-1]
    primary=resistor([b['color'] for b in bands])
    alternatives=[];choices=[]
    for b in bands:
        options=list(dict.fromkeys([b['color']]+b.get('alternatives',[])))
        choices.append([x for x in options if x not in ('unknown','none') or x=='none'])
    count=1
    for c in choices:count*=len(c)
    if bands and 0<count<=512:
        for seq in product(*choices):alternatives.extend(resistor(seq))
    for mark in surface.get('markings',[]):
        primary.extend(capacitor(mark['text'],surface.get('kind','unknown')))
        for alt in mark.get('alternatives',[]):alternatives.extend(capacitor(alt,surface.get('kind','unknown')))
    return {'primary':primary,'alternatives':alternatives,'bands_original_orientation':bands,
            'band_axis':axis,'candidate_expansion_exceeded':count>512,
            'model_confidences_are_uncalibrated':True}


def _key(row):return (row['kind'],format(row['value_si'],'.12g'))


def aggregate(views, *, expected_views=5):
    """A representative supported by actual full-view decodes, never a synthetic vote sequence."""
    support=defaultdict(set);unique=defaultdict(set);possible=defaultdict(set);examples={};band_votes=defaultdict(Counter)
    details=[];unreadable=0
    for i,view in enumerate(views):
        if view.get('status')!='completed':
            unreadable+=1;details.append({'view':i,'error':view.get('error','failed')});continue
        decoded=decode_surface(view['surface'],flipped=view.get('flipped',False))
        keys={_key(r) for r in decoded['primary']}
        if not keys:unreadable+=1
        for row in decoded['primary']:
            k=_key(row);support[k].add(i);examples.setdefault(k,row)
            if len(keys)==1:unique[k].add(i)
        for row in decoded['alternatives']:
            k=_key(row);possible[k].add(i);examples.setdefault(k,row)
        bands=decoded['bands_original_orientation'];axis=decoded['band_axis']
        if axis!='unknown':
            for j,b in enumerate(bands):band_votes[(len(bands),axis,j)][b['color']]+=1
        details.append({'view':i,**decoded})
    candidates=[]
    for k in examples:
        candidates.append({**examples[k],'unique_vote_count':len(unique[k]),'compatible_view_count':len(support[k]),
                           'alternative_view_count':len(possible[k]),'supporting_views':sorted(support[k])})
    candidates.sort(key=lambda x:(-x['compatible_view_count'],x['kind'],x['value_si']))
    leaders=[x for x in candidates if x['compatible_view_count']>0]
    representative=leaders[0] if leaders else None
    ties=[]
    if representative:
        ties=[x for x in leaders if x['compatible_view_count']==representative['compatible_view_count']]
    tallies=[{'band_count':n,'axis':axis,'index':j,'votes':dict(v)} for (n,axis,j),v in sorted(band_votes.items())]
    return {'value_si':representative['value_si'] if representative else None,
            'kind':representative['kind'] if representative else 'unknown',
            'vote_count':representative['compatible_view_count'] if representative else 0,'view_count':expected_views,
            'unique_direction_vote_count':representative['unique_vote_count'] if representative else 0,
            'label':'photo candidate','ties':len(ties)>1,'tied_candidates':ties if len(ties)>1 else [],
            'tie_break':'Canonical kind/value order for display only; tie remains explicit',
            'unreadable_views':unreadable,'candidates':candidates,'band_votes':tallies,'views':details,
            'representative_requires_complete_view_support':True,'per_band_synthetic_value_not_used':True,
            'agreement_is_not_accuracy':True,'votes_can_support_multiple_candidates':True,
            'measurement_verified':False,'preferred_series_filter':False}


def compare_resistance_path(result, effective_ohm, *, component_binding_confirmed=False):
    """A terminal path fit cannot by itself verify a photographed individual resistor."""
    values=sorted({c['value_si'] for c in result['candidates'] if c['kind']=='R' and c['compatible_view_count']>0})
    return {'measurement_scope':'effective_series_path','photo_scope':'individual_visible_component',
            'measurement_verified':False,'status':'not_identifiable_from_effective_path_alone',
            'component_binding_confirmed':component_binding_confirmed,'effective_ohm':effective_ohm,
            'conditional_remaining_series_ohm':[effective_ohm-x for x in values] if component_binding_confirmed else [],
            'limits':'Subtraction assumes the photo component belongs to this series path; it does not identify a unique extra physical part.'}
