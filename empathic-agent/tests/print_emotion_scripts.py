"""Imprime guiones para pruebas de voz E1–E5."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tests.scenarios import EMOTION_SCENARIOS

print("\n" + "=" * 70)
print("  GUIONES — Tabla 5: Escenarios de validación emocional")
print("  Inicia sesión en http://localhost:8000 con el User ID indicado.")
print("  Lee el guion en voz alta con tono emocional natural. Luego Stop Session.")
print("=" * 70 + "\n")

for sid, s in EMOTION_SCENARIOS.items():
    print(f"--- {sid}: {s['expected_es']} (user_id: {s['user_id']}) ---")
    print(s["script"])
    print()

print("Después ejecuta: .venv\\Scripts\\python.exe tests/analyze_emotions.py\n")
