"""See what an embedding is: turn a few texts into vectors and compare them.

Run (Ollama must be running and the model downloaded: ollama pull bge-m3):
    python tools/embedding_demo.py

For each text the script asks Ollama for its embedding (a list of numbers), prints the length and the
first numbers, and then the cosine similarity of every pair of texts (1.0 = same direction = same meaning,
around 0 = unrelated). Read-only helper; nothing is stored.
"""
import json
import math
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/embed"
MODEL = "bge-m3"

TEXTS = [
    "ovesný nápoj",                        # Czech: oat drink
    "oat drink",
    "Haferdrink ohne Zucker",              # German: oat drink without sugar
    "hořká čokoláda s lískovými ořechy",   # Czech: dark chocolate with hazelnuts
]


def embed(texts: list[str]) -> list[list[float]]:
    """Ask Ollama for the embeddings of several texts in one request."""
    body = json.dumps({"model": MODEL, "input": texts}).encode("utf-8")
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))["embeddings"]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity: how similar the directions of two vectors are."""
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


def main() -> None:
    vectors = embed(TEXTS)

    print(f"Model: {MODEL}")
    for text, vector in zip(TEXTS, vectors):
        first = ", ".join(f"{x:+.3f}" for x in vector[:5])
        print(f"{text:<38} {len(vector)} numbers: [{first}, ...]")

    print("\nCosine similarity of every pair:")
    for i in range(len(TEXTS)):
        for j in range(i + 1, len(TEXTS)):
            print(f"  {cosine(vectors[i], vectors[j]):.3f}  {TEXTS[i]}  <->  {TEXTS[j]}")


if __name__ == "__main__":
    main()
