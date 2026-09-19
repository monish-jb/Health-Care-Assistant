"""Perplexity on a held-out file + guardrail smoke tests."""
import argparse
import math
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.llm.checkpoint import load_checkpoint
from app.llm.tokenizer import ByteTokenizer
from app.safety.guardrails import check_input


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/processed/val.txt")
    p.add_argument("--ckpt", default="checkpoints/carepulse_llm.pt")
    a = p.parse_args()

    model = load_checkpoint(a.ckpt)
    ids = torch.tensor(ByteTokenizer().encode(Path(a.data).read_text(encoding="utf-8")))
    bs, losses = model.config.block_size, []
    with torch.no_grad():
        for i in range(0, len(ids) - bs - 1, bs):
            _, loss = model(ids[i:i + bs][None], ids[i + 1:i + bs + 1][None])
            losses.append(loss.item())
    print(f"perplexity: {math.exp(sum(losses) / len(losses)):.2f}")

    for q in ["I have chest pain", "what is a fever"]:
        print(q, "-> emergency" if check_input(q).emergency else "-> ok")


if __name__ == "__main__":
    main()
