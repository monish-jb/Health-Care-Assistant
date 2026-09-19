class ByteTokenizer:
    """Simple byte-level tokenizer (vocab 256). Swap for BPE when you scale up."""
    vocab_size = 256

    def encode(self, text: str) -> list[int]:
        return list(text.encode("utf-8"))

    def decode(self, ids: list[int]) -> str:
        return bytes(i % 256 for i in ids).decode("utf-8", errors="replace")
