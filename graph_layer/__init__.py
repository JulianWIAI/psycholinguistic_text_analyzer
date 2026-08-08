"""
graph_layer — corpus cross-reference graph engine.
Tries to use psycho_core.GraphEngine (C++ compiled version).
Falls back to graph_layer.engine.GraphEngine (pure Python).
"""
try:
    from psycho_core import GraphEngine as _CppEngine
    GraphEngine = _CppEngine
    _BACKEND = "cpp"
except (ImportError, AttributeError):
    from graph_layer.engine import GraphEngine
    _BACKEND = "python"

__all__ = ["GraphEngine", "_BACKEND"]
