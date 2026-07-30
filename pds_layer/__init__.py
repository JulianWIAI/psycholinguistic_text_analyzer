"""
pds_layer — Ousiometric Power-Danger-Structure Analysis Package

Implements the Ousiometrics framework (Dodds et al.) which mathematically
rotates raw NRC Valence-Arousal-Dominance (VAD) scores into a tactically
richer three-axis space:

  Power     — perceived authority / dominance  [-1 Weak … +1 Dominant]
  Danger    — threat level / negativity under activation  [-1 Safe … +1 Threatening]
  Structure — order / composure / predictability  [-1 Chaotic … +1 Composed]

Module layout
─────────────
  pds_transformer.py      — Pure maths: vad_to_pds() rotation + constants
  pds_analyzer.py         — Full pipeline: VAD → rotate → 8-axis affect → aggregate
  affect_parser.py        — Pure 4-column combined-format file parser (no I/O, no cache)
  affect_path_resolver.py — Combined & per-affect path resolution (two-tier fallback)
  affect_loader.py        — Cache layer: load_affect_pack() + load_affect_lexicon() shim

Lexicon dependency
──────────────────
Reuses NRC-VAD TSV files from vad_layer/lexicons/.
Combined affect intensity files (intensity_{lang}.txt) live in the same directory.
"""

from .pds_analyzer        import analyze_ousiometrics                              # noqa: F401
from .pds_transformer     import vad_to_pds, AXIS_LABELS                           # noqa: F401
from .affect_loader       import load_affect_pack, load_affect_lexicon             # noqa: F401
from .affect_path_resolver import (                                                 # noqa: F401
    resolve_affect_path,
    resolve_combined_affect_path,
    list_available_langs,
    list_combined_available_langs,
)
from .affect_parser        import (                                                 # noqa: F401
    parse_combined_affect_file,
    empty_affect_pack,
    EMOTION_LABELS,
    EMOTION_LABELS_ORDERED,
    AffectPack,
)

__all__ = [
    # Core analysis
    "analyze_ousiometrics",
    "vad_to_pds",
    "AXIS_LABELS",
    # Affect loading (primary + compat shim)
    "load_affect_pack",
    "load_affect_lexicon",
    # Path resolution
    "resolve_combined_affect_path",
    "resolve_affect_path",
    "list_combined_available_langs",
    "list_available_langs",
    # Parser primitives (useful for testing and custom pipelines)
    "parse_combined_affect_file",
    "empty_affect_pack",
    "EMOTION_LABELS",
    "EMOTION_LABELS_ORDERED",
    "AffectPack",
]
