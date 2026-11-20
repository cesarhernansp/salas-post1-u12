"""deutsch_jozsa.py -- Algoritmo de Deutsch-Jozsa para n = 2 qubits de entrada.

Decide si una funcion f: {0,1}^n -> {0,1} es constante (da el mismo valor para
todas las entradas) o balanceada (da 0 para exactamente la mitad de las entradas
y 1 para la otra mitad) con UNA sola evaluacion del oraculo. Un algoritmo
clasico determinista necesita, en el peor caso, 2^(n-1) + 1 evaluaciones.

Lectura del resultado (determinista):
    - todas las mediciones de los n qubits de entrada son 0  -> f es constante
    - alguna medicion es 1                                  -> f es balanceada

Uso (desde la raiz del repositorio):
    python src/deutsch_jozsa.py
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from qiskit import QuantumCircuit
from qiskit.visualization import plot_histogram
from qiskit_aer import AerSimulator

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

CAPTURAS = Path(__file__).resolve().parent.parent / "capturas"


def oracle_constante(n):
    """Oraculo constante f(x) = 0: no hace nada (el ancilla ya esta incluido)."""
    return QuantumCircuit(n + 1)


def oracle_constante_uno(n):
    """Oraculo constante f(x) = 1: invierte el ancilla para toda entrada."""
    qc = QuantumCircuit(n + 1)
    qc.x(n)
    return qc


def oracle_balanceada(n):
    """Oraculo balanceado f(x) = x_0 XOR ... XOR x_(n-1): CNOT de cada qubit i al ancilla."""
    qc = QuantumCircuit(n + 1)
    for i in range(n):
        qc.cx(i, n)  # CNOT qubit_i -> ancilla
    return qc


def oracle_balanceada_un_bit(n, bit=0):
    """Oraculo balanceado f(x) = x_bit: una sola CNOT desde el qubit `bit`."""
    qc = QuantumCircuit(n + 1)
    qc.cx(bit, n)
    return qc


def build_dj_circuit(oracle_qc, n):
    """Construye el circuito completo de Deutsch-Jozsa con el oraculo dado."""
    qc = QuantumCircuit(n + 1, n)

    # Inicializar el ancilla en |-> = H|1>
    qc.x(n)
    qc.h(range(n + 1))  # H en todos los qubits: superposicion uniforme de entradas

    # Una unica llamada al oraculo
    qc.compose(oracle_qc, inplace=True)

    # Interferencia: H en los qubits de entrada
    qc.h(range(n))

    # Medir solo los qubits de entrada (no el ancilla)
    qc.measure(range(n), range(n))
    return qc


def deutsch_jozsa(oracle_qc, n, shots=1024):
    """Ejecuta el algoritmo con el oraculo dado y devuelve los conteos."""
    qc = build_dj_circuit(oracle_qc, n)
    return AerSimulator().run(qc, shots=shots).result().get_counts()


def classify(counts, n):
    """Interpreta el resultado: constante si solo aparece 0...0, balanceada si no."""
    return "constante" if set(counts) == {"0" * n} else "balanceada"


def save_histograms(counts_c, counts_b):
    """Guarda en capturas/ los histogramas de los dos oraculos del enunciado."""
    CAPTURAS.mkdir(exist_ok=True)
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    plot_histogram(counts_c, ax=axs[0])
    plot_histogram(counts_b, ax=axs[1])
    axs[0].set_title("Oraculo constante f(x)=0")        # titulos explicitos: con ax=
    axs[1].set_title("Oraculo balanceado (paridad)")    # plot_histogram no siempre los dibuja
    fig.tight_layout()
    fig.savefig(CAPTURAS / "deutsch_jozsa.png", dpi=150)


if __name__ == "__main__":
    n = 2

    # Oraculo constante: todos los resultados deben ser "00"
    counts_c = deutsch_jozsa(oracle_constante(n), n)
    print(f"Constante:  {counts_c}")  # esperado: {"00": 1024}

    # Oraculo balanceado: ningun resultado debe ser "00"
    counts_b = deutsch_jozsa(oracle_balanceada(n), n)
    print(f"Balanceada: {counts_b}")  # esperado: sin "00"

    assert "00" in counts_c, "Error: oraculo constante no retorno 00"
    assert "00" not in counts_b, "Error: oraculo balanceado retorno 00"
    print("OK: Deutsch-Jozsa verifica correctamente")

    print("\nCircuito del oraculo balanceado (una sola evaluacion):")
    print(build_dj_circuit(oracle_balanceada(n), n).draw(output="text"))

    # Comprobacion adicional con otros oraculos (el resultado sigue siendo determinista)
    print("\nOtros oraculos de prueba:")
    otros = [
        ("constante f(x)=1", oracle_constante_uno(n)),
        ("balanceada f(x)=x0", oracle_balanceada_un_bit(n, 0)),
        ("balanceada f(x)=x1", oracle_balanceada_un_bit(n, 1)),
    ]
    for nombre, oraculo in otros:
        c = deutsch_jozsa(oraculo, n)
        print(f"  {nombre:20s} -> {c}  => {classify(c, n)}")

    save_histograms(counts_c, counts_b)
    print(f"\nHistogramas guardados en {CAPTURAS / 'deutsch_jozsa.png'}")
