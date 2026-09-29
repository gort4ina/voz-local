def resolve_device(requested: str) -> str:
    import torch

    from app.core.errors import ApplicationError

    available = torch.cuda.is_available()
    if requested == "cuda" and not available:
        raise ApplicationError(
            "CUDA solicitada, mas indisponível. Use CPU ou configure o driver NVIDIA."
        )
    return ("cuda" if available else "cpu") if requested == "auto" else requested
