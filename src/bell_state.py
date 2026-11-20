"""bell_state.py -- Estado de Bell |Phi+> y verificacion de la correlacion cuantica.

El estado de Bell |Phi+> = (|00> + |11>) / sqrt(2) es el estado entrelazado mas
simple de dos qubits. Se prepara con una puerta Hadamard en el qubit 0 (crea la
superposicion) seguida de una CNOT con el qubit 0 como control (entrelaza).

Uso (desde la raiz del repositorio):
    python src/bell_state.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin ventana: el histograma solo se guarda en disco
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector, state_fidelity
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CAPTURAS = Path(__file__).resolve().parent.parent / "capturas"


def build_bell_circuit(measure=True):
    """Construye el circuito de Bell: H en el qubit 0 y CNOT (control 0, objetivo 1)."""
    qc = QuantumCircuit(2, 2)  # 2 qubits y 2 bits clasicos
    qc.h(0)       # paso 1: Hadamard -> superposicion en el qubit 0
    qc.cx(0, 1)   # paso 2: CNOT -> entrelazamiento de los dos qubits
    if measure:
        qc.measure([0, 1], [0, 1])  # paso 3: medir ambos qubits
    return qc


def verify_ideal_state():
    """Compara el vector de estado del circuito sin medir con |Phi+> teorico."""
    ideal = Statevector.from_instruction(build_bell_circuit(measure=False))
    expected = Statevector([1 / 2**0.5, 0, 0, 1 / 2**0.5])  # (|00> + |11>)/sqrt(2)
    return state_fidelity(ideal, expected)


def bell_state_experiment(shots=1024):
    """Prepara el estado de Bell, lo mide `shots` veces y verifica la correlacion."""
    qc = build_bell_circuit()

    simulator = AerSimulator()
    counts = simulator.run(qc, shots=shots).result().get_counts()

    print(f"Resultados Bell |Phi+> ({shots} shots):")
    for state, count in sorted(counts.items()):
        pct = count / shots * 100
        print(f"  |{state}> : {count:4d} ({pct:.1f}%)")

    # Solo deben aparecer |00> y |11>: la correlacion es perfecta
    assert "01" not in counts and "10" not in counts, \
        "ERROR: aparecieron estados no entrelazados"
    print("OK: correlacion perfecta verificada (nunca |01> ni |10>)")
    print(f"Fidelidad del estado ideal con |Phi+> teorico: {verify_ideal_state():.4f}")

    CAPTURAS.mkdir(exist_ok=True)
    fig = plot_histogram(counts, title="Estado de Bell |Phi+> (1024 shots)")
    fig.savefig(CAPTURAS / "bell_histogram.png", dpi=150)
    print(f"Histograma guardado en {CAPTURAS / 'bell_histogram.png'}")

    print("Diagrama del circuito:")
    print(qc.draw(output="text"))
    return counts


if __name__ == "__main__":
    bell_state_experiment()
