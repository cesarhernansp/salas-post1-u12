"""grover.py -- Algoritmo de Grover para n = 2 qubits (espacio de 4 elementos).

Busca el estado marcado (`target`) en una "base de datos" no estructurada con
aceleracion cuadratica. Para N = 4 el numero optimo de iteraciones es 1 y el
estado marcado se obtiene con probabilidad 1 en el simulador ideal.

Circuito (una iteracion):
    1. superposicion uniforme: H en todos los qubits
    2. oraculo de fase: invierte el signo (fase -1) del estado marcado
    3. difusor: inversion alrededor de la media, que amplifica el estado marcado

Convencion de Qiskit (little-endian): en la cadena de bits "q1q0" el caracter de
la DERECHA es el qubit 0. El oraculo respeta esa convencion; sin ella, los
objetivos "01" y "10" quedarian intercambiados.

Uso (desde la raiz del repositorio):
    python src/grover.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CAPTURAS = Path(__file__).resolve().parent.parent / "capturas"
OBJETIVOS = ["00", "01", "10", "11"]


def append_phase_oracle(qc, target):
    """Oraculo de fase: aplica fase -1 solo al estado `target` (cadena "q1q0").

    CZ invierte la fase de |11>. Para marcar otro estado se aplica X a los qubits
    cuyo bit objetivo es 0 antes y despues del CZ. El bit del qubit i es
    target[-1 - i] porque Qiskit ordena las cadenas con el qubit 0 a la derecha.
    """
    ceros = [i for i in range(2) if target[-1 - i] == "0"]
    if ceros:
        qc.x(ceros)
    qc.cz(0, 1)
    if ceros:
        qc.x(ceros)


def append_diffuser(qc):
    """Difusor (inversion alrededor de la media): H X CZ X H en todos los qubits."""
    qc.h([0, 1])
    qc.x([0, 1])
    qc.cz(0, 1)
    qc.x([0, 1])
    qc.h([0, 1])


def build_grover_circuit(target="11", measure=True):
    """Construye el circuito de Grover de 2 qubits con 1 iteracion."""
    if target not in OBJETIVOS:
        raise ValueError(f"target debe ser uno de {OBJETIVOS}")
    qc = QuantumCircuit(2, 2)
    qc.h([0, 1])                     # paso 1: superposicion uniforme
    append_phase_oracle(qc, target)  # paso 2: oraculo de fase
    append_diffuser(qc)              # paso 3: difusor
    if measure:
        qc.measure([0, 1], [0, 1])
    return qc


def grover_2qubits(target="11", shots=1024):
    """Ejecuta Grover buscando `target` y guarda el histograma en capturas/."""
    qc = build_grover_circuit(target)
    counts = AerSimulator().run(qc, shots=shots).result().get_counts()

    print(f"Grover buscando |{target}> ({shots} shots):")
    for state, count in sorted(counts.items()):
        print(f"  |{state}>: {count:4d} ({count / shots * 100:.1f}%)")

    top = max(counts, key=counts.get)
    resultado = "CORRECTO" if top == target else "ERROR"
    print(f"Estado mas probable: |{top}> -- {resultado}")

    CAPTURAS.mkdir(exist_ok=True)
    fig = plot_histogram(counts, title=f"Grover 2 qubits: objetivo |{target}>")
    fig.savefig(CAPTURAS / f"grover_{target}.png", dpi=150)
    return counts


if __name__ == "__main__":
    print("Circuito (objetivo |11>):")
    print(build_grover_circuit("11").draw(output="text"))
    print()
    for t in OBJETIVOS:
        c = grover_2qubits(target=t)
        assert max(c, key=c.get) == t and c.get(t, 0) / 1024 > 0.9, f"Grover fallo para |{t}>"
        print()
    print("OK: Grover encuentra los 4 objetivos con probabilidad > 90 %")
