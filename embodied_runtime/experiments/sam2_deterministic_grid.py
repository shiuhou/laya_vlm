"""Dense positional-grid compatibility overlay; no learned parameter changes."""
from __future__ import annotations

import copy
import hashlib
from types import MethodType

from ..contracts import require


def _identical_bytes(left, right):
    import torch
    def raw(value):
        return value.detach().contiguous().view(torch.uint8).cpu().numpy().tobytes()
    return left.dtype == right.dtype and left.shape == right.shape and raw(left) == raw(right)


def deterministic_grid_forward(self, size):
    import torch
    h, w = size
    require(type(h) is int and type(w) is int and 0 < h <= 2**24 and 0 < w <= 2**24,
            "exact float32 integer grid range required")
    device = self.positional_encoding_gaussian_matrix.device
    y_embed = (torch.arange(1, h+1, device=device, dtype=torch.float32) - 0.5) / h
    x_embed = (torch.arange(1, w+1, device=device, dtype=torch.float32) - 0.5) / w
    coords = torch.stack([x_embed[None, :].expand(h, w), y_embed[:, None].expand(h, w)], dim=-1)
    return self._pe_encoding(coords).permute(2, 0, 1)


def install_and_verify(model):
    """Check exact native-size coordinates and same-device encoded PE before use.

    Reference sums run on CPU, not unsupported CUDA. Downstream reference PE
    runs on the same GPU/buffer as the overlay. Determinism never turns off.
    This is a dense-grid equivalence check, not full-model GPU replay.
    """
    import torch
    require(torch.are_deterministic_algorithms_enabled(), "strict determinism required")
    layer = model.sam_prompt_encoder.pe_layer
    size = model.sam_prompt_encoder.image_embedding_size
    require(tuple(size) == (64, 64), "only the preregistered native64 grid is supported")
    h, w = size
    weight = layer.positional_encoding_gaussian_matrix
    original_weight = weight.detach().clone()
    digest = hashlib.sha256(weight.detach().cpu().numpy().tobytes()).hexdigest()
    with torch.inference_mode():
        cpu_layer = copy.deepcopy(layer).cpu()
        native_cpu = cpu_layer.forward(size)
        overlay_cpu = deterministic_grid_forward(cpu_layer, size)
        grid = torch.ones((h, w), device="cpu", dtype=torch.float32)
        reference_coords = torch.stack([(grid.cumsum(dim=1)-0.5)/w,
                                        (grid.cumsum(dim=0)-0.5)/h], dim=-1).to(weight.device)
        y = (torch.arange(1, h+1, device=weight.device, dtype=torch.float32)-0.5)/h
        x = (torch.arange(1, w+1, device=weight.device, dtype=torch.float32)-0.5)/w
        overlay_coords = torch.stack([x[None, :].expand(h, w), y[:, None].expand(h, w)], dim=-1)
        reference_pe = layer._pe_encoding(reference_coords).permute(2, 0, 1)
        overlay_pe = deterministic_grid_forward(layer, size)
        require(_identical_bytes(native_cpu, overlay_cpu) and _identical_bytes(reference_coords, overlay_coords)
                and _identical_bytes(reference_pe, overlay_pe) and _identical_bytes(weight, original_weight),
                "dense-grid equivalence failed; do not infer", "NUMERICAL_MISMATCH")
    layer.forward = MethodType(deterministic_grid_forward, layer)
    return dict(condition="sam2-dense-grid-arange/1", size=list(size),
        original_cpu_vs_overlay_cpu_bitwise_equal=True, coordinate_grid_bitwise_equal=True,
        same_gpu_reference_vs_overlay_PE_bitwise_equal=True, max_abs_PE_difference=0.0,
        gaussian_buffer_sha256=digest, learned_buffer_changed=False,
        strict_deterministic_algorithms=True, native_source_modified=False,
        override_scope="this model instance sam_prompt_encoder.pe_layer.forward only",
        forward_with_coords_changed=False, full_native_cuda_model_equivalence="NOT_RUN_UNSUPPORTED_CUMSUM",
        reference_provenance="original CPU ones/cumsum grid, encoded on same GPU and learned buffer")
