"""Audited invocation of the prepared venv without dereferencing its Python link."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

from ..contracts import require
from .p1_segmentation_probe import SAM_SETTINGS, read, write


PREFLIGHT = """
import json, os, sys, torch
from pathlib import Path
expected = sys.argv[1]
record = dict(executable=sys.executable, prefix=sys.prefix, base_prefix=sys.base_prefix,
              torch=torch.__version__, torch_file=torch.__file__,
              cuda_initialized=torch.cuda.is_initialized(), inference_performed=False)
record['passed'] = (os.path.abspath(sys.executable) == expected
    and Path(sys.prefix).absolute() == Path(expected).parent.parent
    and torch.__version__ == '2.5.1+cu121' and not record['cuda_initialized'])
print(json.dumps(record))
sys.exit(0 if record['passed'] else 1)
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["preflight", "masks"])
    parser.add_argument("--output", required=True, help="preflight receipt file or masks run root")
    parser.add_argument("--assets", required=True)
    parser.add_argument("--gpu-uuid", required=True)
    args = parser.parse_args()
    assets = read(args.assets)
    # absolute() preserves the venv invocation name; resolve() would bypass it.
    executable = str(Path(assets["python_executable"]).absolute())
    require(args.gpu_uuid.startswith("GPU-"), "explicit GPU UUID required")
    env = dict(os.environ, CUDA_VISIBLE_DEVICES=args.gpu_uuid,
               CUBLAS_WORKSPACE_CONFIG=SAM_SETTINGS["cublas_workspace_config"])
    started = datetime.now(timezone.utc).isoformat()
    if args.stage == "preflight":
        command = [executable, "-c", PREFLIGHT, executable]
        result = subprocess.run(command, env=env, text=True, capture_output=True)
        receipt = dict(command=command, started_at_utc=started, exit_code=result.returncode,
                       stdout=result.stdout, stderr=result.stderr, hidden_retry=False)
        if result.returncode == 0:
            receipt["environment"] = json.loads(result.stdout)
        write(args.output, receipt)
    else:
        root = Path(args.output)
        require(read(root/"registration.json")["environment_receipt"] == assets,
                "launcher assets differ from registration")
        command = [executable, "-m", "embodied_runtime.experiments.p1_segmentation_probe",
                   "masks", "--output", str(root)]
        with (root/"masks-process.log").open("x") as log:
            result = subprocess.run(command, env=env, stdout=log, stderr=subprocess.STDOUT)
        write(root/"masks-process.json", dict(command=command, started_at_utc=started,
            ended_at_utc=datetime.now(timezone.utc).isoformat(), exit_code=result.returncode,
            gpu_uuid=args.gpu_uuid, cublas_workspace=env["CUBLAS_WORKSPACE_CONFIG"], hidden_retry=False))
    print(f"{args.stage} exit {result.returncode}")
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
