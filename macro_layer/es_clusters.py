"""
Macro-Layer Semantic Clusters — Spanish (ES)
Exact Spanish translations of the four base semantic cluster dictionaries.
Used by MultilingualSemanticAnalyzer when language_code == "ES".

spaCy lemmatizes Spanish text; the word lists below are in lemma/base form
so they match spaCy's es_core_news_sm output reliably.
"""

from typing import Dict, List

ES_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "apretado", "estricto", "presupuesto", "límite", "escaso",
            "falta", "escasez", "restringir", "agotar", "mínimo",
            "reducir", "recorte", "carencia", "privación", "déficit",
        ],
        "abundance": [
            "fluir", "masivo", "interminable", "abundancia", "excedente",
            "rico", "generoso", "amplio", "abundante", "riqueza",
            "pleno", "holgado", "cuantioso", "profuso", "desbordante",
        ],
    },
    "power": {
        "control": [
            "gestionar", "imponer", "dictar", "mandar", "dominar",
            "controlar", "dirigir", "gobernar", "ordenar", "autoridad",
            "mandato", "decreto", "exigir", "regular", "fiscalizar",
        ],
        "submission": [
            "someterse", "asignado", "forzar", "cumplir", "ceder",
            "obedecer", "subordinado", "diferir", "aceptar", "soportar",
            "acatar", "sometido", "dependiente", "resignarse", "rendir",
        ],
    },
    "visibility": {
        "concealment": [
            "capa", "oscurecer", "sombra", "ocultar", "encubrir",
            "enmascarar", "cubrir", "enterrar", "suprimir", "disimular",
            "velar", "silenciar", "esconder", "tapar", "camuflar",
        ],
        "exposure": [
            "brillante", "obvio", "claro", "revelar", "exponer",
            "transparente", "abierto", "visible", "iluminar", "manifestar",
            "mostrar", "descubrir", "publicar", "evidenciar", "señalar",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "regresar", "memoria", "raíz", "tradición", "pasado",
            "antiguo", "restaurar", "recordar", "añoranza", "herencia",
            "origen", "retorno", "ayer", "historia", "nostálgico",
        ],
        "future_projective": [
            "avanzar", "horizonte", "próximo", "futuro", "adelante",
            "progreso", "innovar", "vislumbrar", "prospecto", "visión",
            "emergente", "mañana", "planificar", "proyectar", "impulsar",
        ],
    },
}
