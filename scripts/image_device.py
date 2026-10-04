"""Device policy for the bounded image experiments; no retry on CUDA failure."""

_CUDA_REQUIRED = False


def require_cuda():
    """Latch GPU-only execution in a disposable CUDA-policy probe child."""
    global _CUDA_REQUIRED
    _CUDA_REQUIRED = True
    return select_device()


def select_device():
    import torch

    if torch.cuda.is_available():
        return 'cuda'
    if _CUDA_REQUIRED:
        raise RuntimeError('CUDA address policy requires an available CUDA device')
    return 'cpu'


def prepare_device(model, record):
    device = select_device()
    record('device_selected', device=device)
    if device == 'cuda':
        # Device-only transfer preserves FP16 denoisers and the F32 VAE.
        model.to(device)
    return device
