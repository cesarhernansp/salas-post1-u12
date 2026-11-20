"""grover_noise.py -- Grover de 2 qubits bajo un modelo de ruido despolarizante.

Los experimentos anteriores usan un simulador ideal. Un procesador cuantico NISQ
real introduce un error medible en cada puerta. Aqui se inyecta ese error dentro
del propio simulador con `qiskit_aer.noise.NoiseModel`: un error despolarizante
en cada puerta de 1 qubit (h, x) y de 2 qubits (cz), con tasas del orden de las
publicadas para procesadores superconductores (~0.1 % y ~1 %).

Ademas de la comparacion con y sin ruido pedida en el enunciado, el programa
mide tres cosas que sirven para interpretarla:
    - la variabilidad estadistica de la probabilidad de exito (varias corridas),
    - como cae la probabilidad de exito al aumentar la tasa de error, y
    - como se acumula el error con la profundidad del circuito (numero de CZ).

Uso (desde la raiz del repositorio):
    python src/grover_noise.py
"""
import statistics
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error

from grover import build_grover_circuit  # mismo circuito del Paso 3

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CAPTURAS = Path(__file__).resolve().parent.parent / "capturas"
SEMILLA = 2026  # semilla del simulador: hace reproducibles los numeros del README


def build_noise_model(p1q=0.001, p2q=0.01):
    """Modelo de ruido despolarizante: p1q por puerta de 1 qubit (h, x) y p2q por
    puerta de 2 qubits (cz). Son ordenes de magnitud tipicos del hardware NISQ
    superconductor publicados en la documentacion de IBM Quantum.

    En Qiskit, depolarizing_error(p, n) reemplaza el estado por el estado
    maximamente mezclado con probabilidad p.
    """
    noise_model = NoiseModel()
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p1q, 1), ["h", "x"])
    noise_model.add_all_qubit_quantum_error(depolarizing_error(p2q, 2), ["cz"])
    return noise_model


def run_counts(qc, noise_model=None, shots=1024, seed=SEMILLA):
    """Ejecuta `qc` en AerSimulator (con o sin ruido) y devuelve los conteos."""
    sim = AerSimulator(noise_model=noise_model) if noise_model else AerSimulator()
    return sim.run(qc, shots=shots, seed_simulator=seed).result().get_counts()


def grover_noise_experiment(target="11", shots=1024):
    """Compara la probabilidad de exito de Grover sin ruido y con ruido."""
    qc = build_grover_circuit(target)

    counts_ideal = run_counts(qc, shots=shots)                         # linea base
    counts_noisy = run_counts(qc, build_noise_model(), shots=shots)    # con ruido

    p_ideal = counts_ideal.get(target, 0) / shots
    p_noisy = counts_noisy.get(target, 0) / shots

    print(f"Grover |{target}> sin ruido: {p_ideal * 100:.1f}%")
    print(f"Grover |{target}> con ruido: {p_noisy * 100:.1f}%")
    print(f"Degradacion: {(p_ideal - p_noisy) * 100:.1f} puntos porcentuales")
    print("Conteos con ruido:", dict(sorted(counts_noisy.items())))

    CAPTURAS.mkdir(exist_ok=True)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    plot_histogram(counts_ideal, ax=axs[0])
    plot_histogram(counts_noisy, ax=axs[1])
    axs[0].set_title("Sin ruido")
    axs[1].set_title("Con ruido (despolarizante)")
    fig.tight_layout()
    fig.savefig(CAPTURAS / "grover_noise_comparison.png", dpi=150)
    plt.close(fig)
    return p_ideal, p_noisy, counts_noisy


def estadistica_ruido(target="11", shots=1024, repeticiones=30):
    """Repite el experimento con semillas distintas: media y desviacion tipica."""
    qc = build_grover_circuit(target)
    ruido = build_noise_model()
    probs = [run_counts(qc, ruido, shots, seed=SEMILLA + k).get(target, 0) / shots
             for k in range(repeticiones)]
    return statistics.mean(probs), statistics.stdev(probs)


def barrido_ruido(target="11", shots=8192):
    """Probabilidad de exito de Grover al escalar las tasas de error (p1q = p2q / 10)."""
    qc = build_grover_circuit(target)
    p2q_valores = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.10]
    exitos = []
    for p2q in p2q_valores:
        c = run_counts(qc, build_noise_model(p1q=p2q / 10, p2q=p2q), shots)
        exitos.append(c.get(target, 0) / shots)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot([p * 100 for p in p2q_valores], [e * 100 for e in exitos], "o-")
    ax.axhline(25, color="gray", linestyle="--", label="azar (25 %)")
    ax.axvline(1, color="red", linestyle=":", label="p2q = 1 % (guia)")
    ax.set_xlabel("error por puerta de 2 qubits (%)  [p1q = p2q / 10]")
    ax.set_ylabel(f"probabilidad de exito de |{target}> (%)")
    ax.set_title("Grover 2 qubits: exito frente a la tasa de error")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CAPTURAS / "grover_noise_barrido.png", dpi=150)
    plt.close(fig)
    return list(zip(p2q_valores, exitos))


def profundidad_vs_exito(p2q=0.01, shots=8192):
    """Acumulacion del error con la profundidad: m puertas CZ seguidas sobre |00>.

    Un numero PAR de CZ es la identidad, asi que sin ruido el estado vuelve a |00>
    con probabilidad 1. Con ruido, la probabilidad de medir |00> mide cuanta senal
    sobrevive tras m puertas de 2 qubits.
    """
    ruido = build_noise_model(p2q=p2q)
    profundidades = [0, 2, 10, 20, 50, 100, 200, 400]
    medidas = []
    for m in profundidades:
        qc = QuantumCircuit(2, 2)
        for _ in range(m):
            qc.cz(0, 1)
        qc.measure([0, 1], [0, 1])
        medidas.append(run_counts(qc, ruido, shots).get("00", 0) / shots)

    # Modelo: con probabilidad p2q cada CZ mezcla el estado por completo; el estado
    # sigue intacto con probabilidad (1 - p2q)^m y, si no, queda con 1/4 en |00>
    teoria = [(1 - p2q) ** m + (1 - (1 - p2q) ** m) / 4 for m in profundidades]

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(profundidades, [x * 100 for x in medidas], "o", label="simulacion con ruido")
    ax.plot(profundidades, [x * 100 for x in teoria], "-", label="modelo (1-p)^m + (1-(1-p)^m)/4")
    ax.axhline(25, color="gray", linestyle="--", label="azar (25 %)")
    ax.set_xlabel("numero de puertas CZ (profundidad)")
    ax.set_ylabel("probabilidad de medir |00> (%)")
    ax.set_title(f"Acumulacion del error (p2q = {p2q * 100:.0f} %)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(CAPTURAS / "grover_noise_profundidad.png", dpi=150)
    plt.close(fig)
    return list(zip(profundidades, medidas, teoria))


if __name__ == "__main__":
    print("=== Comparacion con y sin ruido (p1q = 0.1 %, p2q = 1 %) ===")
    p_ideal, p_noisy, counts_noisy = grover_noise_experiment()

    media, desv = estadistica_ruido()
    print(f"\n30 corridas de 1024 shots con ruido: media {media * 100:.1f}% "
          f"(desv. tipica {desv * 100:.1f} puntos)")

    print("\n=== Barrido de la tasa de error (p1q = p2q / 10) ===")
    for p2q, exito in barrido_ruido():
        print(f"  p2q = {p2q * 100:5.1f}%  ->  exito de |11> = {exito * 100:5.1f}%")

    print("\n=== Acumulacion del error con la profundidad (p2q = 1 %) ===")
    print("  CZ seguidas | P(00) simulada | P(00) segun el modelo")
    for m, medida, teoria in profundidad_vs_exito():
        print(f"  {m:11d} | {medida * 100:13.1f}% | {teoria * 100:20.1f}%")
