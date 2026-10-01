"""Token counts -> energy (Wh) -> water (mL). Math is documented in RESEARCH.md §4-5."""
import fnmatch
import os
import tomllib
from dataclasses import dataclass

BANDS = ("low", "mid", "high")
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "coefficients.toml")
USER_PATH = os.path.expanduser("~/.config/drip/coefficients.toml")


@dataclass
class Tokens:
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0

    def __iadd__(self, o):
        self.input += o.input
        self.output += o.output
        self.cache_read += o.cache_read
        self.cache_write += o.cache_write
        return self

    @property
    def total(self):
        return self.input + self.output + self.cache_read + self.cache_write


class Coefficients:
    def __init__(self, path=None):
        path = path or (USER_PATH if os.path.exists(USER_PATH) else DEFAULT_PATH)
        with open(path, "rb") as f:
            self.cfg = tomllib.load(f)
        self.path = path
        self._cache = {}

    def model(self, name):
        """Return the matching [[model]] entry for a model id."""
        name = (name or "").lower()
        if name not in self._cache:
            self._cache[name] = next(
                m for m in self.cfg["model"] if fnmatch.fnmatch(name, m["match"].lower())
            )
        return self._cache[name]

    def is_estimated(self, name):
        return bool(self.model(name).get("fallback"))

    def per_1k_wh(self, model, band="mid"):
        """Wh per 1K tokens for each token type, for this model and band."""
        e = self.cfg["energy"]
        m = self.model(model)
        scale = m["output_price"] / e["reference_output_price"]
        e_in = e[f"input_{band}"] * scale
        cr = m["cache_read"] if band == "mid" else e[f"cache_read_{band}"]
        cw = m["cache_write"] if band == "mid" else e[f"cache_write_{band}"]
        return {
            "input": e_in,
            "output": e[f"output_{band}"] * scale,
            "cache_read": e_in * cr,
            "cache_write": e_in * cw,
        }

    def energy_wh(self, tokens, model, band="mid"):
        c = self.per_1k_wh(model, band)
        return (
            tokens.input * c["input"]
            + tokens.output * c["output"]
            + tokens.cache_read * c["cache_read"]
            + tokens.cache_write * c["cache_write"]
        ) / 1000

    def water_factor(self, band="mid", onsite=False):
        return self.cfg["water_factor_onsite" if onsite else "water_factor"][band]

    def water_ml(self, tokens, model, band="mid", onsite=False):
        # Wh × L/kWh = mL
        return self.energy_wh(tokens, model, band) * self.water_factor(band, onsite)


# Relatable units (RESEARCH.md §8; EPA WaterSense for flush/shower)
GLASS_ML = 237
FLUSH_ML = 6060
SHOWER_MIN_ML = 9460


def fmt_ml(ml):
    if ml < 10:
        return f"{ml:.1f} mL"
    if ml < 1000:
        return f"{ml:.0f} mL"
    return f"{ml / 1000:.1f} L"


def relatable(ml):
    if ml < 6000:
        n = ml / GLASS_ML
        return f"{n:.1f} glass" + ("" if round(n, 1) == 1 else "es")
    if ml < 100_000:
        n = ml / FLUSH_ML
        return f"{n:.1f} toilet flushes"
    return f"{ml / SHOWER_MIN_ML:.0f} shower-minutes"
