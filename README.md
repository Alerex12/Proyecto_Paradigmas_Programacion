# Analisis inteligente de datos — Modulo 1: carga y preprocesamiento

Aplicacion en **Python + Streamlit** que prepara un conjunto de datos para las
tecnicas de analisis posteriores (agrupamiento, deteccion de valores atipicos y
correlaciones).

Este repositorio cubre la **primera parte del proyecto**: carga de archivos CSV
y Excel, validacion de formatos, manejo de errores, limpieza basica (duplicados,
valores nulos, conversion de tipos) y deteccion automatica del tipo de cada
variable.

---

## Como ejecutarlo

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python generar_datos_prueba.py
streamlit run app.py
```

La app abre en <http://localhost:8501>.

Para probar la logica sin levantar la interfaz:

```bash
python probar_core.py
```

---

## Estructura

```
ProyectoIA_Analisis/
├── app.py                     # Pagina principal de Streamlit
├── core/                      # Logica de negocio (sin dependencia de Streamlit)
│   ├── carga.py               # Lectura CSV/Excel, validaciones, deteccion de formato
│   ├── tipos.py               # Deteccion automatica del tipo de cada variable
│   ├── limpieza.py            # Duplicados, nulos, conversion de tipos, bitacora
│   └── estado.py              # Estado compartido entre paginas
├── pages/
│   ├── 1_Carga_de_datos.py
│   ├── 2_Limpieza.py
│   └── 3_Resumen.py
├── datos_ejemplo/             # Dataset sucio generado para pruebas
├── generar_datos_prueba.py
├── probar_core.py             # Prueba de humo de todo el flujo
└── requirements.txt
```

**Regla de la estructura:** `core/` no importa Streamlit. Toda la logica es
testeable desde consola y reutilizable desde un notebook; `pages/` solo arma la
interfaz. Quien agregue clustering, outliers o correlaciones deberia seguir el
mismo patron: un modulo en `core/` con la logica y una pagina en `pages/`.

---

## Que hace cada parte

### 1. Carga (`core/carga.py`)

- Formatos aceptados: `.csv`, `.txt`, `.tsv`, `.xlsx`, `.xls`, `.xlsm`.
- Validaciones: extension soportada, archivo no vacio, tamano maximo 200 MB,
  y que el archivo leido tenga al menos una fila y una columna.
- **Codificacion automatica**: prueba UTF-8, UTF-8 con BOM, Latin-1 y CP1252.
- **Separador automatico**: `csv.Sniffer` y, si falla, conteo de ocurrencias de
  `, ; \t |` en las primeras lineas.
- **Excel**: lista las hojas del libro y permite elegir cual cargar.
- **Nombres de columna**: recorta espacios, nombra las columnas sin titulo
  (`Unnamed: 3` → `columna_4`) y desambigua los nombres repetidos.
- Todos los errores previsibles se lanzan como `ErrorCarga`, con un mensaje
  pensado para mostrarle al usuario en pantalla.

### 2. Deteccion de tipos (`core/tipos.py`)

pandas solo conoce dtypes (`int64`, `object`, ...). Para decidir que columna
sirve para cada tecnica hace falta el **tipo semantico**:

| Tipo | Criterio | Uso posterior |
|---|---|---|
| `numerica_continua` | decimales, o enteros con muchos valores distintos | clustering, outliers, correlacion |
| `numerica_discreta` | enteros con <= 20 valores distintos | correlacion |
| `categorica` | <= 25 categorias y cardinalidad < 50% | requiere codificacion |
| `booleana` | dos valores (si/no, 0/1, true/false) | — |
| `fecha` | >= 80% de los valores parsean como fecha | derivar variables |
| `identificador` | >= 95% de valores distintos | **excluir** |
| `constante` | un solo valor | **excluir** |
| `texto` | alta variabilidad | **excluir** |
| `vacia` | todo nulo | **excluir** |

Ademas reconoce numeros escondidos en texto (`₡850.000,00`, `45%`, `$300`) y
evita confundir un ano suelto (`2024`) con una fecha. Los umbrales estan
centralizados como constantes al inicio del modulo para poder justificarlos en
el informe.

### 3. Limpieza (`core/limpieza.py`)

- **Normalizacion previa**: recorte de espacios y conversion de marcadores
  textuales (`N/A`, `-`, `sin dato`, `?`, ...) en nulos reales. Sin este paso
  el conteo de nulos es falso.
- **Duplicados**: por fila completa o por un subconjunto de columnas,
  conservando la primera o la ultima aparicion.
- **Nulos**: por columna, con estrategias conservar / eliminar filas / media /
  mediana / moda / cero / valor constante. Las estrategias numericas se
  bloquean en columnas no numericas.
- **Conversion de tipos**: automatica segun la deteccion, o manual por columna
  si la deteccion se equivoco. Informa cuantos valores no se pudieron convertir.
- **Bitacora**: registro de cada operacion con filas antes/despues, exportable
  a CSV. Sirve de evidencia del preprocesamiento en el informe.

Ninguna funcion modifica el DataFrame recibido: todas devuelven una copia nueva.

---

## Dataset de prueba

`generar_datos_prueba.py` crea un dataset de clientes deliberadamente sucio
(CSV con separador `;` y Excel de dos hojas) que contiene:

- 12 filas duplicadas
- nulos escritos de 4 formas distintas (`NaN`, `N/A`, `-`, `sin dato`)
- ingresos como texto con simbolo de moneda y separador de miles
- fechas como texto en formato `dd/mm/aaaa`
- una columna constante (`pais`), un identificador (`id_cliente`) y una columna
  casi vacia (`comentario`)
- espacios sobrantes en `ciudad`

Sirve para demostrar cada validacion sin depender de datos reales.

---

## Interfaz para las siguientes etapas

El resto del equipo trabaja sobre el dataset ya preprocesado:

```python
from core import estado, tipos as t

datos = estado.exigir_datos()          # corta la pagina si no hay dataset cargado
perfil = t.perfilar(datos)             # tipo semantico de cada columna
grupos = t.columnas_analizables(perfil)

grupos["numericas"]    # para clustering, outliers y correlaciones
grupos["categoricas"]  # requieren codificacion previa
grupos["fechas"]
grupos["excluir"]      # ids, constantes, texto libre
```

Para agregar una etapa nueva basta con crear `pages/4_Clustering.py` con esas
cuatro lineas al inicio; Streamlit la suma sola al menu lateral.

---

## Notas tecnicas

- Probado con Python 3.14, pandas 3.0 y Streamlit 1.60.
- En pandas 3 las columnas de texto pueden tener dtype `str` en lugar de
  `object`, y ya no se hace upcast implicito al asignar. Por eso el codigo usa
  `tipos.es_texto()` en vez de comparar contra `object`.
- La navegacion entre paginas debe hacerse con los enlaces del menu lateral:
  escribir la URL a mano recarga la sesion y se pierde el dataset en memoria.
