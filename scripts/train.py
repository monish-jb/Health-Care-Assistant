"""Train the LLM on a text corpus: python scripts/train.py --data data/processed/corpus.txt"""
import argparse
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.llm.checkpoint import save_checkpoint
from app.llm.model import CarePulseGPT, GPTConfig
from app.llm.tokenizer import ByteTokenizer


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/processed/corpus.txt")
    p.add_argument("--out", default="checkpoints/carepulse_llm.pt")
    p.add_argument("--steps", type=int, default=2000)
    p.add_argument("--batch", type=int, default=32)
    p.add_argument("--lr", type=float, default=3e-4)
    a = p.parse_args()

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    ids = torch.tensor(ByteTokenizer().encode(Path(a.data).read_text(encoding="utf-8")))
    split = int(0.9 * len(ids))
    train, val = ids[:split], ids[split:]
    cfg = GPTConfig()
    model = CarePulseGPT(cfg).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=a.lr)

    def batch(d):
        ix = torch.randint(len(d) - cfg.block_size - 1, (a.batch,))
        x = torch.stack([d[i:i + cfg.block_size] for i in ix])
        y = torch.stack([d[i + 1:i + cfg.block_size + 1] for i in ix])
        return x.to(dev), y.to(dev)

    for step in range(1, a.steps + 1):
        model.train()
        _, loss = model(*batch(train))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        if step % 100 == 0:
            model.eval()
            with torch.no_grad():
                _, vl = model(*batch(val))
            print(f"step {step} train {loss.item():.3f} val {vl.item():.3f}")
            save_checkpoint(a.out, model, opt, step)


if __name__ == "__main__":
    main()
