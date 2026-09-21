# Server setup with Conda mirrors

The intended environment is Conda Python 3.10. On restricted networks, configure a
reachable Conda and PyPI mirror before creating the environment:

```bash
conda config --remove-key channels || true
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge
conda config --set channel_priority strict
python -m pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple
conda env create -f environment.yml
conda activate laya-embodied
pip install -e ".[mujoco,libero,dev]"
```

The model checkpoint is intentionally outside this repository. The current server
environment was created with Miniforge and Python 3.10; the Conda export records the
resolved packages after installation.
