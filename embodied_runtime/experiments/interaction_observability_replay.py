"""Integrity replay of this probe's recorded low-level controls on fresh resets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .interaction_observability import ARMS, write_json
from .records import code_identity, file_hash


def replay(args):
    from .privileged_multistage_task import WineBottleBottomDrawerAdapter
    source, out = Path(args.source),Path(args.output)
    out.mkdir(parents=True,exist_ok=False)
    sensor_seal = json.loads((source/'sensor-seal.json').read_text())
    if file_hash(source/'sensors.jsonl') != sensor_seal['sha256']['sensors.jsonl']:
        raise ValueError('recorded controls changed')
    evaluation = json.loads((source/'evaluation/summary.json').read_text())
    if file_hash(source/'evaluator-only/labels.json') != evaluation['oracle_labels_sha256']:
        raise ValueError('recorded evaluator states changed')
    controls = [json.loads(line) for line in (source/'sensors.jsonl').read_text().splitlines()]
    labels = json.loads((source/'evaluator-only/labels.json').read_text())
    manifest = {'code':code_identity(), 'source':str(source), 'sensor_controls_sha256':file_hash(source/'sensors.jsonl'),
        'original_diagnostic_state_sha256':file_hash(source/'evaluator-only/labels.json'),
        'fresh_reset_each_arm':True, 'controller_restore':False, 'render':False,
        'meaning':'Replay only newly recorded sensor-probe controls; not archived Task-2 low-level controls.'}
    write_json(out/'manifest.json',manifest)
    trace=[]
    try:
        for arm in ARMS:
            backend=WineBottleBottomDrawerAdapter().make_backend(args,render=False)
            try:
                w=backend.world
                initial=next(r for r in labels if r['arm']==arm and r['after_step']==-1)
                initial_error=float(np.max(np.abs(w.env.sim.get_state().flatten()-initial['state'])))
                if initial_error != 0:
                    raise RuntimeError(f'fresh {arm} initial state differs: {initial_error}')
                for row in [r for r in controls if r['arm']==arm]:
                    w.obs,_,_,_=w.env.step(row['sensor']['command'])
                    expected=next(r for r in labels if r['arm']==arm and r['after_step']==row['step'] and r['control']==row['control'])
                    actual=w.env.sim.get_state().flatten()
                    error=float(np.max(np.abs(actual-expected['state'])))
                    trace.append({'arm':arm,'step':row['step'],'control':row['control'],
                        'sim_time_s':float(w.data.time),'max_state_abs_error':error})
                    if error != 0:
                        raise RuntimeError(f'first replay mismatch: {trace[-1]}')
            finally:
                backend.close()
        write_json(out/'result.json',{'controls':len(trace),'all_272_states_exact':len(trace)==272 and all(r['max_state_abs_error']==0 for r in trace),
            'max_state_abs_error':max(r['max_state_abs_error'] for r in trace),'trace':trace})
    except BaseException as exc:
        write_json(out/'failure.json',{'error':str(exc),'trace':trace,'no_retry':True})
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--libero-root',default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir',default='/home/junhongli/runs/libero-config')
    args=parser.parse_args()
    args.seed,args.init_state_id=1,0
    replay(args)
