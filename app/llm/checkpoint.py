from pathlib import Path

import torch

from app.llm.model import CarePulseGPT, GPTConfig


def save_checkpoint(path: str, model: CarePulseGPT, optimizer=None, step: int = 0) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "config": model.config.to_dict(),
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict() if optimizer else None,
        "step": step,
    }, path)


def load_checkpoint(path: str, device: str = "cpu") -> CarePulseGPT:
    ckpt = torch.load(path, map_location=device, weights_only=True)
    model = CarePulseGPT(GPTConfig(**ckpt["config"]))
    model.load_state_dict(ckpt["model"])
    return model.to(device).eval()
