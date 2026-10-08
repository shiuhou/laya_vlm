from pathlib import Path
from types import SimpleNamespace

from embodied_runtime.experiments.p1_perception_pipeline_dev import build_stages, execute_stages, parser
from embodied_runtime.experiments.p1_segmentation_probe import write, seal


def test_exact_source_camera_env_and_optional_tracker_command_propagation(tmp_path):
    args = parser().parse_args(['--recording', str(tmp_path/'source-a'), '--recording', str(tmp_path/'source-b'),
        '--camera', 'frontview', '--gpu-uuid', 'GPU-test', '--output', str(tmp_path/'out'), '--track',
        '--qwen-python', '/tmp/isolated-qwen/bin/python', '--seed-method', 'depth-supported-rectangle'])
    stages = build_stages(args)
    assert len(stages) == 5
    qwen = stages[0].command
    assert qwen[0] == '/tmp/isolated-qwen/bin/python'
    assert qwen[qwen.index('--camera')+1] == 'frontview'
    assert qwen.count('--recording') == 2
    assert stages[1].command[stages[1].command.index('--input')+1] == stages[0].output
    assert stages[2].command[stages[2].command.index('--input')+1] == stages[1].output
    for i in range(2):
        tracking = stages[3+i].command
        assert tracking[tracking.index('--recording')+1] == str((tmp_path/('source-a' if i==0 else 'source-b')).resolve())
        assert tracking[tracking.index('--geometry')+1] == stages[2].output
        assert tracking[tracking.index('--seed-method')+1] == 'depth-supported-rectangle'
    assert parser().get_default('seed_method') == 'mask-rectangle'


def test_upstream_runtime_failure_preserved_and_never_launches_downstream(tmp_path):
    args = parser().parse_args(['--recording', '/source', '--gpu-uuid', 'GPU-test', '--output', str(tmp_path)])
    stages = build_stages(args)
    calls = []

    def failed(command, **kwargs):
        calls.append(command)
        assert kwargs['env']['CUDA_VISIBLE_DEVICES'] == 'GPU-test'
        out = Path(stages[0].output)
        out.mkdir()
        write(out/'outputs.json', dict(runtime_failure={'error':'actual upstream failure'}))
        seal(out)
        # Even a buggy worker that exits zero cannot erase its runtime failure.
        return SimpleNamespace(returncode=0)

    result = execute_stages(stages, output=tmp_path, environment={'CUDA_VISIBLE_DEVICES':'GPU-test'}, timeout_s=10, runner=failed)
    assert len(calls) == 1
    assert result['first_failure'] == 'grounding'
    assert [x['status'] for x in result['stages']] == ['FAILED','NOT_ATTEMPTED','NOT_ATTEMPTED']
    assert (Path(stages[0].output)/'outputs.json').is_file()
    assert not Path(stages[1].output).exists()
