"""Escenarios de validación — Tablas 5 y 6 (tesis Louie)."""

EMOTION_SCENARIOS = {
    "E1": {
        "name": "Alegría",
        "expected_emotion": "joy",
        "expected_es": "Alegría",
        "script": (
            "Estoy tan feliz. Acabo de graduarme de la universidad y fue el mejor día de mi vida. "
            "No puedo dejar de sonreír, siento una alegría enorme por todo lo que logré."
        ),
        "user_id": "VALID_E1",
    },
    "E2": {
        "name": "Tristeza",
        "expected_emotion": "sadness",
        "expected_es": "Tristeza",
        "script": (
            "Hace poco perdí a mi mascota, que era mi compañero durante diez años. "
            "Me siento muy solo y con mucha pena. Cada día me cuesta un poco más."
        ),
        "user_id": "VALID_E2",
    },
    "E3": {
        "name": "Ansiedad",
        "expected_emotion": "anxiety",
        "expected_es": "Ansiedad",
        "script": (
            "Tengo un examen final mañana y no he podido dormir. Estoy muy nervioso, "
            "me tiemblan las manos y siento mucha presión. No puedo concentrarme."
        ),
        "user_id": "VALID_E3",
    },
    "E4": {
        "name": "Sorpresa",
        "expected_emotion": "surprise",
        "expected_es": "Sorpresa",
        "script": (
            "De repente me llamaron para decirme que gané un premio que ni siquiera "
            "recordaba haber postulado. No me lo puedo creer, fue totalmente inesperado."
        ),
        "user_id": "VALID_E4",
    },
    "E5": {
        "name": "Calma",
        "expected_emotion": "calmness",
        "expected_es": "Calma",
        "script": (
            "Hoy desayuné tranquilamente, leí un poco y salí a caminar por el parque. "
            "Fue un día normal y sencillo, me siento en paz y relajado."
        ),
        "user_id": "VALID_E5",
    },
}

# Emociones detectadas que cuentan como acierto parcial (tesis: % coincidencia)
EMOTION_MATCH_ALIASES: dict[str, set[str]] = {
    "joy": {"joy", "enthusiasm", "excitement", "contentment", "satisfaction", "triumph"},
    "sadness": {"sadness", "distress", "disappointment", "empathic_pain", "grief"},
    "anxiety": {"anxiety", "fear", "distress", "doubt", "horror"},
    "surprise": {"surprise", "surprise_positive", "surprise_negative", "awe", "realization"},
    "calmness": {"calmness", "contentment", "satisfaction", "interest", "contemplation"},
}

MEMORY_SCENARIOS = {
    "M1": {
        "name": "Nombre del usuario",
        "store_messages": [
            {"role": "user", "content": "Me llamo Ana María López y prefiero que me digas Ana."},
            {"role": "assistant", "content": "Perfecto Ana, es un placer conocerte."},
        ],
        "query": "What is the user's name?",
        "must_contain": ["ana", "maría", "lopez", "name"],
    },
    "M2": {
        "name": "Hobby favorito",
        "store_messages": [
            {"role": "user", "content": "Mi hobby favorito es tocar guitarra los fines de semana."},
            {"role": "assistant", "content": "Qué bueno, la guitarra es un instrumento maravilloso."},
        ],
        "query": "What is the user's favorite hobby?",
        "must_contain": ["guitarra", "guitar"],
    },
    "M3": {
        "name": "Evento emocional previo",
        "store_messages": [
            {
                "role": "user",
                "content": "La semana pasada me sentí muy triste porque reprobé un curso importante.",
            },
            {"role": "assistant", "content": "Lamento escuchar eso, debe haber sido difícil."},
        ],
        "query": "What emotional event did the user experience?",
        "must_contain": ["reprob", "triste", "sad", "failed", "course"],
    },
    "M4": {
        "name": "Preferencia conversacional",
        "store_messages": [
            {
                "role": "user",
                "content": "Prefiero que hablemos siempre en español y de forma breve.",
            },
            {"role": "assistant", "content": "Entendido, responderé en español y de manera concisa."},
        ],
        "query": "What are the user's language and conversation preferences?",
        "must_contain": ["español", "spanish", "breve", "brief", "concise", "short"],
    },
    "M5": {
        "name": "Historial emocional",
        "store_messages": [
            {
                "role": "user",
                "content": "Últimamente me siento ansioso por los exámenes finales de la universidad.",
            },
            {"role": "assistant", "content": "Es comprensible sentir ansiedad en época de exámenes."},
        ],
        "query": "What is the user's recent emotional history?",
        "must_contain": ["ansio", "anxious", "exam", "examen"],
    },
}

MEMORY_TEST_USER_PREFIX = "VALID_M"
