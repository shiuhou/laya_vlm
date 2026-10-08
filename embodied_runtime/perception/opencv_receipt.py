"""Read-only CPU OpenCV process identity; no algorithm or thread mutations."""
from hashlib import sha256
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def opencv_process_receipt():
    import cv2
    package = Path(cv2.__file__).resolve().parent
    binaries = sorted(package.glob('*.so'))
    distributions = {}
    for name in ('opencv-python-headless','opencv-python','numpy'):
        try:
            distributions[name] = version(name)
        except PackageNotFoundError:
            distributions[name] = None
    return dict(cv2_version=cv2.__version__,distributions=distributions,
        cv2_module_path=str(Path(cv2.__file__).resolve()),
        binary_sha256={str(p):sha256(p.read_bytes()).hexdigest() for p in binaries},
        build_information_sha256=sha256(cv2.getBuildInformation().encode()).hexdigest(),
        opencv_threads=cv2.getNumThreads(),optimized=cv2.useOptimized(),
        opencl_active=cv2.ocl.useOpenCL(),parameters_changed=False)
