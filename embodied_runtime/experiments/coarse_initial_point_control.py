"""Single initial visual target plus live proprioception; explicit stale admission."""
from __future__ import annotations

import argparse
from copy import deepcopy
import os
from pathlib import Path
import time

from ..decision_interface import CanonicalDecisionInput, CanonicalDecisionState, evidence, geometric_effects
from . import coarse_point_probe as base
from .coarse_point_boundary_probe import MATCHED_ARGUMENTS
from .predicate_verification import one_record
from .records import file_hash, load_records

VERSION = 'initial-point-live-proprioception-v1'
PROTOCOL = Path(__file__).resolve().parents[2]/'docs/research/coarse_initial_point_control_protocol.md'
BASELINE_COMMIT = 'b72fcdc494522ea49cb7fd7d9f0b75f2789de49f'
BASELINE_SHA256 = 'd9ed0bc2b10b61b047e44ec37a03ea788b4e88e2f8d06edd8171bcd29677f319'


class InitialPointGrounding:
    """Only the first RGB-D frame initializes the target; later frames are audit data."""

    def __init__(self):
        self.initial = None
        self.capture_seq = None
        self.capture_time = None
        self.initial_call_started_wall_time = None
        self.calls = 0

    def point_call(self, worker, frame, recorder):
        if self.initial is None:
            if self.calls:
                raise RuntimeError('Initial call cannot be retried')
            self.calls += 1
            self.capture_seq = int(frame['capture_seq'])
            self.capture_time = float(frame['capture_sim_time'])
            self.initial_call_started_wall_time = time.time()
            return base.point_call(worker, frame, recorder)
        # No RGB, depth, model, target motion estimate or identity correction is read.
        return None, None

    def admit_point(self, parsed, audit, frame, recorder):
        if self.initial is None:
            self.initial = base.admit_point(parsed, audit, frame)
            recorder.record('initial_target_frozen', {
                'source_capture_seq':self.capture_seq, 'source_capture_sim_time':self.capture_time,
                'admitted':self.initial, 'completed_model_calls':self.calls,
                'admission_policy':VERSION, 'current_visibility_verified':None})
        age = float(frame['capture_sim_time'])-self.capture_time
        if age < 0 or self.calls != 1:
            raise ValueError('Initial target clock or call count invalid')
        recorder.record('target_grounding_schedule', {
            'boundary_capture_seq':int(frame['capture_seq']), 'source_capture_seq':self.capture_seq,
            'target_source_sim_time_s':self.capture_time,
            'boundary_read_sim_time_s':float(frame['capture_sim_time']), 'target_age_sim_s':age,
            'wall_elapsed_since_initial_call_started_s':time.time()-self.initial_call_started_wall_time,
            'initial_call_started_wall_time_s':self.initial_call_started_wall_time,
            'target_refreshed':int(frame['capture_seq']) == self.capture_seq,
            'current_rgbd_consumed_for_target':int(frame['capture_seq']) == self.capture_seq,
            'completed_model_calls':self.calls, 'fixed_position_world_m':self.initial['position_world_m'],
            'admission_policy':VERSION, 'stationarity_assumption_verified':None})
        return deepcopy(self.initial)

    def decision_input(self, admitted, proprio, frame, history=()):
        if admitted != self.initial:
            raise ValueError('Initial target changed')
        original = base.decision_input(admitted, proprio, frame, history)
        fields = dict(original.state.fields)
        age = float(frame['capture_sim_time'])-self.capture_time
        fields['target.position_m'] = evidence(admitted['position_world_m'], 'sensor',
            'initial completed POINT RGB-D projection copied unchanged; no current observation')
        fields['target.position_definition'] = evidence('initial_POINT_containing_pixel_center_depth', 'sensor',
            'initial source pixel/depth only; later captured RGB-D unconsumed')
        fields['quality.geometry_valid'] = evidence(True, 'derived',
            'initial finite projection admitted under explicit stationary-target assumption; current validity unverified')
        fields['quality.geometry_age_s'] = evidence(age, 'sensor', 'current simulator read time minus initial RGB-D capture time')
        fields['quality.semantic_age_s'] = evidence(age, 'sensor', 'current simulator read time minus sole POINT source capture time')
        state = CanonicalDecisionState(fields, {
            **original.state.meta, 'admission_policy':VERSION,
            'target_source_capture_seq':self.capture_seq, 'target_source_sim_time_s':self.capture_time,
            'target_refreshed':int(frame['capture_seq']) == self.capture_seq,
            'current_rgbd_consumed_for_target':int(frame['capture_seq']) == self.capture_seq,
            'robot_proprioception_read_sim_time_s':float(frame['capture_sim_time']),
            'robot_observation_exact_sample_time_s':None,
            'stationarity_assumption_verified':None})
        return CanonicalDecisionInput(state, original.candidates,
                                      geometric_effects(state, original.candidates), history)


def frozen_baseline(directory):
    path = Path(directory)/'episodes.jsonl'
    if file_hash(path) != BASELINE_SHA256:
        raise ValueError('Frozen fresh-query boundary baseline changed')
    rows, errors = load_records(path)
    start = one_record(rows,'run_start')
    config = start['resolved_config']
    if errors or start['manifest']['code']['commit'] != BASELINE_COMMIT or config['steps'] != 40:
        raise ValueError('Unexpected fresh-query baseline')
    if one_record(rows,'termination') != {'boundary':25,'executed_primitives':25,
            'laya_decisions':0,'reason':'runtime_or_admission_failure'}:
        raise ValueError('Baseline terminal boundary changed')
    return config


def run(args):
    if args.steps != 40 or args.seed != 1 or args.init_state_id != 0 or args.condition != 'rule' or args.timeout_s != 900.:
        raise ValueError('Frozen init0/seed1/rule/40 primitives/900 seconds required')
    if Path(args.output).resolve() == Path(args.baseline_source).resolve():
        raise ValueError('New output required')
    previous = frozen_baseline(args.baseline_source)
    if any(getattr(args,key) != previous[key] for key in MATCHED_ARGUMENTS):
        raise ValueError('Model/physical settings differ from frozen fresh-query condition')
    profile = {
        'name':VERSION, 'primary_outcome':'first physical boundary under initial-point admission',
        'baseline_source':str(Path(args.baseline_source).resolve()), 'baseline_sha256':BASELINE_SHA256,
        'baseline_commit':BASELINE_COMMIT, 'baseline_protocol_sha256':previous['protocol_sha256'],
        'fresh_reset':True, 'archived_controls_executed':False, 'archived_state_restored':False,
        'changed_behavior':'one initial completed POINT; fixed initial world position plus live proprioception',
        'admission_policy':VERSION, 'default_uncertainty_gates_validated':False,
        'max_executed_primitives':40, 'model_call_budget':1, 'no_automatic_budget_extension':True,
        'unchanged':['initial POINT query/checkpoint/settings/strict admission', 'canonical nominal rule and tie-break',
            'seven-action family', 'native controller/executor', 'external contact abort threshold 1 N',
            'execution contracts', '900-second wall limit'],
        'target_estimate_refreshed_after_initial':False, 'tracker':False,
        'execution_environment':{key:os.environ.get(key) for key in
            ('CUDA_VISIBLE_DEVICES','MUJOCO_GL','MUJOCO_EGL_DEVICE_ID','HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE')}}
    return base.run(args, protocol=PROTOCOL, experiment_profile=profile, grounding=InitialPointGrounding())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--baseline-source',default='/home/junhongli/projects/laya-embodied-runtime/runs/autonomous-research/coarse-point-boundary-01')
    parser.add_argument('--steps',type=int,default=40)
    parser.add_argument('--seed',type=int,default=1)
    parser.add_argument('--init-state-id',type=int,default=0)
    parser.add_argument('--device',default='cuda')
    parser.add_argument('--locateanything-path',default='/home/junhongli/models/huggingface/LocateAnything-3B')
    parser.add_argument('--libero-root',default='/home/junhongli/projects/LIBERO')
    parser.add_argument('--config-dir',default='/home/junhongli/runs/libero-config')
    parser.add_argument('--timeout-s',type=float,default=900.)
    parser.set_defaults(condition='rule')
    print(run(parser.parse_args()))
