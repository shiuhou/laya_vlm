"""Prospectively fixed, offline wrist-history versus endpoint comparison."""
from __future__ import annotations

import argparse
from bisect import bisect_left, bisect_right
from collections import Counter
import json
from pathlib import Path

import numpy as np

from ..runtime_core import _sha256_json
from .records import RunRecorder, code_identity, file_hash, versions

ROOT=Path(__file__).resolve().parents[2]
SOURCE=Path('/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/task1-native-contact-run-01')
SOURCE_SHA256='e8e253cefe4c694c6091e1bf944a8f269cfc47c7ed08c053419d97e1a73615d4'
PROTOCOL=ROOT/'docs/research/offline_wrist_history_protocol.md'
COHORTS=('gripper_only','arm_only','gripper_and_arm','no_robot_scene_above_1N','self_contact_present')
SENSOR_KEYS={'global_control','step','control','before_time_s','baseline_force_N','baseline_torque_Nm','after'}
SAMPLE_KEYS={'time_s','force_N','torque_Nm'}
FEATURE_KEYS={'global_control','step','control','before_time_s','after_time_s',
 'endpoint_force_change_N','temporal_force_change_N','endpoint_torque_change_Nm','temporal_torque_change_Nm'}


def records(path):
    previous=None
    with Path(path).open('rb') as stream:
        for i,line in enumerate(stream):
            if not line.endswith(b'\n'):raise ValueError('incomplete source record')
            row=json.loads(line)
            if row['seq']!=i or row['previous_record_id']!=previous or row['record_id']!=_sha256_json({k:v for k,v in row.items() if k!='record_id'}):
                raise ValueError('source record integrity failure')
            previous=row['record_id'];yield row


def write_json(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,allow_nan=False);f.write('\n')


def write_rows(path,rows):
    with Path(path).open('x') as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,allow_nan=False)+'\n')


def read_rows(path):
    with Path(path).open() as f:return [json.loads(line) for line in f]


def extract_sensors(output):
    """Only wrist values, times and indices leave this explicit projection."""
    count=0;current=None;metadata=None
    with (output/'sensors.jsonl').open('x') as target:
        for record in records(SOURCE/'episodes.jsonl'):
            kind,d=record['kind'],record['data']
            if kind=='environment':
                metadata={k:d[k] for k in ('sensors','model_timestep_s','control_timestep_s','integrator')}
            elif kind=='control_started':
                if current is not None:raise ValueError('unclosed sensor control')
                if d['global_control']!=count:raise ValueError('sensor control order')
                current={k:d[k] for k in ('global_control','step','control')};current['after']=[]
            elif kind=='integrator_call_started' and d['within_control_index']==0:
                s=d['before'];buffers=s['wrist_sensor_buffers']
                current.update(before_time_s=s['time_s'],baseline_force_N=buffers['force_ee']['values'],baseline_torque_Nm=buffers['torque_ee']['values'])
            elif kind=='integrator_call_completed':
                s=d['after'];buffers=s['wrist_sensor_buffers']
                if any(buffers[k]['actual_sample_time_s'] is not None for k in ('force_ee','torque_ee')):raise ValueError('unknown sensor sample time changed')
                if d['within_control_index']!=len(current['after']):raise ValueError('native sample order')
                current['after'].append({'time_s':s['time_s'],'force_N':buffers['force_ee']['values'],'torque_Nm':buffers['torque_ee']['values']})
            elif kind=='control_completed':
                validate_sensor_row(current)
                target.write(json.dumps(current,sort_keys=True,allow_nan=False)+'\n');current=None;count+=1
    if count!=970 or current is not None or metadata is None:raise ValueError('incomplete970-control sensor projection')
    write_json(output/'sensor_metadata.json',metadata)
    return count


def validate_sensor_row(row):
    if set(row)!=SENSOR_KEYS or len(row['after'])!=25:raise ValueError('sensor-only schema/control count differs')
    for sample in row['after']:
        if set(sample)!=SAMPLE_KEYS:raise ValueError('sensor sample contains unexpected keys')
    values=[row['baseline_force_N'],row['baseline_torque_Nm']]+[s[k] for s in row['after'] for k in ('force_N','torque_Nm')]
    if any(np.asarray(v).shape!=(3,) or not np.isfinite(v).all() for v in values):raise ValueError('finite three-axis sensor required')
    for i,s in enumerate(row['after']):
        if abs(s['time_s']-row['before_time_s']-(i+1)*.002)>1e-10:raise ValueError('native read-time cadence differs')


def sensor_features(row):
    """Pure sensor function: no source path or contact/evaluator input."""
    validate_sensor_row(row)
    result={k:row[k] for k in ('global_control','step','control','before_time_s')}
    result['after_time_s']=row['after'][-1]['time_s']
    for channel,unit in (('force','N'),('torque','Nm')):
        baseline=np.asarray(row[f'baseline_{channel}_{unit}'])
        deltas=[float(np.linalg.norm(np.asarray(s[f'{channel}_{unit}'])-baseline)) for s in row['after']]
        result[f'endpoint_{channel}_change_{unit}']=deltas[-1]
        result[f'temporal_{channel}_change_{unit}']=max(deltas)
    if set(result)!=FEATURE_KEYS:raise ValueError('feature-only schema changed')
    return result


def contact_membership(contacts,geometry):
    robot=set(geometry['robot']['ids']);gripper=set(geometry['gripper']['ids']);arm=set(geometry['arm']['ids']);drawer=set(geometry['drawer']['ids'])
    if gripper & arm or gripper | arm != robot:raise ValueError('declared robot/gripper/arm partition changed')
    result={'gripper':False,'arm':False,'self':False,'gripper_drawer':False,'raw_external_rows':0,'strong_contacts':[]}
    for c in contacts:
        a,b=c['geom_ids'];ar,br=a in robot,b in robot
        if ar != br:result['raw_external_rows']+=1
        if c['normal_force_N']<=1.:continue
        if ar and br:result['self']=True;result['strong_contacts'].append({**c,'group':'self'})
        elif ar!=br:
            body,scene=(a,b) if ar else (b,a)
            group='gripper' if body in gripper else 'arm'
            result[group]=True
            if group=='gripper' and scene in drawer:result['gripper_drawer']=True
            result['strong_contacts'].append({**c,'group':group,'scene_is_drawer':scene in drawer})
    return result


def cohort(gripper,arm,self_contact):
    if self_contact:return 'self_contact_present'
    if gripper and arm:return 'gripper_and_arm'
    if gripper:return 'gripper_only'
    if arm:return 'arm_only'
    return 'no_robot_scene_above_1N'


def extract_labels(output):
    """Evaluator pass after all sensor features are sealed; reads contacts only."""
    labels=[];current=None;geometry=None;before_time=None
    for record in records(SOURCE/'episodes.jsonl'):
        kind,d=record['kind'],record['data']
        if kind=='environment':geometry=d['geometry']
        elif kind=='control_started':
            current={k:d[k] for k in ('global_control','step','control')}
            current['native_samples']=[]
        elif kind=='integrator_call_started':before_time=d['before']['time_s']
        elif kind=='integrator_call_completed':
            sample=contact_membership(d['after']['contacts'],geometry)
            current['native_samples'].append({'substep':d['within_control_index'],'interval_s':[before_time,d['after']['time_s']],**sample})
        elif kind=='control_completed':
            samples=current['native_samples']
            if len(samples)!=25:raise ValueError('gold native sample count differs')
            flags={key:any(s[key] for s in samples) for key in ('gripper','arm','self')}
            current.update(flags);current['cohort']=cohort(flags['gripper'],flags['arm'],flags['self'])
            current['endpoint_gripper']=samples[-1]['gripper']
            current['endpoint_missed_gripper_only']=current['cohort']=='gripper_only' and not current['endpoint_gripper']
            labels.append(current);current=None
    if len(labels)!=970 or current is not None:raise ValueError('complete970-control evaluator required')
    write_rows(output/'labels.jsonl',labels)
    return labels


def negative_rank(score,negatives):
    if not negatives:return None
    ordered=sorted(negatives)
    lo,hi=bisect_left(ordered,score),bisect_right(ordered,score)
    return (lo+.5*(hi-lo))/len(ordered)


def auroc(positives,negatives):
    if not positives or not negatives:return None
    return float(np.mean([negative_rank(x,negatives) for x in positives]))


def distribution(values):
    if not values:return {'count':0,'min':None,'p05':None,'median':None,'p95':None,'max':None}
    q=np.quantile(values,[0,.05,.5,.95,1],method='linear').tolist()
    return dict(count=len(values),**dict(zip(('min','p05','median','p95','max'),q)))


def compare(positives,negatives):
    score=auroc(positives,negatives)
    return {'positive':distribution(positives),'negative':distribution(negatives),'auroc':score,
        'positive_values_within_negative_observed_range':sum(min(negatives)<=p<=max(negatives) for p in positives) if negatives else None,
        'negative_values_within_positive_observed_range':sum(min(positives)<=n<=max(positives) for n in negatives) if positives else None}


def evaluate(features,labels):
    if len(features)!=970 or len(labels)!=970:raise ValueError('all970 controls required')
    for i,(f,label) in enumerate(zip(features,labels)):
        if set(f)!=FEATURE_KEYS or f['global_control']!=i or any(f[k]!=label[k] for k in ('global_control','step','control')):raise ValueError('feature/gold lineage differs')
    negatives=[f for f,l in zip(features,labels) if l['cohort']=='no_robot_scene_above_1N']
    positives=[f for f,l in zip(features,labels) if l['cohort']=='gripper_only']
    missed=[f for f,l in zip(features,labels) if l['endpoint_missed_gripper_only']]
    comparisons={};groups={}
    for channel,unit in (('force','N'),('torque','Nm')):
        end=f'endpoint_{channel}_change_{unit}';temp=f'temporal_{channel}_change_{unit}'
        comparisons[channel]={}
        for name,cohort_rows in (('all_gripper_only',positives),('endpoint_missed_gripper_only',missed)):
            result={key:compare([x[field] for x in cohort_rows],[x[field] for x in negatives]) for key,field in (('endpoint',end),('temporal',temp))}
            a,b=result['endpoint']['auroc'],result['temporal']['auroc'];result['auroc_temporal_minus_endpoint']=None if a is None or b is None else b-a
            comparisons[channel][name]=result
        groups[channel]={name:{key:distribution([f[field] for f,l in zip(features,labels) if l['cohort']==name]) for key,field in (('endpoint',end),('temporal',temp))} for name in COHORTS}
    examples=[]
    for f,label in zip(features,labels):
        if not label['endpoint_missed_gripper_only']:continue
        ranks={key:negative_rank(f[key],[n[key] for n in negatives]) for key in FEATURE_KEYS if key.startswith(('endpoint_','temporal_'))}
        examples.append({**f,'negative_cohort_ranks':ranks,
            'gripper_contact_native_intervals':[{'substep':s['substep'],'interval_s':s['interval_s'],'contacts':[c for c in s['strong_contacts'] if c['group']=='gripper']} for s in label['native_samples'] if s['gripper']]})
    counts=Counter(l['cohort'] for l in labels)
    return {'source_sha256':SOURCE_SHA256,'controls':970,'cohort_counts':{c:counts[c] for c in COHORTS},
        'primary_force_secondary_torque':comparisons,'all_cohort_distributions':groups,'endpoint_missed_controls':examples,
        'scope':'one dependent trajectory; native moving-local-frame sensor changes; no calibration, causal attribution, threshold fitting, holding or live gate'}


def run(output):
    output=Path(output);code=code_identity()
    if code['dirty_status']:raise ValueError('clean committed protocol/source/tests required')
    if file_hash(SOURCE/'episodes.jsonl')!=SOURCE_SHA256:raise ValueError('canonical source changed')
    recorder=RunRecorder(output,{'source':str(SOURCE),'source_sha256':SOURCE_SHA256,'offline_only':True,'model_calls':0,'physics_calls':0},
        {'run_id':output.name,'code':code,'versions':versions()})
    try:
        recorder.record('frozen_analysis',{'code':code,'protocol_sha256':file_hash(PROTOCOL),'source_sha256':SOURCE_SHA256,
            'source_summary_sha256':file_hash(SOURCE/'summary.json'),'cohorts':list(COHORTS),'force_primary':True,'torque_secondary':True})
        (output/'protocol.md').write_bytes(PROTOCOL.read_bytes())
        extract_sensors(output)
        recorder.record('sensors_sealed',{'sensors_sha256':file_hash(output/'sensors.jsonl'),'metadata_sha256':file_hash(output/'sensor_metadata.json'),'gold_available_to_feature_function':False})
        sensor_rows=read_rows(output/'sensors.jsonl');features=[sensor_features(s) for s in sensor_rows]
        write_rows(output/'features.jsonl',features)
        recorder.record('features_sealed',{'features_sha256':file_hash(output/'features.jsonl'),'rows':len(features),'gold_labels_written':False})
        labels=extract_labels(output)
        recorder.record('labels_sealed',{'labels_sha256':file_hash(output/'labels.jsonl'),'rows':len(labels),'oracle_evaluator_only':True})
        summary=evaluate(features,labels);write_json(output/'summary.json',summary)
        recorder.record('termination',{'reason':'offline_comparison_complete','controls':970,'summary_sha256':file_hash(output/'summary.json'),'model_calls':0,'physics_calls':0})
    except BaseException as exc:
        recorder.record('failure',{'reason':repr(exc)});raise
    finally:recorder.close()


def audit(output):
    output=Path(output);rows=list(records(output/'episodes.jsonl'))
    if any(r['kind']=='failure' for r in rows):raise ValueError('recorded offline failure')
    kinds=[r['kind'] for r in rows]
    if kinds!=['run_start','frozen_analysis','sensors_sealed','features_sealed','labels_sealed','termination']:raise ValueError('sensor/features not sealed before evaluator')
    frozen=rows[1]['data']
    if code_identity()['source_sha256']!=frozen['code']['source_sha256'] or file_hash(PROTOCOL)!=frozen['protocol_sha256']:raise ValueError('frozen scientific code/protocol changed')
    if file_hash(SOURCE/'episodes.jsonl')!=SOURCE_SHA256:raise ValueError('raw source changed')
    checks={'sensors.jsonl':rows[2]['data']['sensors_sha256'],'sensor_metadata.json':rows[2]['data']['metadata_sha256'],
            'features.jsonl':rows[3]['data']['features_sha256'],'labels.jsonl':rows[4]['data']['labels_sha256'],
            'summary.json':rows[5]['data']['summary_sha256'],'protocol.md':frozen['protocol_sha256']}
    for name,digest in checks.items():
        if file_hash(output/name)!=digest:raise ValueError('sealed artifact changed: '+name)
    sensors=read_rows(output/'sensors.jsonl');features=read_rows(output/'features.jsonl');labels=read_rows(output/'labels.jsonl')
    geometry=None;current=None;index=None;before_time=None;checked=0
    for record in records(SOURCE/'episodes.jsonl'):
        kind,d=record['kind'],record['data']
        if kind=='environment':
            geometry=d['geometry']
            if {k:d[k] for k in ('sensors','model_timestep_s','control_timestep_s','integrator')}!=json.loads((output/'sensor_metadata.json').read_text()):raise ValueError('sensor metadata differs from source')
        elif kind=='control_started':
            index=d['global_control'];current=sensors[index];sample_index=0
            if any(current[k]!=d[k] for k in ('global_control','step','control')):raise ValueError('projection/source control differs')
        elif kind=='integrator_call_started':
            before_time=d['before']['time_s']
            if d['within_control_index']==0:
                buffers=d['before']['wrist_sensor_buffers']
                if current['before_time_s']!=before_time or current['baseline_force_N']!=buffers['force_ee']['values'] or current['baseline_torque_Nm']!=buffers['torque_ee']['values']:raise ValueError('sensor baseline differs from source')
        elif kind=='integrator_call_completed':
            s=d['after'];buffers=s['wrist_sensor_buffers']
            expected={'time_s':s['time_s'],'force_N':buffers['force_ee']['values'],'torque_Nm':buffers['torque_ee']['values']}
            if current['after'][sample_index]!=expected:raise ValueError('projected sensor sample differs')
            gold={'substep':d['within_control_index'],'interval_s':[before_time,s['time_s']],**contact_membership(s['contacts'],geometry)}
            if labels[index]['native_samples'][sample_index]!=gold:raise ValueError('evaluator sample differs from raw contact')
            sample_index+=1
        elif kind=='control_completed':
            if sample_index!=25:raise ValueError('incomplete control projection')
            label=labels[index];flags={key:any(s[key] for s in label['native_samples']) for key in ('gripper','arm','self')}
            expected_cohort=cohort(flags['gripper'],flags['arm'],flags['self'])
            if any(label[key]!=value for key,value in flags.items()) or label['cohort']!=expected_cohort:raise ValueError('control gold cohort differs from native samples')
            if label['endpoint_gripper']!=label['native_samples'][-1]['gripper'] or label['endpoint_missed_gripper_only']!=(expected_cohort=='gripper_only' and not label['endpoint_gripper']):raise ValueError('registered missed-contact subset differs')
            checked+=1
    if checked!=970:raise ValueError('source projection incomplete')
    if [sensor_features(s) for s in sensors]!=features:raise ValueError('feature reconstruction differs')
    summary=evaluate(features,labels)
    if summary!=json.loads((output/'summary.json').read_text()):raise ValueError('registered score reconstruction differs')
    return {'status':'pass','analysis_raw_sha256':file_hash(output/'episodes.jsonl'),'source_sha256':SOURCE_SHA256,
        'artifacts':checks,'sensor_rows':len(sensors),'feature_rows':len(features),'gold_rows':len(labels),
        'sealing_order':'sensors then pure features then oracle labels','physics_calls':0,'model_calls':0}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['run','audit']);p.add_argument('--output',required=True);a=p.parse_args()
    if a.mode=='run':run(a.output)
    else:print(json.dumps(audit(a.output),indent=2))


if __name__=='__main__':main()
