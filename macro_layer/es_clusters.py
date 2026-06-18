"""
Macro-Layer Semantic Clusters — Spanish (ES)
6-cluster operational/steganographic dictionaries.
Words are in lemma/base form to match spaCy es_core_news_sm output.
"""

from typing import Dict, List

ES_CLUSTERS: Dict[str, Dict[str, List[str]]] = {
    "resources": {
        "scarcity": [
            "racionar", "déficit", "hambre", "estricto", "apretar",
            "escasez", "falta", "restringir", "agotar", "mínimo",
            "carencia", "austeridad", "congelar", "recorte", "privar",
            "mermar", "limitar", "presupuesto", "exprimir", "agotamiento",
            "gravar", "secar", "insuficiencia", "magro", "estrangular",
        ],
        "abundance": [
            "excedente", "inundar", "opulento", "interminable", "recurso",
            "riqueza", "desbordar", "generoso", "amplio", "abundante",
            "próspero", "proliferar", "profuso", "exceso", "derroche",
            "tesoro", "fluir", "floreciente", "colmar", "rebosar",
            "saturar", "cascada", "auge", "superávit", "exuberante",
        ],
    },
    "power": {
        "control": [
            "imponer", "dictar", "autorizar", "red", "desplegar",
            "ordenar", "dominar", "gobernar", "mandato", "vigilancia",
            "coercionar", "obligar", "vigilar", "regular", "anular",
            "contener", "aprovechar", "gestionar", "dirigir", "suprimir",
            "ejecutar", "canalizar", "bloquear", "controlar", "mandar",
        ],
        "submission": [
            "soportar", "asignado", "forzado", "arrastrado", "ceder",
            "obedecer", "someterse", "subordinado", "deferir", "aceptar",
            "capitular", "rendirse", "tolerar", "sucumbir", "resignarse",
            "confinar", "atrapar", "presionar", "impotente", "absorber",
            "doblegarse", "transigir", "subjugado", "plegarse", "acatar",
        ],
    },
    "visibility": {
        "concealment": [
            "oscurecer", "interceptar", "velo", "cifrar", "sombra",
            "capa", "ocultar", "disimular", "enmascarar", "cubrir",
            "enterrar", "suprimir", "emboscar", "envolver", "camuflar",
            "filtrar", "desviar", "cegar", "encubrir", "amortiguar",
            "sumergir", "invisible", "silenciar", "encriptar", "tapar",
        ],
        "exposure": [
            "difundir", "claro", "obvio", "superficie", "brillante",
            "revelar", "exponer", "transparente", "abierto", "visible",
            "iluminar", "manifestar", "mostrar", "señalar", "publicar",
            "manifiesto", "desenmascarar", "develar", "declarar", "desnudo",
            "explícito", "ostensible", "divulgar", "directo", "descubrir",
        ],
    },
    "temporal": {
        "past_nostalgic": [
            "raíces", "restaurar", "memoria", "antes", "legado",
            "regresar", "tradición", "antiguo", "recordar", "reminiscencia",
            "patrimonio", "origen", "establecer", "reliquia", "nostalgia",
            "recuperar", "antepasado", "retroceder", "pasado", "vestigio",
            "archivar", "extinto", "anticuado", "histórico", "fundador",
        ],
        "future_projective": [
            "horizonte", "entrante", "avanzar", "amenaza", "trayectoria",
            "progreso", "innovar", "emerger", "visión", "objetivo",
            "escalar", "inminente", "desplegar", "proyectar", "próximo",
            "surgir", "converger", "presagiar", "reunir", "pronóstico",
            "impender", "prever", "anticipar", "movilizar", "desatar",
        ],
    },
    "cognitive": {
        "scientific": [
            "calcular", "variable", "física", "métrica", "observar",
            "estructura", "analizar", "empírico", "parámetro", "medir",
            "cuantificar", "modelar", "datos", "hipótesis", "sistemático",
            "lógica", "fórmula", "experimentar", "evidencia", "verificar",
            "calibrar", "clasificar", "precisión", "algoritmo", "derivar",
        ],
        "emotional": [
            "sentir", "esperar", "alma", "desesperación", "intuitivo",
            "abstracto", "percibir", "creer", "soñar", "sufrir",
            "llorar", "amar", "temer", "doler", "anhelar",
            "lamentar", "añorar", "angustiar", "imaginar", "desear",
            "empatizar", "tristeza", "pasión", "sincero", "compasión",
        ],
    },
    "kinetic": {
        "aggression": [
            "golpear", "brecha", "cinético", "eliminar", "objetivo",
            "atacar", "asaltar", "destruir", "neutralizar", "ruptura",
            "penetrar", "aplastar", "abrumar", "incursión", "detonar",
            "movilizar", "lanzar", "involucrar", "escalar", "aniquilar",
            "apoderarse", "capturar", "impactar", "percutir", "arremeter",
        ],
        "diplomacy": [
            "negociar", "mantener", "dilatar", "tratado", "equilibrio",
            "alto", "diálogo", "mediar", "estabilizar", "pausa",
            "diferir", "reconciliar", "compromiso", "retirar", "contener",
            "vigilar", "observar", "sostener", "retener", "moderar",
            "ceder", "resolver", "acordar", "pacificar", "distender",
        ],
    },
}
