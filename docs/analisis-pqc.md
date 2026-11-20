# Impacto de la computación cuántica en la ciberseguridad y migración a criptografía post-cuántica

**Autor:** César Hernán Salas Peñaranda  
**Curso:** Arquitectura de Computadores — Unidad 12, Parte 2  
**Fecha de consulta de las fuentes:** 20 de noviembre de 2026

## Introducción

Un computador cuántico criptográficamente relevante (CRQC, por sus siglas en inglés) tendría capacidad para romper los sistemas de clave pública que protegen hoy las comunicaciones, las firmas digitales y la infraestructura de claves (CISA, NSA y NIST, 2023). Este documento analiza ese impacto en cinco pasos: el inventario de algoritmos criptográficos clasificados según su vulnerabilidad al algoritmo de Shor o al de Grover; los tres estándares post-cuánticos que el NIST publicó el 13 de agosto de 2024 (ML-KEM, ML-DSA y SLH-DSA); un plan de migración para tres perfiles de organización con horizontes de sensibilidad de datos muy distintos; la cuantificación del crecimiento en bytes de las claves y firmas post-cuánticas y su efecto en un *handshake* TLS 1.3 híbrido; y dos decisiones técnicas justificadas.

**Criterio de fuentes.** Cada cifra técnica proviene de los documentos primarios que se leyeron para este análisis: los tres FIPS del NIST (FIPS 203, 204 y 205), el informe NIST IR 8547 en su versión final de octubre de 2026, el *factsheet* de CISA, NSA y NIST de 2023 y el RFC 10024 del IETF. Las tablas de tamaños y de parámetros se transcribieron de las tablas oficiales de los FIPS. Donde una afirmación no pudo verificarse en una fuente primaria, el documento lo indica de forma expresa.

**Diferencias respecto a la guía.** La revisión de las fuentes mostró tres puntos que conviene aclarar desde el principio:

- El NIST IR 8547 ya no es un borrador: se publicó en su versión final el 27 de octubre de 2026, y la guía lo conoce solo por el borrador de noviembre de 2024. Los plazos de transición se citan de la versión final.
- El esquema de TLS híbrido X25519+ML-KEM-768 ya está estandarizado como **RFC 10024** (Proposed Standard, agosto de 2026), con el nombre de grupo `X25519MLKEM768` (valor IANA 4588); la guía lo menciona como `X25519Kyber768` en despliegue desde 2023-2024.
- El documento "ETSI GR QSC 006" que lista la guía como "Transition Guidelines" no pudo localizarse con ese título, por lo que no se cita.

## 1. Inventario de algoritmos criptográficos vulnerables

El primer paso de cualquier migración post-cuántica es un inventario completo de los algoritmos en uso (CISA, NSA y NIST, 2023). Para clasificarlos conviene separar dos amenazas distintas.

- **Algoritmo de Shor.** Factoriza enteros y calcula logaritmos discretos en tiempo polinómico en un computador cuántico (Shor, 1997). Rompe de forma completa todo lo que se apoya en la factorización (RSA) o en el logaritmo discreto, sea en cuerpos finitos (Diffie-Hellman) o en curvas elípticas (ECDH, X25519, ECDSA, EdDSA). No existe un aumento razonable del tamaño de clave que lo contrarreste.
- **Algoritmo de Grover.** Acelera de forma cuadrática la búsqueda en un espacio no estructurado (Grover, 1996): una búsqueda exhaustiva de 2ⁿ claves pasa a costar del orden de 2^(n/2) operaciones. Afecta a la criptografía simétrica y a las funciones hash, pero no las rompe; basta con aumentar el tamaño de clave o la longitud de salida.

### 1.1 Tabla de vulnerabilidad

| Algoritmo | Tipo | Vulnerabilidad cuántica | Algoritmo atacante | Estado post-cuántico y acción recomendada |
|---|---|---|---|---|
| RSA-2048, RSA-3072, RSA-4096 | Cifrado y firma asimétricos | **Roto completamente** | Shor (factorización) | Reemplazar por ML-KEM (cifrado/encapsulación) y por ML-DSA o SLH-DSA (firma) |
| ECDSA (P-256, P-384) | Firma digital | **Roto completamente** | Shor (logaritmo discreto en curvas elípticas) | Reemplazar por ML-DSA (o SLH-DSA como respaldo) |
| ECDH / X25519 | Intercambio de clave | **Roto completamente** | Shor (logaritmo discreto en curvas elípticas) | Reemplazar por ML-KEM; en transición, usar el modo híbrido X25519+ML-KEM-768 |
| DH de campo finito | Intercambio de clave | **Roto completamente** | Shor (logaritmo discreto) | Reemplazar por ML-KEM |
| AES-128 | Cifrado simétrico | **Debilitado**: clave efectiva de 64 bits frente a Grover | Grover, O(√N) | Migrar a AES-256; el NIST lo mantiene en la categoría de seguridad 1 (NIST, 2026) |
| AES-256 | Cifrado simétrico | **Aceptable**: clave efectiva de 128 bits | Grover, O(√N) | Mantener |
| SHA-256 | Función hash | **Debilitada** en preimagen (de 2²⁵⁶ a 2¹²⁸ con Grover); la búsqueda de colisiones en un hash de 256 bits es la referencia de la categoría 2 del NIST | Grover | Mantener con precaución; para nuevos sistemas, SHA-384 o SHA-512 |
| SHA-3-256 | Función hash | **Debilitada**, equivalente a SHA-256 | Grover | Usar SHA3-384 o superior |

La clasificación distingue dos grados. "**Roto completamente**" significa que un CRQC permite recuperar claves privadas y, por tanto, **descifrar de forma retroactiva** el tráfico que se capturó con anterioridad y falsificar firmas. "**Debilitado**" significa que la seguridad efectiva baja, pero sigue siendo suficiente con parámetros mayores: duplicar la longitud de la clave simétrica devuelve el nivel de seguridad original.

El NIST usa cinco categorías de seguridad definidas por la dificultad de ataques de referencia: la categoría 1 equivale a la búsqueda de una clave de un cifrador de bloque de 128 bits (AES-128), la 2 a una búsqueda de colisiones en una función hash de 256 bits (SHA-256), la 3 a una clave de 192 bits (AES-192), la 4 a colisiones en un hash de 384 bits (SHA3-384) y la 5 a una clave de 256 bits (AES-256) (NIST, 2026). Estas categorías son la escala que se usa más adelante para comparar ML-KEM, ML-DSA y SLH-DSA.

### 1.2 Plazos del NIST para los algoritmos de clave pública

El NIST IR 8547, en su versión final de octubre de 2026, fija el calendario de abandono de los algoritmos cuánticamente vulnerables (NIST, 2026): **RSA, ECDSA, EdDSA y los esquemas de intercambio de clave Diffie-Hellman (DH y ECDH) quedan en desuso ("deprecated") después de 2030 y prohibidos ("disallowed") después de 2035** en los estándares y guías del NIST. La ventana de 2030 a 2035 atiende los sistemas de menor riesgo con restricciones heredadas; no altera los plazos anteriores para los activos de alto valor del gobierno federal de Estados Unidos, que según la Orden Ejecutiva 14412 y el memorando OMB M-26-15 deben adoptar criptografía post-cuántica para el establecimiento de claves antes del 31 de diciembre de 2030 y para las firmas digitales antes del 31 de diciembre de 2031 (NIST, 2026). El memorando NSM-10 ya había fijado 2035 como objetivo para completar la migración federal.

### 1.3 Por qué la amenaza es de "recolectar ahora, descifrar después"

Un adversario puede interceptar hoy comunicaciones cifradas con RSA, ECDH o X25519 y guardarlas hasta contar con un CRQC: es la amenaza de *harvest now, decrypt later* (HNDL), que CISA, NSA y NIST citan como razón principal para empezar a migrar sin esperar a que exista la máquina (CISA, NSA y NIST, 2023). La amenaza HNDL afecta a la **confidencialidad** de datos con una vida útil larga; no afecta del mismo modo a una firma, cuya validez se comprueba en el momento de la emisión.

El tamaño de la máquina necesaria baja con el tiempo. Gidney y Ekerå (2021) estimaron que factorizar un entero RSA de 2048 bits requería unos 20 millones de qubits ruidosos y unas 8 horas; Gidney (2025) lo redujo a menos de un millón de qubits ruidosos y menos de una semana, con una tasa de error de puerta de 0,1 %, un ciclo del código de superficie de 1 µs y un tiempo de reacción del control de 10 µs. Ninguna de las dos máquinas existe hoy; lo relevante es la tendencia, que acorta el plazo de seguridad de los datos con horizonte largo.

**Checkpoint 1.** El inventario incluye ocho algoritmos clasificados, distingue los vulnerables a Shor (asimétricos) de los vulnerables a Grover (simétricos y hash), indica la acción de remediación y diferencia "roto completamente" (compromiso retroactivo de la confidencialidad) de "debilitado".
