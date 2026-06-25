"""
Analiza escenarios E1–E5 y genera matriz de confusión.
Lee sesiones con user_id VALID_E1 … VALID_E5 en logs/.

Ejecutar después de las pruebas de voz:
    .venv\\Scripts\\python.exe tests/analyze_emotions.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.scenarios import EMOTION_MATCH_ALIASES, EMOTION_SCENARIOS

LOGS_DIR = ROOT / "logs"
OUTPUT_DIR = LOGS_DIR / "validation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

LABELS_ES = {
    "joy": "Alegría",
    "sadness": "Tristeza",
    "anxiety": "Ansiedad",
    "surprise": "Sorpresa",
    "calmness": "Calma",
    "neutral": "Neutral",
    "enthusiasm": "Entusiasmo",
    "distress": "Angustia",
    "other": "Otra",
}


def _matches(expected: str, detected: str) -> bool:
    if detected == expected:
        return True
    aliases = EMOTION_MATCH_ALIASES.get(expected, set())
    return detected in aliases


def _load_session_emotions(user_id: str) -> tuple[str, float, list[tuple[str, float]]]:
    """Returns (dominant_emotion, max_score, per_turn list)."""
    summary_path = LOGS_DIR / "summary_all_sessions.csv"
    session_id = None
    dominant = "neutral"

    if summary_path.exists():
        with open(summary_path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("user_id") == user_id:
                    session_id = row.get("session_id")
                    dominant = row.get("dominant_emotion", "neutral")

    turns: list[tuple[str, float]] = []
    if session_id:
        session_file = LOGS_DIR / f"session_{session_id}.csv"
        if session_file.exists():
            with open(session_file, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    em = row.get("emotion_primary", "neutral")
                    sc = float(row.get("emotion_score") or 0)
                    if em and sc > 0:
                        turns.append((em, sc))

    if turns:
        best = max(turns, key=lambda x: x[1])
        return best[0], best[1], turns

    return dominant, 0.0, turns


def collect_results() -> list[dict]:
    rows = []
    for sid, scenario in EMOTION_SCENARIOS.items():
        detected, score, turns = _load_session_emotions(scenario["user_id"])
        expected = scenario["expected_emotion"]
        strict_match = detected == expected
        relaxed_match = _matches(expected, detected)

        rows.append({
            "scenario": sid,
            "expected_es": scenario["expected_es"],
            "expected": expected,
            "detected": detected,
            "score": round(score, 4),
            "turns_with_data": len(turns),
            "strict_match": strict_match,
            "relaxed_match": relaxed_match,
            "user_id": scenario["user_id"],
        })
    return rows


def print_table(rows: list[dict]) -> None:
    print("\n=== Tabla 5 — Validación emocional (Hume EVI) ===\n")
    print(f"{'Esc.':<6} {'Esperada':<12} {'Detectada':<12} {'Score':<8} {'Estricto':<10} {'Relajado'}")
    print("-" * 62)
    for r in rows:
        print(
            f"{r['scenario']:<6} {r['expected_es']:<12} {r['detected']:<12} "
            f"{r['score']:<8.4f} {'Sí' if r['strict_match'] else 'No':<10} "
            f"{'Sí' if r['relaxed_match'] else 'No'}"
        )

    strict = sum(1 for r in rows if r["strict_match"] and r["turns_with_data"] > 0)
    relaxed = sum(1 for r in rows if r["relaxed_match"] and r["turns_with_data"] > 0)
    with_data = sum(1 for r in rows if r["turns_with_data"] > 0)
    n = len(rows)

    print("-" * 62)
    if with_data == 0:
        print("Sin datos de sesión VALID_E*. Ejecuta las pruebas de voz primero.")
    else:
        print(f"Coincidencia estricta:  {strict}/{with_data} ({100*strict/with_data:.1f}%)")
        print(f"Coincidencia relajada: {relaxed}/{with_data} ({100*relaxed/with_data:.1f}%)")


def generate_confusion_matrix(rows: list[dict], out_path: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("Instala matplotlib: .venv\\Scripts\\pip.exe install matplotlib")
        return

    expected_labels = [s["expected_emotion"] for s in EMOTION_SCENARIOS.values()]
    all_detected = {r["detected"] for r in rows if r["turns_with_data"] > 0}
    detected_labels = sorted(all_detected | set(expected_labels))

    idx_exp = {e: i for i, e in enumerate(expected_labels)}
    idx_det = {d: i for i, d in enumerate(detected_labels)}

    matrix = np.zeros((len(expected_labels), len(detected_labels)), dtype=int)
    for r in rows:
        if r["turns_with_data"] == 0:
            continue
        i = idx_exp[r["expected"]]
        j = idx_det.get(r["detected"], idx_det.get("other", 0))
        matrix[i, j] += 1

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(matrix, cmap="Blues")

    ax.set_xticks(range(len(detected_labels)))
    ax.set_yticks(range(len(expected_labels)))
    ax.set_xticklabels([LABELS_ES.get(d, d) for d in detected_labels], rotation=45, ha="right")
    ax.set_yticklabels([LABELS_ES.get(e, e) for e in expected_labels])
    ax.set_xlabel("Emoción detectada (Hume EVI)", fontsize=11)
    ax.set_ylabel("Emoción esperada (escenario)", fontsize=11)
    ax.set_title("Matriz de confusión — Validación emocional Louie", fontsize=13)

    for i in range(len(expected_labels)):
        for j in range(len(detected_labels)):
            val = int(matrix[i, j])
            if val > 0:
                ax.text(j, i, str(val), ha="center", va="center", color="white" if val > 0 else "black")

    plt.colorbar(im, ax=ax, label="Nº de escenarios")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nMatriz de confusión guardada: {out_path}")


def write_csv(rows: list[dict]) -> Path:
    out = OUTPUT_DIR / "emotion_validation_results.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return out


def main() -> None:
    rows = collect_results()
    print_table(rows)
    csv_path = write_csv(rows)
    print(f"Resultados CSV: {csv_path}")

    matrix_path = OUTPUT_DIR / "confusion_matrix_emotions.png"
    generate_confusion_matrix(rows, matrix_path)

    missing = [r["scenario"] for r in rows if r["turns_with_data"] == 0]
    if missing:
        print(f"\nPendientes (sin sesión): {', '.join(missing)}")
        print("Usa los user_id VALID_E1 … VALID_E5 al iniciar sesión en el navegador.")


if __name__ == "__main__":
    main()
