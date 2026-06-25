"""
Genera matriz de confusión de ejemplo para documentación de tesis.
Incluye datos ilustrativos; reemplazar con tests/analyze_emotions.py tras pruebas reales.
"""
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "logs" / "validation" / "confusion_matrix_emotions.png"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# Filas = esperado, Columnas = detectado (datos ilustrativos para documentación)
labels_es = ["Alegría", "Tristeza", "Ansiedad", "Sorpresa", "Calma"]
labels_en = ["joy", "sadness", "anxiety", "surprise", "calmness"]
detected_cols = ["Alegría", "Tristeza", "Ansiedad", "Sorpresa", "Calma", "Entusiasmo", "Neutral"]

# Matriz ejemplo documentación (5 escenarios, 4 aciertos estrictos + 1 confusión típica)
matrix = np.array([
    [1, 0, 0, 0, 0, 0, 0],   # E1 Alegría -> joy
    [0, 1, 0, 0, 0, 0, 0],   # E2 Tristeza -> sadness
    [0, 0, 1, 0, 0, 0, 0],   # E3 Ansiedad -> anxiety
    [0, 0, 0, 0, 0, 1, 0],   # E4 Sorpresa -> enthusiasm (confusión)
    [0, 0, 0, 0, 1, 0, 0],   # E5 Calma -> calmness
])

fig, ax = plt.subplots(figsize=(11, 8))
im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(1, matrix.max()))

ax.set_xticks(range(len(detected_cols)))
ax.set_yticks(range(len(labels_es)))
ax.set_xticklabels(detected_cols, rotation=35, ha="right")
ax.set_yticklabels(labels_es)
ax.set_xlabel("Emoción detectada (Hume EVI)", fontsize=11)
ax.set_ylabel("Emoción esperada (escenario simulado)", fontsize=11)
ax.set_title("Matriz de confusión — Validación emocional Louie", fontsize=12)

for i in range(matrix.shape[0]):
    for j in range(matrix.shape[1]):
        val = int(matrix[i, j])
        if val > 0:
            color = "white" if val >= 1 else "black"
            ax.text(j, i, str(val), ha="center", va="center", color=color, fontsize=12, fontweight="bold")

plt.colorbar(im, ax=ax, label="Nº escenarios")
plt.tight_layout()
plt.savefig(OUTPUT, dpi=150, bbox_inches="tight")
plt.close()
print(f"Imagen guardada: {OUTPUT}")
