"""Shared setup for the report figures: repo root on sys.path, output folder, save helper."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=200)
    print("Saved", OUT / f"{name}.png")


def money(v):
    if abs(v) >= 1e6:
        return f"${v/1e6:.2f}M"
    if abs(v) >= 1e3:
        return f"${v/1e3:.0f}k"
    return f"${v:.0f}"
