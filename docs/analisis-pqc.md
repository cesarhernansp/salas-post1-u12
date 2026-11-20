# Impacto de la computación cuántica en la ciberseguridad y migración a criptografía post-cuántica

**Autor:** César Hernán Salas Peñaranda  
**Curso:** Arquitectura de Computadores — Unidad 12, Parte 2  
**Fecha de consulta de las fuentes:** 20 de noviembre de 2026

## Introducción

Un computador cuántico criptográficamente relevante (CRQC, por sus siglas en inglés) tendría capacidad para romper los sistemas de clave pública que protegen hoy las comunicaciones, las firmas digitales y la infraestructura de claves (CISA, NSA y NIST, 2023). Este documento analiza ese impacto en cinco pasos: el inventario de algoritmos criptográficos clasificados según su vulnerabilidad al algoritmo de Shor o al de Grover; los tres estándares post-cuánticos que el NIST publicó el 13 de agosto de 2024 (ML-KEM, ML-DSA y SLH-DSA); un plan de migración para tres perfiles de organización con horizontes de sensibilidad de datos muy distintos; la cuantificación del crecimiento en bytes de las claves y firmas post-cuánticas y su efecto en un *handshake* TLS 1.3 híbrido; y dos decisiones técnicas justificadas.

**Criterio de fuentes.** Cada cifra técnica proviene de los documentos primarios que se leyeron para este análisis: los tres FIPS del NIST (FIPS 203, 204 y 205), el informe NIST IR 8547 en su versión final de octubre de 2026, el *factsheet* de CISA, NSA y NIST de 2023, el aviso de la NSA sobre CNSA 2.0 (versión 1.0, septiembre de 2022) y el RFC 10024 del IETF. Las tablas de tamaños y de parámetros se transcribieron de las tablas oficiales de los FIPS. Donde una afirmación no pudo verificarse en una fuente primaria, el documento lo indica de forma expresa.

**Diferencias respecto a la guía.** La revisión de las fuentes mostró tres puntos que conviene aclarar desde el principio:

- El NIST IR 8547 ya no es un borrador: se publicó en su versión final el 27 de octubre de 2026, y la guía lo conoce solo por el borrador de noviembre de 2024. Los plazos de transición se citan de la versión final.
- El esquema de TLS híbrido X25519+ML-KEM-768 ya está estandarizado como **RFC 10024** (*Standards Track*, agosto de 2026), con el nombre de grupo `X25519MLKEM768` (valor IANA 4588); la guía lo menciona como `X25519Kyber768` en despliegue desde 2023-2024.
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
| AES-128 | Cifrado simétrico | **Debilitado**: clave efectiva de 64 bits frente a Grover | Grover, O(√N) | Migrar a AES-256; el NIST lo mantiene en la categoría de seguridad 1 (Moody et al., 2026) |
| AES-256 | Cifrado simétrico | **Aceptable**: clave efectiva de 128 bits | Grover, O(√N) | Mantener |
| SHA-256 | Función hash | **Debilitada** en preimagen (de 2²⁵⁶ a 2¹²⁸ con Grover); la búsqueda de colisiones en un hash de 256 bits es la referencia de la categoría 2 del NIST | Grover | Mantener con precaución; para nuevos sistemas, SHA-384 o SHA-512 |
| SHA-3-256 | Función hash | **Debilitada**, equivalente a SHA-256 | Grover | Usar SHA3-384 o superior |

La clasificación distingue dos grados. "**Roto completamente**" significa que un CRQC permite recuperar claves privadas y, por tanto, **descifrar de forma retroactiva** el tráfico que se capturó con anterioridad y falsificar firmas. "**Debilitado**" significa que la seguridad efectiva baja, pero sigue siendo suficiente con parámetros mayores: duplicar la longitud de la clave simétrica devuelve el nivel de seguridad original.

El NIST usa cinco categorías de seguridad definidas por la dificultad de ataques de referencia: la categoría 1 equivale a la búsqueda de una clave de un cifrador de bloque de 128 bits (AES-128), la 2 a una búsqueda de colisiones en una función hash de 256 bits (SHA-256), la 3 a una clave de 192 bits (AES-192), la 4 a colisiones en un hash de 384 bits (SHA3-384) y la 5 a una clave de 256 bits (AES-256) (Moody et al., 2026). Estas categorías son la escala que se usa más adelante para comparar ML-KEM, ML-DSA y SLH-DSA.

### 1.2 Plazos del NIST para los algoritmos de clave pública

El NIST IR 8547, en su versión final de octubre de 2026, fija el calendario de abandono de los algoritmos cuánticamente vulnerables (Moody et al., 2026): **RSA, ECDSA, EdDSA y los esquemas de intercambio de clave Diffie-Hellman (DH y ECDH) quedan en desuso ("deprecated") después de 2030 y prohibidos ("disallowed") después de 2035** en los estándares y guías del NIST. La ventana de 2030 a 2035 atiende los sistemas de menor riesgo con restricciones heredadas; no altera los plazos anteriores para los activos de alto valor del gobierno federal de Estados Unidos, que según la Orden Ejecutiva 14412 y el memorando OMB M-26-15 deben adoptar criptografía post-cuántica para el establecimiento de claves antes del 31 de diciembre de 2030 y para las firmas digitales antes del 31 de diciembre de 2031 (Moody et al., 2026). El memorando NSM-10 ya había fijado 2035 como objetivo para completar la migración federal.

### 1.3 Por qué la amenaza es de "recolectar ahora, descifrar después"

Un adversario puede interceptar hoy comunicaciones cifradas con RSA, ECDH o X25519 y guardarlas hasta contar con un CRQC: es la amenaza de *harvest now, decrypt later* (HNDL), que CISA, NSA y NIST citan como razón principal para empezar a migrar sin esperar a que exista la máquina (CISA, NSA y NIST, 2023). La amenaza HNDL afecta a la **confidencialidad** de datos con una vida útil larga; no afecta del mismo modo a una firma, cuya validez se comprueba en el momento de la emisión.

El tamaño de la máquina necesaria baja con el tiempo. Gidney y Ekerå (2021) estimaron que factorizar un entero RSA de 2048 bits requería unos 20 millones de qubits ruidosos y unas 8 horas; Gidney (2025) lo redujo a menos de un millón de qubits ruidosos y menos de una semana, con una tasa de error de puerta de 0,1 %, un ciclo del código de superficie de 1 µs y un tiempo de reacción del control de 10 µs. Ninguna de las dos máquinas existe hoy; lo relevante es la tendencia, que acorta el plazo de seguridad de los datos con horizonte largo.

**Checkpoint 1.** El inventario incluye ocho algoritmos clasificados, distingue los vulnerables a Shor (asimétricos) de los vulnerables a Grover (simétricos y hash), indica la acción de remediación y diferencia "roto completamente" (compromiso retroactivo de la confidencialidad) de "debilitado".

## 2. Estándares NIST de criptografía post-cuántica (agosto de 2024)

El NIST publicó el 13 de agosto de 2024 los tres primeros estándares de criptografía post-cuántica: FIPS 203 (ML-KEM), FIPS 204 (ML-DSA) y FIPS 205 (SLH-DSA) (NIST, 2024a, 2024b, 2024c). Los tres resisten, según el estado actual del conocimiento, a adversarios con computadores cuánticos. Los tamaños de las tablas siguientes se transcribieron de las tablas oficiales de cada estándar.

### 2.1 ML-KEM (FIPS 203): encapsulamiento de claves

ML-KEM es un mecanismo de encapsulamiento de claves (KEM): permite que dos partes establezcan un secreto compartido sobre un canal público, que luego se usa con cifrado simétrico. Deriva de CRYSTALS-KYBER y su seguridad se relaciona con la dificultad del problema *Module Learning with Errors* (MLWE) (NIST, 2024a). Define tres conjuntos de parámetros, en orden creciente de seguridad y decreciente de rendimiento:

| Conjunto | Categoría NIST (equivalente simétrico) | Clave pública (encapsulación) | Clave privada (desencapsulación) | Ciphertext | Secreto compartido |
|---|---|---|---|---|---|
| ML-KEM-512 | 1 (AES-128) | 800 bytes | 1632 bytes | 768 bytes | 32 bytes |
| ML-KEM-768 | 3 (AES-192) | 1184 bytes | 2400 bytes | 1088 bytes | 32 bytes |
| ML-KEM-1024 | 5 (AES-256) | 1568 bytes | 3168 bytes | 1568 bytes | 32 bytes |

Fuente: Tablas 2 y 3 de NIST (2024a); las categorías se explican en NIST (2024a) y Moody et al. (2026). **El NIST recomienda ML-KEM-768 como conjunto de parámetros por defecto**, porque ofrece un amplio margen de seguridad con un costo de rendimiento razonable; los otros dos se reservan para casos en que se requiera más seguridad o menos tamaño (NIST, 2024a). ML-KEM **reemplaza a ECDH, X25519 y a RSA como mecanismo de intercambio o transporte de claves**.

### 2.2 ML-DSA (FIPS 204): firma digital basada en retículos

ML-DSA es un algoritmo de firma digital basado en retículos (*lattices*), derivado de CRYSTALS-Dilithium (NIST, 2024b). Define tres conjuntos de parámetros:

| Conjunto | Categoría NIST | Clave privada | Clave pública | Firma |
|---|---|---|---|---|
| ML-DSA-44 | 2 | 2560 bytes | 1312 bytes | 2420 bytes |
| ML-DSA-65 | 3 | 4032 bytes | 1952 bytes | 3309 bytes |
| ML-DSA-87 | 5 | 4896 bytes | 2592 bytes | 4627 bytes |

Fuente: Tablas 1 y 2 de NIST (2024b).

**Comparación con ECDSA-256.** ECDSA sobre P-256 tiene una clave pública de 64 bytes, una privada de 32 y una firma de unos 72 bytes en codificación DER (64 bytes sin formato). Frente a esas cifras, la firma de ML-DSA-44 es unas 34 veces mayor (2420/72), la de ML-DSA-65 unas 46 veces (3309/72) y la de ML-DSA-87 unas 64 veces (4627/72); la clave pública crece de 20 a 40 veces (1312/64 a 2592/64). La guía pide comparar también la velocidad de verificación. Los FIPS no publican tiempos de ejecución, que dependen de la implementación y del hardware, y este análisis no cita cifras de tiempo que no pudo verificar en una fuente primaria; la comparación se hace en bytes, que sí es una magnitud verificable.

### 2.3 SLH-DSA (FIPS 205): firma digital basada solo en hash

SLH-DSA es un esquema de firma *stateless* basado únicamente en funciones hash, derivado de SPHINCS+ (NIST, 2024c). Define 12 conjuntos de parámetros: seis combinaciones de tamaño de seguridad (128, 192 y 256 bits) y variante (`s`, firmas pequeñas, o `f`, generación rápida de firmas), cada una instanciable con SHA-2 o con SHAKE. La clave pública ocupa 2n bytes y la privada 4n bytes (n = 16, 24 o 32 bytes), y cada par de claves puede firmar como máximo 2⁶⁴ mensajes.

| Conjunto (SHA2 o SHAKE) | Categoría NIST | Clave pública | Firma |
|---|---|---|---|
| SLH-DSA-128s | 1 | 32 bytes | 7856 bytes |
| SLH-DSA-128f | 1 | 32 bytes | 17 088 bytes |
| SLH-DSA-192s | 3 | 48 bytes | 16 224 bytes |
| SLH-DSA-192f | 3 | 48 bytes | 35 664 bytes |
| SLH-DSA-256s | 5 | 64 bytes | 29 792 bytes |
| SLH-DSA-256f | 5 | 64 bytes | 49 856 bytes |

Fuente: Tabla 2 de NIST (2024c). La clave privada del conjunto de 128 bits ocupa 64 bytes y la pública 32.

**Por qué es más conservador que ML-DSA.** La seguridad de SLH-DSA depende únicamente de las propiedades de las funciones hash con que se instancia, que llevan décadas de estudio, y no asume la dificultad de un problema algebraico estructurado como MLWE, cuya seguridad a largo plazo frente a futuros avances de criptoanálisis ha tenido menos años de escrutinio. El precio es el tamaño: la firma de SLH-DSA-128s (7856 bytes) es 2,4 veces mayor que la de ML-DSA-65 (3309 bytes), y las variantes rápidas (`f`) tienen firmas aún mayores, hasta 49 856 bytes. Por eso se recomienda como **alternativa de respaldo** y diversificación, no como algoritmo principal.

### 2.4 Qué reemplaza a qué

| Función | Algoritmo clásico (vulnerable a Shor) | Reemplazo post-cuántico | Estándar |
|---|---|---|---|
| Intercambio o encapsulamiento de claves | ECDH, X25519, DH, RSA | **ML-KEM** (768 por defecto) | FIPS 203 |
| Firma digital de uso general | ECDSA, EdDSA, RSA | **ML-DSA** (ML-DSA-65, categoría 3, en este análisis) | FIPS 204 |
| Firma digital de respaldo o de larga vida | ECDSA, RSA | **SLH-DSA** | FIPS 205 |

ML-KEM **no es un esquema de firma**: solo establece claves. ML-DSA y SLH-DSA son esquemas de firma y no sirven para intercambiar claves. El NIST IR 8547 enumera estos estándares como destino de la transición de los algoritmos del Paso 1 (Moody et al., 2026).

**Checkpoint 2.** La sección incluye tablas comparativas con el tamaño en bytes de la clave pública, la clave privada, el ciphertext o la firma de los tres estándares, con fuente citada, y explica que ML-KEM reemplaza a ECDH y RSA para el intercambio de claves mientras que ML-DSA y SLH-DSA reemplazan a ECDSA y RSA para las firmas.

## 3. Plan de migración para tres perfiles organizacionales

La prioridad de migración de cada organización la determina el **horizonte de sensibilidad de sus datos** frente al tiempo que tardaría en existir un CRQC y al tiempo que tomará la propia migración: cuanto más tiempo deba permanecer secreto un dato, antes hay que protegerlo con criptografía post-cuántica, porque el tráfico capturado hoy puede descifrarse después (CISA, NSA y NIST, 2023). Los tres planes siguen los pasos que recomienda ese *factsheet*: establecer una hoja de ruta de preparación cuántica con un equipo de proyecto, preparar un inventario criptográfico con herramientas de descubrimiento, alimentar con él la evaluación de riesgos y conversar con los proveedores sobre sus hojas de ruta, y se alinean con los plazos del NIST: los algoritmos cuánticamente vulnerables quedan en desuso después de 2030 y prohibidos después de 2035 (Moody et al., 2026).

Todos los planes usan la **criptografía híbrida (clásica + post-cuántica en paralelo) como etapa de transición**: el secreto compartido combina el de un esquema clásico con el de ML-KEM, de modo que la sesión sigue protegida si falla cualquiera de los dos. En TLS 1.3 esto es el grupo `X25519MLKEM768` del RFC 10024 (Kwiatkowski et al., 2026). Como conjunto de parámetros por defecto de ML-KEM se usa 768, el que recomienda el NIST (NIST, 2024a).

### 3.1 Perfil A: hospital universitario

**Contexto.** Registros médicos con una sensibilidad de 50 a 75 años, portal de pacientes sobre TLS y firma digital de prescripciones con ECDSA. La amenaza HNDL es **crítica**: lo que un adversario capture hoy podría descifrarse dentro de 10 a 15 años, cuando los datos siguen siendo sensibles.

**(1) Inventario de sistemas con criptografía asimétrica activa.** Portal de pacientes (TLS), certificados de servidor y de cliente, firma de prescripciones, VPN entre sedes y con farmacias y aseguradoras, correo seguro, firma de actualizaciones de dispositivos médicos, servicios de directorio e infraestructura de clave pública (PKI) interna, y los respaldos y archivos cifrados. Se incluye la tecnología operativa (OT) y los dispositivos médicos conectados, que suelen ser los más difíciles de actualizar.

**(2) Clasificación de datos por horizonte de sensibilidad.**

| Dato | Horizonte | Riesgo HNDL | Prioridad |
|---|---|---|---|
| Historia clínica (tráfico y archivo) | 50 a 75 años | Crítico | 1 |
| Resultados de laboratorio e imágenes | 30 a 50 años | Alto | 1 |
| Prescripciones firmadas | Vigencia legal de la receta; autenticidad, no confidencialidad | Bajo (afecta a la autenticidad) | 2 |
| Datos administrativos y de facturación | 5 a 10 años | Medio | 3 |

**(3) Estrategia híbrida.** Habilitar `X25519MLKEM768` en el portal y en las VPN, y firmar las prescripciones con **ML-DSA-65** en una etapa de doble firma (ECDSA y ML-DSA) hasta que los verificadores externos soporten solo el esquema nuevo. El cifrado simétrico de los archivos (AES-256) no necesita cambio.

**(4) Cronograma en fases con hitos verificables.**

| Fase | Plazo | Hito verificable |
|---|---|---|
| 0. Inventario y hoja de ruta | primer semestre de 2027 | Inventario criptográfico completo con herramientas de descubrimiento, hoja de ruta aprobada y respuestas de los proveedores sobre su plan post-cuántico |
| 1. TLS híbrido en el portal | segundo semestre de 2027 | El 100 % de los *endpoints* públicos del portal negocia `X25519MLKEM768`, medido en los registros del servidor TLS |
| 2. Firma de prescripciones | 2028 | PKI interna piloto con ML-DSA-65 y emisión de prescripciones con doble firma; farmacias asociadas verifican ambas |
| 3. VPN y enlaces externos | 2029 | Todos los túneles entre sedes y con terceros usan establecimiento de claves híbrido o ML-KEM |
| 4. Fin del uso exclusivo de algoritmos clásicos | diciembre de 2030 | Ningún servicio nuevo usa ECDH/RSA/ECDSA de forma exclusiva (inicio del desuso que fija el NIST) |
| 5. Retiro de algoritmos vulnerables | 2035 | Los algoritmos clásicos de clave pública se eliminan de todos los sistemas (plazo de prohibición del NIST) |

**(5) Riesgos y mitigaciones.**

| Riesgo | Mitigación |
|---|---|
| Dispositivos médicos y sistemas heredados que no pueden actualizarse | Identificarlos en el inventario, aislarlos en segmentos de red protegidos por una pasarela con criptografía post-cuántica y planificar su reemplazo (Moody et al., 2026) |
| Datos ya capturados con intercambios clásicos (HNDL ya consumado) | Priorizar la protección del tráfico futuro; considerar la reencriptación de lo que aún no haya salido de la organización |
| Verificadores externos (farmacias, aseguradoras) sin soporte de ML-DSA | Doble firma durante la transición |
| Cadenas de certificados más grandes que afecten a la latencia del portal | Medir el efecto (sección 4) y usar certificados con una sola firma post-cuántica en la cadena corta |

**Justificación de la prioridad.** El Perfil A es el de **mayor urgencia**: su horizonte de 50 a 75 años excede por mucho cualquier estimación razonable del tiempo hasta un CRQC, de modo que la confidencialidad del tráfico actual ya está en riesgo. Por eso la fase 1 (el establecimiento de claves) va antes que las firmas.

### 3.2 Perfil B: startup de comercio electrónico

**Contexto.** Transacciones cifradas con AES-256 y TLS 1.3 (X25519 + ECDSA), datos de tarjetas sujetos a PCI-DSS, horizonte de sensibilidad de 5 a 7 años (el ciclo de vida de una tarjeta). La urgencia es menor que en salud, pero ofrecer TLS post-cuántico híbrido a los clientes es un diferenciador competitivo temprano.

**(1) Inventario.** Certificados de servidor y su autoridad certificadora, el *endpoint* TLS (balanceador o CDN), las bibliotecas criptográficas de la aplicación y de los clientes móviles y web, las pasarelas de pago, los servicios en la nube y las claves de firma del código.

**(2) Clasificación por horizonte.** Datos de tarjeta y de cuenta: 5 a 7 años (prioridad alta frente a HNDL, aunque menor que en el Perfil A); datos de navegación y de catálogo: menos de 1 año (prioridad baja).

**(3) Estrategia híbrida.** Habilitar `X25519MLKEM768` en el borde (balanceador o CDN). Es un cambio de configuración, no de código, siempre que el proveedor lo ofrezca. Las firmas del certificado se dejan en ECDSA hasta que las autoridades certificadoras públicas emitan certificados con ML-DSA; no se encontró una fecha verificada para ello.

**(4) Cronograma.**

| Fase | Plazo | Hito verificable |
|---|---|---|
| 0. Inventario y consulta a proveedores | primer trimestre de 2027 | Inventario de certificados, bibliotecas y CDN; confirmación escrita de qué proveedores soportan `X25519MLKEM768` |
| 1. TLS híbrido en el borde | segundo trimestre de 2027 | Porcentaje de conexiones que negocian `X25519MLKEM768` visible en los registros; sin aumento de errores de *handshake* |
| 2. Clientes y bibliotecas | 2028 | Aplicaciones móviles y SDK actualizados; las pruebas de compatibilidad no muestran fallos con redes y *middleboxes* de los clientes |
| 3. Firmas post-cuánticas | cuando las autoridades certificadoras públicas lo permitan, y antes de 2030 | Certificado de prueba con ML-DSA validado en un entorno de pruebas |
| 4. Fin del uso exclusivo de algoritmos clásicos | diciembre de 2030 | Ningún servicio usa solo ECDH/ECDSA (desuso del NIST) |

**(5) Riesgos y mitigaciones.** Los *middleboxes* y clientes antiguos que no toleren un `ClientHello` de más de 1 KB: pruebas de compatibilidad antes del despliegue y cadena de reversión a X25519 sin ML-KEM para quienes fallen. El aumento de latencia en redes móviles con pérdida de paquetes: medir con datos reales (sección 4). La dependencia del soporte de la CDN y de la autoridad certificadora: elegir proveedores con hoja de ruta publicada.

**Justificación de la prioridad.** El horizonte de 5 a 7 años hace que el riesgo HNDL sea moderado, por eso el plan arranca después del Perfil A, pero el costo de la fase 1 es bajo (configuración) y el beneficio de protección doble es alto. La fase final se alinea con el desuso de 2030 del NIST (Moody et al., 2026).

### 3.3 Perfil C: entidad gubernamental de defensa

**Contexto.** Comunicaciones clasificadas, firma de documentos oficiales (PKI nacional) y VPN entre agencias, con datos de 25 a 50 años de sensibilidad. Es un adversario de nivel estatal y, si se trata de un sistema de seguridad nacional de Estados Unidos, la migración es **mandatoria** según la NSA: el 7 de septiembre de 2022 publicó el *Commercial National Security Algorithm Suite 2.0* (CNSA 2.0), que fija los algoritmos resistentes a la computación cuántica que serán obligatorios en esos sistemas; se basa en las selecciones del NIST y en tanto no se completen los estándares se mantiene la conformidad con CNSA 1.0 (NSA, 2022b). La NSA indica además que los propietarios de estos sistemas no deben desplegar algoritmos resistentes a la computación cuántica en redes de misión hasta que los hayan examinado el NIST y la NIAP, como exige CNSSP-11 (NSA, 2022b).

**Fuente de CNSA 2.0.** Los algoritmos y los plazos de este perfil provienen del aviso de ciberseguridad de la NSA *Announcing the Commercial National Security Algorithm Suite 2.0* (versión 1.0, septiembre de 2022, PP-22-1338), que se leyó completo (NSA, 2022a). Esa versión es anterior a los estándares finales del NIST: nombra los algoritmos como CRYSTALS-Kyber y CRYSTALS-Dilithium, con especificación "por determinar" y parámetros de "nivel V". Este análisis los interpreta como ML-KEM-1024 y ML-DSA-87, los conjuntos de categoría 5 de los FIPS 203 y 204; esa equivalencia es interpretación propia, no una afirmación del aviso. No se revisaron versiones posteriores del aviso, de modo que los plazos podrían haberse actualizado desde 2022. Si la entidad no es estadounidense, se aplican los lineamientos equivalentes de su país con la misma lógica.

**(1) Inventario.** Todas las redes y enlaces de comunicaciones clasificadas, VPN entre agencias, módulos de seguridad de hardware (HSM), la PKI nacional y sus autoridades certificadoras, la firma de *firmware* y software, y los dispositivos criptográficos de campo.

**(2) Clasificación por horizonte.** Datos clasificados de 25 a 50 años (prioridad máxima); documentos oficiales firmados de larga vida (la validez de la firma debe sostenerse); comunicaciones tácticas de corta vida (prioridad menor).

**(3) Estrategia.** Cumplir CNSA 2.0, que según la NSA (2022a) exige:

| Función | Algoritmo de CNSA 2.0 | Parámetros |
|---|---|---|
| Cifrado simétrico | AES | Claves de 256 bits para todos los niveles de clasificación |
| Función hash | SHA-384 o SHA-512 | Todos los niveles de clasificación |
| Establecimiento de claves | CRYSTALS-Kyber (ML-KEM-1024 en este análisis) | Parámetros de nivel V |
| Firma digital de uso general | CRYSTALS-Dilithium (ML-DSA-87 en este análisis) | Parámetros de nivel V |
| Firma de software y *firmware* | LMS o XMSS (NIST SP 800-208) | Todos los parámetros aprobados; se recomienda LMS con SHA-256/192 |

Mientras tanto sigue exigiéndose CNSA 1.0: ECDH y ECDSA con la curva P-384, SHA-384, y RSA o Diffie-Hellman con módulo de al menos 3072 bits (NSA, 2022a). La NSA advierte que CNSA 2.0 dejará en desuso RSA, Diffie-Hellman y la criptografía de curva elíptica cuando se vuelva obligatoria. Las firmas LMS y XMSS exigen cumplir todos los requisitos de NIST SP 800-208, incluida la gestión del estado de las claves y la firma en hardware. Respecto a la criptografía híbrida, el aviso admite que los protocolos o la interoperabilidad pueden permitirla o exigirla, pero precisa que, llegada la fecha, seleccionar solo algoritmos de CNSA 1.0 dejará de estar aprobado (NSA, 2022a). Por eso el plan usa el modo híbrido solo para interoperar con socios que aún no migran. Se empieza por el **establecimiento de claves** y por la **firma de *firmware***, que son los casos con más riesgo retroactivo y más difíciles de reparar en campo.

**(4) Cronograma.** La NSA fija fechas distintas según el tipo de tecnología: "apoyar y preferir" CNSA 2.0 (*support and prefer*) y, más tarde, usarlo de forma exclusiva (NSA, 2022a).

| Tecnología (NSA, 2022a) | Apoyar y preferir CNSA 2.0 | Uso exclusivo de CNSA 2.0 |
|---|---|---|
| Firma de software y *firmware* | 2025 | 2030 |
| Equipos de red tradicionales (VPN, enrutadores) | 2026 | 2030 |
| Navegadores y servidores web, servicios en la nube | 2025 | 2033 |
| Sistemas operativos | 2027 | 2033 |
| Equipos especializados (dispositivos restringidos, PKI de gran tamaño) | 2030 | 2033 |
| Aplicaciones a medida y equipos heredados | no aplica | actualizar o reemplazar antes de 2033 |

La NSA espera que la transición completa de los sistemas de seguridad nacional termine en 2035, en línea con NSM-10 (NSA, 2022a). Las fechas de 2025 y 2026 de la tabla **ya vencieron**, de modo que la fase 0 del plan debe empezar con un análisis de brechas: si la entidad aún no las cumple, tratarlas como incumplimientos que se corrigen primero. Combinado con los plazos federales del NIST, el cronograma del perfil es:

| Fase | Plazo | Hito verificable |
|---|---|---|
| 0. Inventario y análisis de brechas | 2027 | Inventario criptográfico de todos los sistemas de misión, priorizado por horizonte de sensibilidad, y lista de los sistemas que incumplen las fechas ya vencidas de 2025 y 2026 |
| 1. Validación de productos | 2027 a 2028 | Los productos con ML-KEM y ML-DSA cuentan con la validación NIAP o de la NSA que exige CNSSP 11 antes de entrar en redes de misión; los equipos nuevos cumplen los perfiles de protección de la NIAP y los antiguos en su próxima actualización (NSA, 2022a) |
| 2. Establecimiento de claves | antes del 31 de diciembre de 2030 | Los sistemas de alto impacto usan ML-KEM para establecer claves (plazo federal de EO 14412 y OMB M-26-15; Moody et al., 2026) |
| 3. Firma de software y red | 2030 | Firma de software y *firmware* con LMS o XMSS, y VPN y enrutadores, usan CNSA 2.0 de forma exclusiva (NSA, 2022a) |
| 4. Firmas digitales | antes del 31 de diciembre de 2031 | Los sistemas de alto impacto firman con algoritmos post-cuánticos (plazo federal; Moody et al., 2026) |
| 5. Navegadores, nube, sistemas operativos y equipos especializados | 2033 | Uso exclusivo de CNSA 2.0; las aplicaciones a medida y los equipos heredados se actualizaron o reemplazaron (NSA, 2022a) |
| 6. Cierre de la transición | 2035 | Fin del uso de algoritmos vulnerables (objetivo de NSM-10 y prohibición del NIST; NSA, 2022a; Moody et al., 2026) |

**(5) Riesgos y mitigaciones.**

| Riesgo | Mitigación |
|---|---|
| Datos de 25 a 50 años expuestos a HNDL de un adversario estatal | Priorizar el establecimiento de claves y eliminar las rutas con criptografía exclusivamente clásica en primer lugar |
| Dependencia de proveedores sin módulos validados | Exigir en los contratos criptografía post-cuántica integrada, calendarios de actualización (CISA, NSA y NIST, 2023) y validación NIAP o de la NSA, no solo FIPS (NSA, 2022a) |
| Sistemas que no admiten criptografía post-cuántica | Identificarlos y priorizarlos para su reemplazo o retiro; el equipo heredado que no se renueve requerirá una exención y un plan de cumplimiento (NSA, 2022a; Moody et al., 2026) |
| Firmas con estado (LMS/XMSS) mal gestionadas | Controles estrictos de gestión del estado de las claves, y firma en hardware como exige NIST SP 800-208 (NSA, 2022a) |
| Fechas de 2025 y 2026 ya vencidas | Análisis de brechas en la fase 0 y plan de corrección con prioridad sobre el resto |

**Justificación de la prioridad.** El Perfil C combina el **mayor horizonte** con el **adversario más capaz** y con un **mandato regulatorio**, así que es el de plazos más estrictos y menos flexibles: no puede esperar a que la criptografía híbrida madure en el mercado.

**Checkpoint 3.** El plan cubre los tres perfiles con inventario, clasificación por horizonte, estrategia híbrida, un cronograma con más de tres hitos verificables y riesgos con mitigaciones; la prioridad de cada uno se justifica por su horizonte de sensibilidad (A: crítico; C: máximo y mandatorio; B: moderado), con las fuentes del NIST, la NSA y CISA.

## 4. Tamaños de claves y firmas, e impacto en TLS 1.3

El costo principal de la criptografía post-cuántica no es de cómputo sino de **bytes**: claves, *ciphertexts* y firmas son de uno a dos órdenes de magnitud mayores que los de la criptografía de curva elíptica, y en un protocolo como TLS esos bytes viajan en cada *handshake*.

### 4.1 Tabla comparativa de tamaños

| Algoritmo | Tipo | Clave pública | Clave privada | Ciphertext o firma | Fuente |
|---|---|---|---|---|---|
| X25519 | Intercambio de claves (clásico) | 32 bytes | 32 bytes | (32 bytes de clave compartida enviada) | Langley et al. (2016) |
| ECDSA P-256 | Firma (clásico) | 64 bytes | 32 bytes | 64 bytes (72 en DER) | Inventario de la sección 1 |
| Ed25519 | Firma (clásico) | 32 bytes | 32 bytes | 64 bytes | Josefsson y Liusvaara (2017) |
| RSA-2048 | Firma o transporte de claves (clásico) | 256 bytes (módulo) | cerca de 256 bytes (exponente privado) | 256 bytes | Cálculo: módulo de 2048 bits |
| **ML-KEM-512** | KEM post-cuántico | 800 bytes | 1632 bytes | 768 bytes | NIST (2024a) |
| **ML-KEM-768** | KEM post-cuántico | 1184 bytes | 2400 bytes | 1088 bytes | NIST (2024a) |
| **ML-KEM-1024** | KEM post-cuántico | 1568 bytes | 3168 bytes | 1568 bytes | NIST (2024a) |
| **ML-DSA-44** | Firma post-cuántica | 1312 bytes | 2560 bytes | 2420 bytes | NIST (2024b) |
| **ML-DSA-65** | Firma post-cuántica | 1952 bytes | 4032 bytes | 3309 bytes | NIST (2024b) |
| **ML-DSA-87** | Firma post-cuántica | 2592 bytes | 4896 bytes | 4627 bytes | NIST (2024b) |
| **SLH-DSA-128s** | Firma post-cuántica (hash) | 32 bytes | 64 bytes | 7856 bytes | NIST (2024c) |
| **SLH-DSA-128f** | Firma post-cuántica (hash) | 32 bytes | 64 bytes | 17 088 bytes | NIST (2024c) |

Los tamaños de X25519, Ed25519 y RSA-2048 son valores estándar de esos esquemas; el de la clave privada de RSA es aproximado, porque depende de la representación (con parámetros del teorema chino del resto ocupa más). Los de los estándares post-cuánticos se transcribieron de los FIPS.

**Factores de crecimiento respecto a la criptografía actual.**

| Comparación | Cálculo | Factor |
|---|---|---|
| Clave pública ML-KEM-768 frente a X25519 | 1184 / 32 | 37 veces |
| *Ciphertext* ML-KEM-768 frente a la clave pública X25519 del servidor | 1088 / 32 | 34 veces |
| Clave pública ML-DSA-65 frente a ECDSA P-256 | 1952 / 64 | 30,5 veces |
| Firma ML-DSA-65 frente a ECDSA P-256 (DER) | 3309 / 72 | 46 veces |
| Firma ML-DSA-65 frente a RSA-2048 | 3309 / 256 | 12,9 veces |
| Firma SLH-DSA-128s frente a ECDSA P-256 (DER) | 7856 / 72 | 109 veces |
| Clave pública SLH-DSA-128s frente a ECDSA P-256 | 32 / 64 | 0,5 veces (la mitad) |

SLH-DSA es la única opción cuya clave pública es **menor** que la de ECDSA, pero paga con las firmas más grandes de la tabla.

### 4.2 Impacto en un handshake TLS 1.3 con intercambio híbrido X25519 + ML-KEM-768

En TLS 1.3 el intercambio de claves híbrido `X25519MLKEM768` (RFC 10024) concatena la clave de X25519 y la de ML-KEM-768 en la extensión `key_share`: el cliente envía **1216 bytes** (32 de X25519 y 1184 de ML-KEM-768) y el servidor responde con **1120 bytes** (32 y 1088), frente a 32 y 32 bytes de X25519 solo (Kwiatkowski et al., 2026). El `ClientHello` crece, por tanto, en 1184 bytes y el `ServerHello` en 1088 bytes. Con un segmento TCP típico de 1460 bytes, solo la clave compartida del cliente ocupa el 83 % del segmento, así que el resto del mensaje apenas cabe y es probable que se reparta en más de un segmento.

Para dimensionar el efecto total se suman los bytes de material criptográfico de un *handshake* completo con una cadena de dos certificados (hoja e intermedio; la raíz no se envía). Contiene cuatro elementos: la clave compartida del cliente, la del servidor, dos claves públicas (las de los certificados) y tres firmas (la de la hoja, la del intermedio y la de `CertificateVerify`).

| Escenario | Intercambio de claves (cliente + servidor) | Autenticación (2 claves públicas + 3 firmas) | Total | Respecto al clásico |
|---|---|---|---|---|
| 1. Clásico: X25519 + ECDSA P-256 | 32 + 32 = 64 | 2·64 + 3·72 = 344 | 408 bytes | 1 vez |
| 2. Híbrido + ECDSA P-256 (solo KEM migrado) | 1216 + 1120 = 2336 | 344 | 2680 bytes | 6,6 veces |
| 3. Híbrido + ML-DSA-44 | 2336 | 2·1312 + 3·2420 = 9884 | 12 220 bytes | 30 veces |
| 4. Híbrido + ML-DSA-65 | 2336 | 2·1952 + 3·3309 = 13 831 | 16 167 bytes | 39,6 veces |
| 5. Híbrido + SLH-DSA-128s | 2336 | 2·32 + 3·7856 = 23 632 | 25 968 bytes | 63,6 veces |

Estas cifras **solo cuentan el material criptográfico**; el mensaje real es mayor porque incluye nombres, extensiones y otros campos de los certificados X.509 que este análisis no cuantifica, de modo que son cotas inferiores.

**Lectura de la tabla.**

1. **Migrar solo el intercambio de claves cuesta poco** (escenario 2: 2,3 KB adicionales) y es lo que protege contra la amenaza HNDL, porque el secreto de sesión es lo que un adversario captura hoy. Por eso la fase 1 de los perfiles A y B de la sección 3 es TLS híbrido con certificados ECDSA.
2. **Migrar la autenticación es lo que encarece el *handshake*.** El escenario 4 transmite unos 16 KB, 40 veces más que el clásico, y la firma post-cuántica protege la autenticidad, que solo puede atacarse en el momento de la conexión y no retroactivamente, así que es menos urgente.
3. **Efecto en la ventana inicial de TCP.** La ventana de congestión inicial habitual es de 10 segmentos, unos 14 600 bytes con segmentos de 1460 (Chu et al., 2013). El vuelo del servidor de cada escenario es la clave compartida de 1120 bytes más su autenticación: en los escenarios 2 y 3 es de 1464 y 11 004 bytes y cabe en la ventana; en el escenario 4 es de 1120 + 13 831 = 14 951 bytes y **la supera** incluso sin contar los campos X.509. El escenario 3, con 11 004 bytes, deja un margen de unos 3,6 KB para esos campos. Cuando el vuelo supera la ventana, el servidor debe esperar un ACK antes de seguir enviando, lo que añade **un viaje de ida y vuelta (RTT)** al *handshake*; en una red móvil con 100 ms de RTT son 100 ms adicionales por conexión nueva. Ese valor es un ejemplo ilustrativo del cálculo, no una medición.
4. **Mitigaciones.** Reutilizar sesiones (reanudación) para evitar repetir el *handshake* completo; usar cadenas de certificados cortas (una sola autoridad intermedia); considerar ML-DSA-44 en las hojas de menor riesgo; y, a largo plazo, soluciones que reduzcan el tamaño de la cadena de certificados, que el análisis no evalúa por no haber una fuente verificada en esta revisión.

### 4.3 Otros costos por tamaño

- **Almacenamiento y ancho de banda de claves.** Una clave privada de ML-DSA-65 (4032 bytes) es 126 veces mayor que una de ECDSA P-256 (32 bytes) y la pública es unas 30 veces mayor; para una PKI con millones de certificados (como en el Perfil A) esto multiplica el tamaño de los registros, las listas de revocación y las copias de seguridad.
- **Dispositivos restringidos.** Los dispositivos médicos e IoT con poca memoria y ancho de banda sufren más con firmas de 3 a 8 KB; es el motivo por el que el inventario del Perfil A los identifica aparte.
- **Firmas de *firmware* y documentos.** Una firma de 3309 bytes es insignificante frente a una imagen de *firmware* de megabytes, así que el costo por tamaño importa sobre todo en protocolos de tiempo real, no en firma de archivos.

**Checkpoint 4.** La sección tabula los tamaños de clave y firma de los algoritmos clásicos y de los tres estándares post-cuánticos, calcula los factores de crecimiento y cuantifica el impacto sobre un *handshake* TLS 1.3 con el intercambio híbrido `X25519MLKEM768` (cliente 1216 bytes, servidor 1120 bytes) y con distintas firmas, incluyendo el efecto sobre la ventana inicial de TCP y las mitigaciones.

## 5. Decisiones técnicas

### 5.1 Perfil A: ¿qué algoritmo de firma debe prescribir el análisis para las recetas médicas?

<!-- decision-3:inicio -->
Para firmar las recetas del hospital se prescribe **ML-DSA-65 como firma principal, acompañada de la firma ECDSA actual durante la transición (doble firma), y SLH-DSA reservado para las claves de la raíz de la infraestructura de clave pública (PKI) y para la evidencia de archivo de larga vida**. Las recetas se emiten en gran volumen y se verifican en la farmacia en el momento de dispensar, de modo que el tamaño de la firma pesa más que en una firma poco frecuente: la de ML-DSA-65 ocupa 3309 bytes, frente a 7856 de SLH-DSA-128s (2,4 veces más) y 17 088 de SLH-DSA-128f (5,2 veces más); por cada millón de recetas son unos 3,3 GB, 7,9 GB y 17,1 GB de firmas (cálculo propio con los tamaños de los FIPS 204 y 205). La razón para no usar SLH-DSA en las recetas, aunque dependa solo de funciones hash y sea el más conservador, es ese costo en bytes, que se paga en cada documento. En cambio, la clave de una autoridad raíz firma muy pocas veces y debe ser creíble durante décadas, de modo que sus 7856 bytes no importan y la diversificación sí: si apareciera un avance de criptoanálisis contra los retículos de los que depende ML-DSA, una raíz basada en hash seguiría siendo válida. La doble firma se justifica porque farmacias y aseguradoras migrarán a ritmos distintos; ECDSA mantiene la verificación mientras ML-DSA protege frente a un CRQC, y se retira cuando los verificadores externos soporten ML-DSA, a más tardar en el desuso de diciembre de 2030 que fija el NIST. Esta recomendación no se apoya en tiempos de ejecución, porque los FIPS no los publican y no se verificó una fuente primaria; se apoya en tamaños, categoría de seguridad (la 3 de ML-DSA-65 coincide con la de ML-KEM-768) y la naturaleza de cada uso.
<!-- decision-3:fin -->

### 5.2 Perfil B: ¿el esquema híbrido debe ser permanente o solo transitorio?

<!-- decision-4:inicio -->
Para la startup de comercio electrónico se prescribe el esquema híbrido `X25519MLKEM768` como solución **transitoria con una revisión explícita en 2030, y no como arquitectura permanente**. A favor de mantenerlo mientras dure la transición está su bajo costo: frente a ML-KEM-768 solo, el híbrido añade apenas 32 bytes por dirección (1216 frente a 1184 en el cliente, 1120 frente a 1088 en el servidor, es decir, un 2,7 % y un 2,9 % más), de modo que el tamaño no justifica abandonarlo pronto. Su valor es de seguridad: ML-KEM se estandarizó en 2024, mientras que las curvas elípticas llevan décadas de análisis, y si se descubriera una debilidad clásica en el problema de retículos MLWE, la mitad X25519 seguiría protegiendo la sesión frente a adversarios sin computador cuántico (Kwiatkowski et al., 2026). El horizonte de datos del Perfil B también lo respalda: lo que se cifre en 2027 debe seguir secreto hasta 2034 y el híbrido cubre esa ventana completa. Pero no debe ser permanente: contra un adversario con un CRQC la mitad X25519 no aporta nada y solo añade complejidad de implementación y una dependencia que el NIST va a retirar, pues declara no permitidos los esquemas clásicos de establecimiento de claves después de 2035 (Moody et al., 2026), lo que afecta a cualquier cliente del Perfil B sujeto a esa norma. La regla de salida propuesta es: reevaluar en 2030 y pasar a ML-KEM sin componente clásico solo si no hubo avances de criptoanálisis significativos contra MLWE, los clientes del comercio ya lo soportan y el proveedor ofrece ese grupo en TLS; este análisis no verificó que exista hoy un grupo TLS de ML-KEM solo estandarizado, de modo que esa condición queda abierta.
<!-- decision-4:fin -->

## 6. Conclusiones

1. **La amenaza es real pero asimétrica.** El algoritmo de Shor rompe por completo RSA, ECDH y ECDSA; el de Grover solo debilita a AES y a las funciones hash, y se compensa con claves de 256 bits. La urgencia no depende de cuándo llegue el CRQC sino de cuánto tiempo deben permanecer secretos los datos (HNDL).
2. **Los estándares ya existen.** ML-KEM (FIPS 203), ML-DSA (FIPS 204) y SLH-DSA (FIPS 205) cubren el intercambio de claves y la firma, y el RFC 10024 define su uso híbrido en TLS 1.3.
3. **El costo es de bytes, no de algoritmos nuevos.** Migrar solo el intercambio de claves añade unos 2,3 KB por *handshake*; migrar también la autenticación con ML-DSA-65 lo lleva a unos 16 KB, 40 veces el *handshake* clásico, y puede superar la ventana inicial de TCP.
4. **El orden de la migración sigue al horizonte de datos.** Primero el establecimiento de claves (protege lo capturado hoy), luego las firmas; el Perfil A es el más urgente, el C el más estricto por mandato y el B el de menor urgencia pero de bajo costo.
5. **Hay datos que este análisis no pudo verificar.** Los tiempos de ejecución de ML-DSA y SLH-DSA, la existencia de un grupo TLS de ML-KEM sin componente clásico y las versiones del aviso de la NSA posteriores a la 1.0 de septiembre de 2022 quedan marcados como no verificados en la fuente primaria. Los algoritmos y plazos de CNSA 2.0 sí se verificaron en esa versión 1.0.

## 7. Referencias

Chu, J., Dukkipati, N., Cheng, Y., y Mathis, M. (2013). *Increasing TCP's initial window* (RFC 6928). Internet Engineering Task Force. https://doi.org/10.17487/RFC6928

CISA, NSA y NIST. (2023, agosto). *Quantum-readiness: Migration to post-quantum cryptography* [Hoja informativa]. Cybersecurity and Infrastructure Security Agency. https://www.cisa.gov/resources-tools/resources/quantum-readiness-migration-post-quantum-cryptography

Gidney, C. (2025). *How to factor a 2048-bit RSA integer with less than a million noisy qubits* (arXiv:2505.15917). arXiv. https://arxiv.org/abs/2505.15917 *(fuente académica reciente)*

Gidney, C., y Ekerå, M. (2021). How to factor 2048 bit RSA integers in 8 hours using 20 million noisy qubits. *Quantum, 5*, Artículo 433. https://doi.org/10.22331/q-2021-04-15-433

Grover, L. K. (1996). A fast quantum mechanical algorithm for database search. En *Proceedings of the 28th Annual ACM Symposium on Theory of Computing* (pp. 212-219). ACM. https://doi.org/10.1145/237814.237866

Josefsson, S., y Liusvaara, I. (2017). *Edwards-curve digital signature algorithm (EdDSA)* (RFC 8032). Internet Engineering Task Force. https://doi.org/10.17487/RFC8032

Kwiatkowski, K., Kampanakis, P., Westerbaan, B. E., y Stebila, D. (2026). *Post-quantum traditional (PQ/T) hybrid key agreement mechanisms for TLS 1.3* (RFC 10024). Internet Engineering Task Force. https://www.rfc-editor.org/info/rfc10024 *(fuente técnica de implementación)*

Langley, A., Hamburg, M., y Turner, S. (2016). *Elliptic curves for security* (RFC 7748). Internet Engineering Task Force. https://doi.org/10.17487/RFC7748

Moody, D., Perlner, R., Regenscheid, A., Robinson, A., y Cooper, D. (2026). *Transition to post-quantum cryptography standards* (NIST IR 8547). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.IR.8547

National Institute of Standards and Technology. (2024a). *Module-lattice-based key-encapsulation mechanism standard* (FIPS 203). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.203

National Institute of Standards and Technology. (2024b). *Module-lattice-based digital signature standard* (FIPS 204). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.204

National Institute of Standards and Technology. (2024c). *Stateless hash-based digital signature standard* (FIPS 205). U.S. Department of Commerce. https://doi.org/10.6028/NIST.FIPS.205

National Security Agency. (2022a, septiembre). *Announcing the Commercial National Security Algorithm Suite 2.0* (PP-22-1338, versión 1.0) [Aviso de ciberseguridad]. https://media.defense.gov/2022/Sep/07/2003071834/-1/-1/0/CSA_CNSA_2.0_ALGORITHMS_.PDF

National Security Agency. (2022b, 7 de septiembre). *NSA releases future quantum-resistant (QR) algorithm requirements for National Security Systems* [Comunicado de prensa]. https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/Article/3148990/nsa-releases-future-quantum-resistant-qr-algorithm-requirements-for-national-se/

Shor, P. W. (1997). Polynomial-time algorithms for prime factorization and discrete logarithms on a quantum computer. *SIAM Journal on Computing, 26*(5), 1484-1509. https://doi.org/10.1137/S0097539795293172

**Nota sobre las citas.** El informe NIST IR 8547 se cita en el texto como Moody et al. (2026) y los tres FIPS como NIST (2024a, 2024b, 2024c). Los algoritmos y plazos de CNSA 2.0 provienen del aviso de la NSA (2022a); el comunicado de prensa (2022b) solo se usa para el contexto y para la exigencia de validación de CNSSP 11.
