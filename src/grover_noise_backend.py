"""grover_noise_backend.py -- Grover de 2 qubits con ruido calibrado de un backend IBM.

Auxiliar de la decision tecnica del Paso 6 (no es parte del enunciado). Compara
el modelo despolarizante simplificado de `grover_noise.py` con un modelo de ruido
CALIBRADO: `NoiseModel.from_backend()` sobre `FakeSherbrooke`, una copia local de
los datos de calibracion publicados por el procesador IBM Sherbrooke (127 qubits
superconductores). No requiere cuenta de IBM Quantum ni conexion: los datos de
calibracion vienen incluidos en `qiskit-ibm-runtime`.

El modelo calibrado incluye errores de puerta distintos por qubit y por par
acoplado, relajacion termica (T1, T2) y errores de lectura (readout).

Uso (desde la raiz del repositorio):
    python src/grover_noise_backend.py
"""
import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import transpile
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeSherbrooke

from grover import build_grover_circuit
from grover_noise import build_noise_model, run_counts

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=DeprecationWarning)

CAPTURAS = Path(__file__).resolve().parent.parent / "capturas"
TARGET = "11"
SHOTS = 8192
SEMILLA = 2026
PARES = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7), (7, 8)]  # pares acoplados


def datos_del_par(backend, a, b):
    """Parametros calibrados de los qubits a y b: T1, T2 (us), errores ECR y de lectura."""
    t = backend.target
    qa, qb = backend.qubit_properties(a), backend.qubit_properties(b)
    return {
        "t1_a": qa.t1 * 1e6, "t2_a": qa.t2 * 1e6,
        "t1_b": qb.t1 * 1e6, "t2_b": qb.t2 * 1e6,
        "ecr": t["ecr"][(a, b)].error if (a, b) in t["ecr"] else t["ecr"][(b, a)].error,
        "ro_a": t["measure"][(a,)].error, "ro_b": t["measure"][(b,)].error,
    }


def exito_calibrado(backend, noise_model, a, b):
    """Probabilidad de exito de Grover |11> sobre el par de qubits fisicos (a, b)."""
    qc = transpile(build_grover_circuit(TARGET), backend, initial_layout=[a, b],
                   optimization_level=0, seed_transpiler=SEMILLA)
    sim = AerSimulator(noise_model=noise_model, basis_gates=noise_model.basis_gates,
                       coupling_map=backend.coupling_map)
    counts = sim.run(qc, shots=SHOTS, seed_simulator=SEMILLA).result().get_counts()
    return counts.get(TARGET, 0) / SHOTS, qc


if __name__ == "__main__":
    backend = FakeSherbrooke()
    noise_model = NoiseModel.from_backend(backend)
    print(f"Backend: {backend.name} ({backend.num_qubits} qubits). "
          f"Puertas del modelo calibrado: {sorted(noise_model.basis_gates)}\n")

    # Referencia: el modelo despolarizante simplificado (sin transpilar al hardware)
    p_desp = run_counts(build_grover_circuit(TARGET), build_noise_model(), SHOTS).get(TARGET, 0) / SHOTS
    print(f"Modelo despolarizante simplificado (p1q=0.1%, p2q=1%): {p_desp * 100:.1f}%\n")

    print("Modelo calibrado (NoiseModel.from_backend) sobre pares de qubits acoplados:")
    print("  par    T1 (us)       T2 (us)       error ECR  readout   exito |11>")
    exitos = []
    for a, b in PARES:
        p, qc_hw = exito_calibrado(backend, noise_model, a, b)
        d = datos_del_par(backend, a, b)
        exitos.append(p)
        print(f"  ({a},{b})  {d['t1_a']:5.0f}/{d['t1_b']:5.0f}   {d['t2_a']:5.0f}/{d['t2_b']:5.0f}   "
              f"{d['ecr'] * 100:6.2f}%   {d['ro_a'] * 100:4.1f}/{d['ro_b'] * 100:4.1f}%   {p * 100:6.1f}%")

    media = sum(exitos) / len(exitos)
    print(f"\n  media {media * 100:.1f}%  |  minimo {min(exitos) * 100:.1f}%  |  maximo {max(exitos) * 100:.1f}%")
    print(f"\nCircuito transpilado a las puertas nativas del hardware (par {PARES[0]}):")
    puertas = qc_hw.count_ops()
    print("  ", dict(puertas), f"| profundidad {qc_hw.depth()}")

    fig, ax = plt.subplots(figsize=(8, 4))
    etiquetas = ["ideal", "despolarizante\n(simplificado)"] + [f"calibrado\n{a}-{b}" for a, b in PARES]
    valores = [100.0, p_desp * 100] + [e * 100 for e in exitos]
    colores = ["gray", "tab:blue"] + ["tab:orange"] * len(PARES)
    ax.bar(range(len(valores)), valores, color=colores)
    ax.set_xticks(range(len(valores)))
    ax.set_xticklabels(etiquetas, fontsize=7)
    ax.set_ylim(80, 101)
    ax.set_ylabel("probabilidad de exito de |11> (%)")
    ax.set_title("Grover 2 qubits: modelo simplificado frente a ruido calibrado (FakeSherbrooke)")
    fig.tight_layout()
    CAPTURAS.mkdir(exist_ok=True)
    fig.savefig(CAPTURAS / "grover_noise_backend.png", dpi=150)
    print(f"\nGrafico guardado en {CAPTURAS / 'grover_noise_backend.png'}")
