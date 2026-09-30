# P0 dependencies

Target: Linux x86_64, CPython **3.10.21**. The hash-pinned core/dev lock does not
install model weights, PyTorch, LIBERO, MuJoCo, Pillow or OpenCV.

```sh
python3.10 -m venv .venv-p0
.venv-p0/bin/python -m pip install --require-hashes -r requirements/p0-py310-linux.lock
.venv-p0/bin/python -m pip install --no-deps --no-build-isolation -e .
.venv-p0/bin/python -m pip check
```

`p0.in` pins direct dependencies and build tools. The generated lock also pins
transitive dependencies and accepted artifact hashes. `lock-toolchain.txt`
records the isolated resolver environment (pip 25.1.1, pip-tools 7.5.1); it is not
part of the runtime environment. To regenerate in that tool environment:

```sh
pip-compile --generate-hashes --allow-unsafe --strip-extras --index-url https://pypi.org/simple --output-file requirements/p0-py310-linux.lock requirements/p0.in
```

`baseline/` is a read-only inventory of the previous model/simulator environment,
including its local source paths. It is **not a fully reproducible model lock**.
The existing environment has not been upgraded. Real Qwen/model dependencies
must receive a separate lock when the corresponding later phase is implemented.

Explicit setuptools package discovery is needed because this repository has
several top-level non-package directories. Package data retains task BDDL/JSON;
it does not add those tasks to P0 execution.
