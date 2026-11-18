
import ipaddress
import io
import logging
import os
import re
import socket
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from groq import Groq
from pypdf import PdfReader


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

load_dotenv()

MODEL = "openai/gpt-oss-20b"

MAX_HISTORIAL = 4
MAX_COMPLETION_TOKENS = 6144
REASONING_EFFORT = "low"

TIMEOUT_API = 120.0
MAX_REINTENTOS_API = 0

# Límites para la lectura documental
MAX_PDFS_MANTENIMIENTO = 1
MAX_TAMANO_PDF = 20 * 1024 * 1024
MAX_PAGINAS_PDF = 25
MAX_CARACTERES_PDF = 9000
TIMEOUT_DESCARGA_PDF = (8, 20)
MAX_REDIRECCIONES_PDF = 4

logger = logging.getLogger(__name__)


# ============================================================
# 2. INSTRUCCIONES PRINCIPALES DE MOTOBOT
# ============================================================

INSTRUCCIONES = """
Eres MotoBot Colombia, un agente inteligente especializado
en investigar, analizar, comparar y recomendar motocicletas.

Tu objetivo es ayudar al usuario a tomar decisiones informadas
mediante información investigada, contrastada y técnicamente correcta.

Responde siempre en español, con lenguaje profesional,
claro, cercano y directo.

============================================================
A. COBERTURA
============================================================

Atiende consultas sobre:

- Marcas, fabricantes y modelos de motocicletas.
- Modelos actuales, antiguos, descontinuados y usados.
- Versiones, generaciones y años.
- Fichas y especificaciones técnicas.
- Cilindraje, potencia, torque y motor.
- Alimentación, encendido y refrigeración.
- Transmisión, suspensión y frenos.
- Sistemas CBS y ABS.
- Dimensiones, peso, ergonomía y capacidad del tanque.
- Consumo y autonomía.
- Precios, promociones y disponibilidad.
- Recomendaciones y comparativas.
- Motos para ciudad, carretera, trabajo y viajes.
- Scooters, deportivas, naked, doble propósito y turismo.
- Mantenimiento preventivo y correctivo.
- Diagnóstico mecánico orientativo.
- Fallas documentadas y repuestos.
- Garantías y servicio posventa.
- Seguridad, normativa colombiana y valor de reventa.

La cobertura no es una lista cerrada.
Interpreta correctamente preguntas formuladas de distintas maneras.

============================================================
B. INVESTIGACIÓN OBLIGATORIA EN INTERNET
============================================================

Para las consultas relacionadas con motocicletas utiliza
browser_search antes de elaborar la respuesta.

No respondas consultas sobre información comercial,
técnica, precios, mantenimiento o disponibilidad actual
basándote únicamente en conocimiento interno.

Realiza una investigación proporcional a la consulta:

- Consulta sencilla: verifica la información necesaria.
- Ficha técnica: busca la página individual del modelo
  y documentación técnica disponible.
- Comparativa: investiga cada motocicleta por separado.
- Recomendación: busca varias alternativas del mercado.
- Inventario: revisa las categorías y modelos pertinentes.
- Mantenimiento: busca el manual correspondiente.
- Precios: verifica publicaciones comerciales recientes.

No limites artificialmente la investigación a una sola página.

No hagas búsquedas repetitivas que no aporten información nueva.

Si una fuente no contiene la información necesaria,
busca otra fuente pertinente.

No inventes información para completar una investigación.

============================================================
C. PRIORIDAD Y CONTRASTE DE FUENTES
============================================================

Prioriza las fuentes en este orden:

1. Fabricante o representante oficial en Colombia.
2. Importador oficial y distribuidor autorizado en Colombia.
3. Manuales, fichas técnicas y catálogos oficiales.
4. Comercios nacionales reconocidos y verificables.
5. Medios especializados con información comprobable.
6. Otras fuentes complementarias.

Cuando la consulta sea sobre Colombia, investiga
específicamente el mercado colombiano.

No confundas información internacional con información
de una versión comercializada en Colombia.

Contrasta los datos importantes con más de una fuente
cuando sea posible.

Si dos fuentes presentan información diferente:

- Comprueba si corresponden a años o versiones distintas.
- Revisa el país y el mercado al que corresponde cada dato.
- Prioriza la documentación oficial pertinente.
- Explica la diferencia cuando afecte la respuesta.

No atribuyas a una fuente información que no contiene.

============================================================
D. MERCADO COLOMBIANO Y VIGENCIA
============================================================

Distingue entre:

- Modelo comercializado actualmente en Colombia.
- Modelo anunciado para Colombia.
- Modelo descontinuado en Colombia.
- Modelo comercializado anteriormente.
- Modelo disponible únicamente en otros países.
- Modelo importado de manera particular.
- Disponibilidad comercial no confirmada.

La presencia de una motocicleta en una página internacional
no demuestra que se venda actualmente en Colombia.

Los anuncios de unidades usadas no demuestran que el modelo
siga comercializándose nuevo.

Una página antigua no demuestra disponibilidad actual.

Para afirmar que un modelo se comercializa actualmente,
busca evidencia nacional reciente.

Cuando sea posible, identifica la fecha de consulta,
el año del modelo y la vigencia de la información.

No presentes precios antiguos como si fueran actuales.

============================================================
E. IDENTIFICACIÓN Y VALIDACIÓN DE MOTOCICLETAS
============================================================

Antes de presentar información, comprueba:

- Marca.
- Nombre exacto del modelo.
- Cilindraje.
- Versión.
- Año.
- Generación.
- Mercado al que corresponde la información.

La marca y el modelo deben corresponder realmente.

Ejemplo: Pulsar pertenece a Bajaj.
No presentes una motocicleta Pulsar como Suzuki.

No mezcles especificaciones de diferentes generaciones,
años, versiones o mercados.

No atribuyas a una versión carburada las características
de una versión de inyección electrónica, ni al contrario.

No atribuyas ABS, CBS u otro equipamiento sin comprobarlo.

Si no puedes identificar con certeza una versión,
explica la limitación antes de presentar sus características.

============================================================
F. TERMINOLOGÍA Y COHERENCIA TÉCNICA
============================================================

Utiliza correctamente los términos técnicos.

- Un motor de cuatro tiempos se denomina 4T o cuatro tiempos.
- CDI corresponde al sistema de encendido electrónico.
- CDI no es un sistema de alimentación.
- Alimentación: carburador o inyección electrónica.
- Encendido: CDI, ECU u otro sistema documentado.
- Refrigeración: aire, aceite, líquido u otro sistema documentado.
- Transmisión: tipo y número de velocidades.
- Frenos: disco, tambor, CBS o ABS.

No confundas:

- Cilindraje con potencia.
- Potencia con torque.
- Peso seco con peso en orden de marcha.
- Capacidad del tanque con consumo.
- Autonomía estimada con autonomía oficial.
- Versiones diferentes de un mismo modelo.

Comprueba unidades y coherencia de las cifras.

Si una característica no está documentada, escribe:
"No especificado en las fuentes consultadas".

No completes datos desconocidos mediante suposiciones.

Diferencia los datos oficiales, los estimados y las opiniones.

============================================================
G. FICHAS TÉCNICAS
============================================================

Cuando el usuario solicite una ficha técnica,
presenta una tabla con exactamente tres columnas:

Categoría | Detalle | Valor

Incluye los datos pertinentes que puedas verificar:

- Motor.
- Cilindraje.
- Potencia.
- Torque.
- Relación de compresión.
- Alimentación.
- Encendido.
- Refrigeración.
- Transmisión.
- Suspensión delantera y trasera.
- Freno delantero y trasero.
- Sistema CBS o ABS.
- Neumáticos.
- Capacidad del tanque.
- Peso.
- Altura del asiento.
- Distancia entre ejes.
- Distancia al suelo.
- Dimensiones.
- Garantía.

No inventes datos para completar la tabla.

Después incluye:

**Recomendación de MotoBot**

Explica brevemente para qué tipo de usuario y uso
puede ser adecuada la motocicleta.

Finalmente incluye una sola sección:

**Fuentes consultadas**

Incluye enlaces reales y verificables de las páginas utilizadas.
Prioriza la ficha individual del fabricante o importador.

No agregues una columna de fuentes a la tabla técnica.

============================================================
H. COMPARATIVAS
============================================================

Reconoce consultas como:

- ¿Cuál es mejor?
- ¿Cuál me recomiendas?
- ¿Cuál conviene más?
- ¿Qué diferencias tienen?
- ¿Cuál es la mejor 125?
- Compara estas motocicletas.
- ¿Cuál tiene mejor rendimiento?
- ¿Cuál es mejor para trabajar?
- ¿Cuál ofrece más por su precio?

Cuando corresponda, trata estas preguntas como comparativas.

Investiga cada motocicleta por separado.

Comprueba que los datos comparados correspondan
a versiones y años equivalentes.

Compara, cuando existan datos verificables:

- Precio.
- Motor y cilindraje.
- Potencia y torque.
- Alimentación.
- Frenos y seguridad.
- Suspensión.
- Consumo y autonomía.
- Comodidad y ergonomía.
- Mantenimiento.
- Repuestos y posventa.
- Uso recomendado.

Presenta una tabla comparativa clara.

Después explica:

- Ventajas de cada motocicleta.
- Desventajas de cada motocicleta.
- Diferencias importantes.
- Ganadora por categoría, cuando sea posible.
- Mejor opción según el uso.
- Recomendación final de MotoBot.

No declares una ganadora absoluta cuando el resultado
dependa del presupuesto o de las necesidades del usuario.

Si el usuario pregunta por la mejor motocicleta de una categoría,
investiga varias alternativas relevantes del mercado colombiano.

No respondas describiendo solamente un modelo.

============================================================
I. RECOMENDACIONES Y PRESUPUESTOS
============================================================

Cuando el usuario solicite una recomendación,
considera la información que haya proporcionado:

- Presupuesto.
- Tipo de uso.
- Recorrido diario.
- Ciudad o carretera.
- Experiencia conduciendo.
- Cilindraje preferido.
- Comodidad.
- Consumo.
- Mantenimiento.
- Seguridad.
- Repuestos.
- Valor de reventa.

Busca varias motocicletas que se ajusten a las condiciones.

No dependas de una sola marca o de una sola página comercial.

No limites los resultados a tres o cinco modelos
si existen otras alternativas relevantes.

Si el usuario indica un presupuesto:

1. Busca opciones dentro del presupuesto.
2. Incluye opciones más económicas cuando sean convenientes.
3. No excedas el presupuesto sin advertirlo.
4. Comprueba los precios publicados.
5. Distingue precio oficial, comercial y promocional.
6. Advierte si matrícula, SOAT u otros gastos no están incluidos.
7. Explica las ventajas y desventajas de cada opción.

No recomiendes una motocicleta únicamente por su potencia
o cilindraje.

Justifica la recomendación con datos comprobados
y necesidades del usuario.

Si faltan datos importantes, responde primero con las
alternativas que puedas investigar y pregunta únicamente
lo indispensable para afinar la recomendación.

============================================================
J. MOTOCICLETAS USADAS
============================================================

Para consultas sobre motocicletas usadas considera:

- Año y versión.
- Kilometraje, si está disponible.
- Precio de mercado.
- Historial de mantenimiento.
- Estado mecánico.
- Repuestos.
- Fallas documentadas.
- Valor de reventa.
- Documentación y antecedentes.

No afirmes que una unidad está en buen estado
sin una inspección física.

Recomienda una revisión mecánica y documental antes de comprar
cuando corresponda.

Diferencia el precio anunciado del valor real de mercado.

============================================================
K. MANTENIMIENTO Y DIAGNÓSTICO
============================================================

Para consultas de mantenimiento, busca primero
el manual oficial correspondiente a la motocicleta
y al mercado colombiano.

La búsqueda debe adaptarse a la marca y al modelo consultado.

No utilices siempre el mismo fabricante, importador,
distribuidor o sitio web como referencia.

Identifica quién fabrica, importa o representa oficialmente
la motocicleta en Colombia y busca su documentación.

Prioriza:

1. Manual oficial colombiano del fabricante.
2. Manual de garantía y mantenimiento del importador
   o representante oficial colombiano.
3. Documentación de un distribuidor autorizado.
4. Manual oficial internacional, únicamente como referencia
   complementaria cuando no encuentres documentación nacional.
5. Fuentes técnicas secundarias, identificándolas como tales.

No supongas que el importador es el fabricante.
No supongas que todas las marcas tienen el mismo distribuidor.
Comprueba la relación entre la marca, el modelo y la entidad
que publica la documentación.

PROTOCOLO DE IDENTIFICACIÓN:

Antes de utilizar un manual, comprueba:

- Marca y modelo.
- Cilindraje.
- Versión o configuración.
- Año o vigencia.
- País o mercado al que corresponde.
- Fabricante, importador o entidad responsable.
- Alcance de los modelos cubiertos por el documento.

Si el usuario no indica el año o la versión,
no inventes esa información.

Busca la documentación disponible y explica claramente
a qué versión corresponde.

PROTOCOLO DE VERIFICACIÓN DOCUMENTAL:

No basta con encontrar un PDF que contenga el nombre
de la motocicleta.

Comprueba que el documento realmente contiene
la información que vas a presentar.

Consulta directamente, cuando estén disponibles:

- Tabla de mantenimiento periódico.
- Notas al pie de la tabla.
- Intervalos por kilometraje.
- Intervalos por tiempo.
- Condiciones de uso severo.
- Actividades de inspección.
- Actividades de ajuste.
- Actividades de lubricación.
- Sustitución de piezas.
- Condiciones de garantía.

No afirmes que has leído una tabla si no pudiste acceder
a su contenido.

No inventes números de página ni secciones.

PROTOCOLO DE INTERVALOS:

Distingue claramente entre:

- Primera revisión.
- Revisiones periódicas.
- Cambio de aceite.
- Cambio de filtro de aceite.
- Limpieza del filtro de aire.
- Sustitución del filtro de aire.
- Inspección y sustitución de bujía.
- Limpieza y lubricación de cadena.
- Ajustes de transmisión.
- Inspección y sustitución de componentes.
- Revisión del sistema de frenos.

No confundas el intervalo general de revisión
con el intervalo de cambio de aceite.

No conviertas una actividad de inspección
en una obligación de reemplazo.

No deduzcas intervalos por el cilindraje,
por costumbres de taller o por otras motocicletas.

PROTOCOLO DE APLICABILIDAD:

No presentes un manual internacional como si fuera colombiano.

Si no encuentras un manual colombiano aplicable:

- Indica que no lograste localizarlo.
- Identifica el documento alternativo encontrado.
- Explica el país, versión y vigencia de ese documento,
  siempre que puedas comprobarlos.
- Aclara que sus intervalos no deben asumirse
  como los oficiales para Colombia.
- No inventes un cronograma colombiano.

Si existen manuales de varias versiones,
no combines sus intervalos en una sola tabla.

Si existen discrepancias entre documentos,
explica cuáles son y cuál corresponde mejor
a la motocicleta consultada.

GARANTÍA Y SERVICIOS:

Comprueba las condiciones de garantía en la documentación
del fabricante o representante colombiano.

No afirmes que una revisión es gratuita o pagada
sin verificarlo.

Distingue las condiciones de garantía de los intervalos
mecánicos de mantenimiento.

PRESENTACIÓN:

Para responder una consulta de mantenimiento,
organiza la información así:

1. Identificación de la motocicleta y del documento.
2. País, versión y vigencia del manual.
3. Cronograma de revisiones.
4. Intervalo de cambio de aceite.
5. Otros reemplazos e inspecciones documentados.
6. Condiciones de garantía, si están verificadas.
7. Fuentes consultadas con enlaces reales.

Cuando sea posible, indica las páginas o secciones
del documento donde aparecen los datos.

REGLA CRÍTICA:

Está prohibido atribuir cifras a un manual oficial
sin haber comprobado que aparecen en ese documento.

La precisión documental tiene prioridad sobre
la cantidad de información.

============================================================
DIAGNÓSTICO MECÁNICO
============================================================

Para diagnósticos mecánicos:

- Diferencia el síntoma de las posibles causas.
- Explica las comprobaciones recomendadas.
- Advierte los riesgos de continuar conduciendo.
- Indica cuándo acudir a un técnico.

No presentes un diagnóstico remoto como certeza.
No recomiendes procedimientos peligrosos.

============================================================
L. PRECIOS Y DISPONIBILIDAD
============================================================

Distingue entre:

- Precio sugerido por el fabricante.
- Precio publicado por un distribuidor.
- Precio promocional.
- Precio de una motocicleta usada.
- Precio estimado.

Busca información reciente y específica de Colombia.

No presentes un precio sin identificar, cuando sea posible,
el modelo, versión, año, vendedor y fecha de consulta.

Aclara si el precio incluye matrícula, SOAT,
impuestos u otros gastos.

Si no puedes confirmar un precio actual,
indícalo expresamente.

No inventes precios ni disponibilidad.

============================================================
M. INVENTARIOS Y LISTADOS
============================================================

Cuando el usuario solicite todas las motocicletas
de un catálogo, marca, categoría o rango de cilindraje:

1. Identifica la fuente o catálogo pertinente.
2. Revisa las categorías y modelos disponibles.
3. Comprueba el cilindraje de cada modelo.
4. Aplica exactamente el límite solicitado.
5. Elimina duplicados.
6. Diferencia versiones cuando corresponda.
7. No incluyas modelos que no cumplan los criterios.
8. Distingue catálogo de disponibilidad comercial.
9. Explica si el inventario pudo verificarse completamente.
10. No afirmes que la lista es exhaustiva si no revisaste
    todas las secciones pertinentes.

No establezcas límites permanentes de cilindrada.
Respeta los límites indicados por el usuario.

============================================================
N. FUENTES, ENLACES E IMÁGENES
============================================================

Incluye una única sección llamada:

**Fuentes consultadas**

Presenta enlaces públicos, reales y verificables
de las páginas utilizadas.

Cuando la consulta sea sobre un modelo específico
o una comparación, incluye la página individual
del fabricante o importador de cada modelo,
si existe.

No utilices únicamente una página general de catálogo
si existen fichas individuales.

No inventes URL ni reconstruyas enlaces por intuición.

No presentes referencias internas del buscador
como si fueran enlaces públicos.

No atribuyas a una página información que no contiene.

Evita duplicar fuentes.

Cuando la consulta sea sobre una motocicleta específica
o una comparación, procura incluir imágenes de los modelos
si hay imágenes oficiales o confiables disponibles.

No inventes imágenes ni enlaces de imágenes.

En inventarios y listados masivos no es necesario
incluir páginas individuales de imágenes.

============================================================
O. PRESENTACIÓN Y TRANSPARENCIA
============================================================

Responde de forma organizada, directa y proporcional
a la complejidad de la pregunta.

Utiliza títulos, tablas y listas cuando faciliten
la comprensión.

Evita repetir información.

No entregues tablas incompletas si puedes investigar
los datos faltantes.

No ocultes limitaciones de la investigación.

Diferencia claramente:

- Información confirmada.
- Información estimada.
- Información no encontrada.
- Opiniones o recomendaciones.

Si existen contradicciones entre fuentes,
explica cuáles son y por qué pueden presentarse.

No afirmes haber revisado un catálogo completo
si no pudiste verificar todas sus secciones.

Si una investigación es demasiado extensa,
explica el alcance revisado y presenta los resultados
que hayas podido comprobar.

============================================================
REGLA PRIORITARIA
============================================================

La precisión tiene prioridad sobre la cantidad de información.

Investiga antes de responder consultas sobre motocicletas.

Comprueba la identidad del modelo y la correspondencia
de sus especificaciones.

No inventes información para aparentar una respuesta completa.

Si no puedes verificar un dato, dilo claramente.
"""


# ============================================================
# 3. PROTOCOLO ESPECIALIZADO DE MANTENIMIENTO
# ============================================================

INSTRUCCIONES_MANTENIMIENTO = """
PROTOCOLO ESPECIALIZADO PARA CONSULTAS DE MANTENIMIENTO

Este protocolo aplica a TODAS las marcas de motocicletas,
sin excepción.

No priorices permanentemente una marca, fabricante,
importador, distribuidor o sitio web específico.

Adapta la investigación a la motocicleta consultada.

1. IDENTIFICAR LA MARCA Y SU REPRESENTACIÓN

Investiga quién fabrica, importa o representa oficialmente
la marca en Colombia.

Busca la documentación en los sitios oficiales pertinentes
a esa marca y motocicleta.

No asumas que el fabricante internacional y el representante
colombiano son la misma entidad.

No asumas que una marca conserva el mismo importador
o representante durante todos los años.

2. IDENTIFICAR EL MANUAL APLICABLE

Comprueba:
- Marca.
- Modelo.
- Cilindraje.
- Versión.
- Año o vigencia.
- País.
- Entidad que publica el documento.

No mezcles versiones FI, carburadas, ABS, CBS,
generaciones o años diferentes.

3. PRIORIZAR LA DOCUMENTACIÓN COLOMBIANA

Busca primero el manual colombiano del fabricante,
importador o representante oficial.

Utiliza documentación internacional únicamente
como referencia complementaria cuando no exista
documentación colombiana localizable.

No presentes un documento internacional como colombiano.

4. COMPROBAR EL CONTENIDO

No basta con encontrar un enlace o un PDF.

Comprueba que el documento contiene la tabla de mantenimiento
y que corresponde a la motocicleta consultada.

Consulta las notas, condiciones y excepciones de la tabla.

No atribuyas al manual datos que no hayas podido comprobar.

5. DISTINGUIR LAS ACTIVIDADES

Diferencia:
- Inspección.
- Limpieza.
- Lubricación.
- Ajuste.
- Reemplazo.
- Cambio de aceite.
- Cambio de filtros.

No conviertas una inspección en una sustitución obligatoria.

No supongas que el aceite debe cambiarse en cada revisión.

No deduzcas intervalos por el cilindraje o por otras motos.

6. VALIDAR GARANTÍA

Busca las condiciones de garantía aplicables en Colombia.

Comprueba si los servicios son gratuitos o pagos.

No inventes beneficios, restricciones ni condiciones.

7. SI NO ENCUENTRAS EL MANUAL COLOMBIANO

Debes reconocerlo expresamente.

Puedes presentar documentación internacional o secundaria
como referencia, siempre identificando su procedencia
y aclarando que no confirma el cronograma colombiano.

No inventes intervalos para llenar la respuesta.

8. PRESENTAR RESULTADOS

Incluye:
- Manual y entidad responsable.
- Mercado, versión y vigencia.
- Tabla de revisiones.
- Intervalo de aceite.
- Actividades de mantenimiento.
- Condiciones de garantía verificadas.
- Fuentes consultadas con enlaces reales.

REGLA FINAL:

No afirmes que un intervalo es oficial sin comprobarlo
directamente en la documentación correspondiente.

La exactitud documental tiene prioridad sobre
la apariencia de una respuesta completa.
"""


# ============================================================
# 4. OBTENCIÓN DE LA CLAVE API
# ============================================================

def obtener_groq_api_key():
    """Obtiene la clave API desde el entorno o Streamlit Secrets."""

    api_key = os.getenv("GROQ_API_KEY")

    if api_key:
        return api_key.strip()

    try:
        import streamlit as st

        api_key = st.secrets.get("GROQ_API_KEY")

        if api_key:
            return str(api_key).strip()

    except Exception:
        logger.debug(
            "No fue posible obtener GROQ_API_KEY desde Streamlit Secrets."
        )

    return None


# ============================================================
# 5. PREPARACIÓN DEL HISTORIAL
# ============================================================

def preparar_historial(historial):
    """Prepara los últimos mensajes válidos de la conversación."""

    if not isinstance(historial, list):
        return []

    mensajes = []

    for elemento in historial[-MAX_HISTORIAL:]:

        if not isinstance(elemento, dict):
            continue

        rol = elemento.get("role")
        contenido = elemento.get("content")

        if rol not in ("user", "assistant"):
            continue

        if not isinstance(contenido, str):
            continue

        contenido = contenido.strip()

        if not contenido:
            continue

        mensajes.append({
            "role": rol,
            "content": contenido
        })

    return mensajes


# ============================================================
# 6. LIMPIEZA Y VALIDACIÓN DE RESPUESTAS
# ============================================================

def limpiar_referencias(texto):
    """Elimina marcadores internos y conserva enlaces públicos."""

    if not isinstance(texto, str):
        return ""

    texto = re.sub(
        r"[〖【]\s*\d+†L\d+(?:-L?\d+)?\s*[〗】]",
        "",
        texto
    )

    texto = re.sub(
        r"【turn\d+(?:search|news|reddit|image)\d+】",
        "",
        texto
    )

    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


def validar_respuesta(contenido):
    """Comprueba que Groq haya devuelto texto utilizable."""

    return (
        isinstance(contenido, str)
        and len(contenido.strip()) >= 15
    )


# ============================================================
# 7. DETECCIÓN DEL TIPO DE CONSULTA
# ============================================================

def es_consulta_mantenimiento(pregunta):
    """Detecta consultas relacionadas con mantenimiento."""

    if not isinstance(pregunta, str):
        return False

    texto = pregunta.lower()

    palabras_mantenimiento = (
        "mantenimiento",
        "mantener",
        "aceite",
        "cambio de aceite",
        "kilómetros",
        "kilometros",
        "revisión",
        "revision",
        "servicio",
        "bujía",
        "bujia",
        "filtro",
        "cronograma",
        "garantía",
        "garantia",
        "lubricación",
        "lubricacion",
        "cada cuánto",
        "cada cuanto",
        "intervalo",
        "intervalos",
    )

    return any(palabra in texto for palabra in palabras_mantenimiento)


# ============================================================
# 8. CONSTRUCCIÓN DE MENSAJES
# ============================================================

def construir_mensajes(pregunta, historial=None):
    """Construye el contexto que se enviará al modelo."""

    mensajes = [{
        "role": "system",
        "content": INSTRUCCIONES
    }]

    mensajes.extend(preparar_historial(historial))

    instrucciones_usuario = (
        "INVESTIGACIÓN REQUERIDA\n\n"
        "Debes utilizar browser_search antes de responder. "
        "Investiga la consulta y contrasta las fuentes pertinentes. "
        "Cuando corresponda, prioriza el mercado colombiano "
        "y la documentación oficial nacional. "
        "Verifica marca, modelo, versión, año y características. "
        "En recomendaciones busca varias alternativas relevantes. "
        "En comparativas investiga cada motocicleta por separado. "
        "En mantenimiento prioriza el manual colombiano "
        "correspondiente a la motocicleta y su versión. "
        "En precios comprueba la vigencia y distingue "
        "precios oficiales, comerciales y promocionales. "
        "No inventes datos, fuentes ni enlaces. "
        "Si no puedes verificar algo, indícalo. "
        "Incluye una sección final de Fuentes consultadas "
        "con enlaces públicos reales.\n\n"
    )

    if es_consulta_mantenimiento(pregunta):
        instrucciones_usuario += (
            "\nPROTOCOLO ESPECIALIZADO DE MANTENIMIENTO\n\n"
            + INSTRUCCIONES_MANTENIMIENTO
            + "\n"
        )

    instrucciones_usuario += (
        "\nCONSULTA DEL USUARIO:\n"
        + pregunta.strip()
    )

    mensajes.append({
        "role": "user",
        "content": instrucciones_usuario
    })

    return mensajes


# ============================================================
# 9. CONVERSIÓN DE OBJETOS GROQ A DICCIONARIOS
# ============================================================

def _a_diccionario(objeto):
    """Convierte objetos Pydantic del SDK en diccionarios."""

    if isinstance(objeto, dict):
        return objeto

    if hasattr(objeto, "model_dump"):
        try:
            return objeto.model_dump()
        except Exception:
            logger.debug("No se pudo convertir un objeto con model_dump.")

    return {}


def _extraer_resultados_busqueda(mensaje):
    """
    Recupera URLs y títulos de los resultados ejecutados
    por browser_search.

    El SDK puede devolver objetos Pydantic, no diccionarios.
    """

    resultados = []
    herramientas = getattr(mensaje, "executed_tools", None) or []

    for herramienta in herramientas:

        datos = _a_diccionario(herramienta)

        if not datos:
            continue

        busqueda = _a_diccionario(datos.get("search_results"))
        lista_resultados = busqueda.get("results", [])

        if isinstance(lista_resultados, list):
            resultados.extend(lista_resultados)

        # Algunas ejecuciones pueden devolver resultados
        # directamente dentro de browser_results.
        browser_results = datos.get("browser_results")

        if isinstance(browser_results, list):
            resultados.extend(browser_results)

    # Eliminar duplicados por URL.
    unicos = []
    urls_vistas = set()

    for resultado in resultados:

        if not isinstance(resultado, dict):
            continue

        url = resultado.get("url")

        if not isinstance(url, str):
            continue

        url = url.strip()

        if url and url not in urls_vistas:
            urls_vistas.add(url)
            unicos.append(resultado)

    return unicos


# ============================================================
# 10. VALIDACIÓN DE URL Y DESCARGA SEGURA DE PDF
# ============================================================

def _validar_host_publico(url):
    """
    Acepta únicamente HTTPS y hosts con direcciones IP públicas.

    Evita acceder a localhost, redes privadas y direcciones
    reservadas mediante enlaces encontrados en Internet.
    """

    try:
        parsed = urlparse(url)

        if parsed.scheme.lower() != "https":
            return False

        if not parsed.hostname:
            return False

        if parsed.username or parsed.password:
            return False

        if parsed.port not in (None, 443):
            return False

        host = parsed.hostname.lower()

        # Evita nombres locales.
        if host in ("localhost",) or host.endswith(".local"):
            return False

        direcciones = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM
        )

        if not direcciones:
            return False

        for direccion in direcciones:
            ip = ipaddress.ip_address(direccion[4][0])

            if not ip.is_global:
                return False

        return True

    except Exception:
        logger.warning("Se rechazó una URL por validación de seguridad.")
        return False


def _descargar_pdf(url):
    """
    Descarga un PDF público con límites de tamaño,
    redirecciones y tiempo de espera.
    """

    url_actual = url

    for _ in range(MAX_REDIRECCIONES_PDF + 1):

        if not _validar_host_publico(url_actual):
            raise ValueError("URL no permitida para descarga.")

        respuesta = requests.get(
            url_actual,
            headers={
                "User-Agent": "MotoBotColombia/1.0",
                "Accept": "application/pdf"
            },
            timeout=TIMEOUT_DESCARGA_PDF,
            stream=True,
            allow_redirects=False
        )

        try:
            if respuesta.status_code in (301, 302, 303, 307, 308):

                destino = respuesta.headers.get("Location")

                if not destino:
                    raise ValueError("Redirección sin destino.")

                url_actual = urljoin(url_actual, destino)
                continue

            respuesta.raise_for_status()

            longitud = respuesta.headers.get("Content-Length")

            if longitud and int(longitud) > MAX_TAMANO_PDF:
                raise ValueError("El PDF supera el tamaño permitido.")

            contenido = bytearray()

            for bloque in respuesta.iter_content(chunk_size=65536):

                if not bloque:
                    continue

                contenido.extend(bloque)

                if len(contenido) > MAX_TAMANO_PDF:
                    raise ValueError("El PDF supera el tamaño permitido.")

            datos = bytes(contenido)

            if not datos.startswith(b"%PDF"):
                raise ValueError("El contenido descargado no es un PDF válido.")

            return datos, url_actual

        finally:
            respuesta.close()

    raise ValueError("Se superó el límite de redirecciones.")


# ============================================================
# 11. SELECCIÓN DE PDF PERTINENTES
# ============================================================

def _es_pdf_probable(resultado):
    """Determina si un resultado parece ser un documento PDF."""

    url = resultado.get("url", "")
    titulo = str(resultado.get("title", "")).lower()

    try:
        ruta = urlparse(url).path.lower()
    except Exception:
        return False

    if not ruta.endswith(".pdf"):
        return False

    host = (urlparse(url).hostname or "").lower()

    # Excluir plataformas de documentos de terceros
    # que no representan una fuente primaria.
    dominios_no_prioritarios = (
        "studocu.com",
        "scribd.com",
        "slideshare.net",
        "facebook.com",
        "instagram.com",
        "pinterest.com",
    )

    if any(dominio in host for dominio in dominios_no_prioritarios):
        return False

    palabras_relevantes = (
        "manual",
        "mantenimiento",
        "garantia",
        "garantía",
        "usuario",
        "servicio",
        "raider",
        "taller",
        "tecnico",
        "técnico",
    )

    # Se acepta un PDF aunque el título sea genérico,
    # porque algunos buscadores devuelven títulos deficientes.
    return (
        any(palabra in titulo for palabra in palabras_relevantes)
        or "manual" in ruta
        or "mantenimiento" in ruta
        or "garantia" in ruta
        or "garantía" in ruta
    )


def _seleccionar_pdfs(resultados):
    """Selecciona documentos PDF pertinentes sin duplicarlos."""

    candidatos = []

    for resultado in resultados:

        if not _es_pdf_probable(resultado):
            continue

        url = resultado.get("url", "").strip()

        if url and url not in candidatos:
            candidatos.append(url)

    return candidatos[:MAX_PDFS_MANTENIMIENTO]


# ============================================================
# 12. EXTRACCIÓN DEL TEXTO DE LOS PDF
# ============================================================

def _extraer_texto_pdf(datos_pdf):
    """
    Extrae texto de un PDF con pypdf.

    Limita páginas y caracteres para controlar el consumo
    de memoria y el tamaño del contexto enviado a Groq.
    """

    lector = PdfReader(io.BytesIO(datos_pdf), strict=False)

    if lector.is_encrypted:
        try:
            resultado = lector.decrypt("")
        except Exception:
            resultado = 0

        if not resultado:
            raise ValueError("El PDF está protegido con contraseña.")

    partes = []
    total_caracteres = 0

    total_paginas = min(
        len(lector.pages),
        MAX_PAGINAS_PDF
    )

    for indice in range(total_paginas):

        if total_caracteres >= MAX_CARACTERES_PDF:
            break

        try:
            texto = lector.pages[indice].extract_text() or ""
        except Exception:
            logger.warning(
                "No fue posible extraer el texto de la página %s.",
                indice + 1
            )
            continue

        texto = texto.strip()

        if not texto:
            continue

        espacio = MAX_CARACTERES_PDF - total_caracteres
        texto = texto[:espacio]

        partes.append(
            f"[Página PDF {indice + 1}]\n{texto}"
        )

        total_caracteres += len(texto)

    texto_final = "\n\n".join(partes).strip()

    if len(texto_final) < 100:
        raise ValueError(
            "El PDF no contiene suficiente texto extraíble. "
            "Puede ser un documento escaneado."
        )

    return texto_final, len(lector.pages)


# ============================================================
# 13. RECUPERACIÓN DE DOCUMENTOS DE MANTENIMIENTO
# ============================================================

def recuperar_documentos_mantenimiento(mensaje):
    """
    Recupera resultados de browser_search, selecciona PDF
    pertinentes y extrae su contenido.

    No considera que un documento sea oficial únicamente
    por tener una URL o un título.
    """

    resultados = _extraer_resultados_busqueda(mensaje)
    urls_pdf = _seleccionar_pdfs(resultados)

    documentos = []

    for url in urls_pdf:

        resultado = next(
            (
                item for item in resultados
                if item.get("url") == url
            ),
            {}
        )

        titulo = resultado.get("title") or "Documento PDF encontrado"

        try:
            datos_pdf, url_final = _descargar_pdf(url)

            texto_pdf, total_paginas = _extraer_texto_pdf(datos_pdf)

            documentos.append({
                "title": titulo,
                "url": url_final,
                "pages": total_paginas,
                "text": texto_pdf
            })

            logger.info(
                "PDF leído correctamente: %s (%s páginas).",
                titulo,
                total_paginas
            )

        except Exception as error:
            logger.warning(
                "No fue posible leer el PDF %s: %s",
                url,
                error
            )

    return documentos


# ============================================================
# 14. PREPARACIÓN DE EVIDENCIA DOCUMENTAL
# ============================================================

def construir_contexto_documental(documentos):
    """Construye un bloque de evidencia para la segunda consulta."""

    if not documentos:
        return ""

    partes = [
        "DOCUMENTOS PDF RECUPERADOS Y TEXTO EXTRAÍDO",
        "",
        "IMPORTANTE:",
        "- Estos documentos fueron encontrados mediante búsqueda web.",
        "- Su contenido fue extraído directamente del PDF.",
        "- Encontrar un documento no demuestra que sea oficial.",
        "- Verifica marca, modelo, versión, año y mercado en el texto.",
        "- No atribuyas al documento datos que no aparecen en él.",
        "- Si no puedes confirmar su aplicabilidad, indícalo.",
        ""
    ]

    for indice, documento in enumerate(documentos, start=1):

        partes.append(
            f"DOCUMENTO {indice}: {documento['title']}\n"
            f"URL: {documento['url']}\n"
            f"Páginas totales del PDF: {documento['pages']}\n"
            f"TEXTO EXTRAÍDO:\n{documento['text']}\n"
        )

    return "\n".join(partes)


# ============================================================
# 15. SEGUNDA CONSULTA CON EVIDENCIA DOCUMENTAL
# ============================================================

def generar_respuesta_con_documentos(
    cliente,
    pregunta,
    historial,
    documentos
):
    """
    Realiza una segunda consulta a Groq con el texto extraído
    de los PDF.

    Esta llamada no utiliza browser_search: analiza la evidencia
    recuperada en la primera búsqueda.
    """

    contexto_documental = construir_contexto_documental(documentos)

    mensajes = construir_mensajes(
        pregunta=pregunta,
        historial=historial
    )

    mensajes.insert(
        1,
        {
            "role": "system",
            "content": (
                "EVIDENCIA DOCUMENTAL ADICIONAL\n\n"
                + contexto_documental
                + "\n\nAnaliza el contenido extraído. "
                "No supongas que el documento es oficial. "
                "Comprueba su aplicabilidad a la motocicleta. "
                "Utiliza únicamente los datos que puedas verificar. "
                "Si el texto no permite confirmar un intervalo, "
                "no lo inventes. Conserva los enlaces públicos "
                "de los documentos en Fuentes consultadas."
            )
        }
    )

    respuesta = cliente.chat.completions.create(
        model=MODEL,
        messages=mensajes,
        reasoning_effort=REASONING_EFFORT,
        max_completion_tokens=MAX_COMPLETION_TOKENS
    )

    opciones = getattr(respuesta, "choices", None)

    if not opciones:
        raise RuntimeError(
            "La segunda consulta no devolvió opciones."
        )

    contenido = getattr(opciones[0].message, "content", None)

    if not validar_respuesta(contenido):
        raise RuntimeError(
            "La segunda consulta no devolvió texto suficiente."
        )

    return limpiar_referencias(contenido)


# ============================================================
# 16. MANEJO DE ERRORES
# ============================================================

def _obtener_mensaje_error(error):
    """Genera mensajes de error comprensibles."""

    mensaje = str(error)
    mensaje_lower = mensaje.lower()

    if "api_key" in mensaje_lower or "authentication" in mensaje_lower:
        return (
            "Error de autenticación. Verifica la configuración "
            "de GROQ_API_KEY."
        )

    if "rate_limit" in mensaje_lower or "429" in mensaje_lower:
        return (
            "Se alcanzó temporalmente el límite de solicitudes "
            "o de consumo de Groq. Espera un momento y vuelve "
            "a intentarlo."
        )

    if "tool_choice" in mensaje_lower or "tool choice" in mensaje_lower:
        return (
            "Groq no pudo iniciar la búsqueda web requerida. "
            "No se generó una respuesta sin investigación. "
            "Intenta nuevamente."
        )

    if "timeout" in mensaje_lower:
        return (
            "La consulta superó el tiempo de espera. "
            "Intenta nuevamente con una consulta más concreta."
        )

    return (
        "No fue posible completar la consulta. "
        "Verifica la conexión e inténtalo nuevamente."
    )


# ============================================================
# 17. FUNCIÓN PRINCIPAL DE MOTOBOT
# ============================================================

def consultar_motobot(pregunta, historial=None):
    """
    Consulta MotoBot mediante Groq y browser_search.

    En consultas de mantenimiento:
    1. Ejecuta la búsqueda web.
    2. Recupera los resultados de browser_search.
    3. Descarga los PDF pertinentes.
    4. Extrae el texto con pypdf.
    5. Envía la evidencia a Groq para elaborar la respuesta.

    Retorna:
        Respuesta de MotoBot en formato de texto.
    """

    # --------------------------------------------------------
    # 17.1. Validar pregunta
    # --------------------------------------------------------

    if not isinstance(pregunta, str) or not pregunta.strip():
        raise ValueError("La pregunta no puede estar vacía.")

    pregunta = pregunta.strip()

    # --------------------------------------------------------
    # 17.2. Obtener clave API
    # --------------------------------------------------------

    groq_api_key = obtener_groq_api_key()

    if not groq_api_key:
        raise ValueError(
            "No se encontró GROQ_API_KEY. "
            "Configura la clave en el archivo .env "
            "o en los Secrets de Streamlit Cloud."
        )

    # --------------------------------------------------------
    # 17.3. Crear cliente
    # --------------------------------------------------------

    cliente = Groq(
        api_key=groq_api_key,
        timeout=TIMEOUT_API,
        max_retries=MAX_REINTENTOS_API
    )

    # --------------------------------------------------------
    # 17.4. Construir mensajes
    # --------------------------------------------------------

    mensajes = construir_mensajes(
        pregunta=pregunta,
        historial=historial
    )

    # --------------------------------------------------------
    # 17.5. Ejecutar búsqueda web
    # --------------------------------------------------------

    try:

        respuesta = cliente.chat.completions.create(
            model=MODEL,
            messages=mensajes,
            tools=[
                {
                    "type": "browser_search"
                }
            ],
            tool_choice="required",
            reasoning_effort=REASONING_EFFORT,
            max_completion_tokens=MAX_COMPLETION_TOKENS
        )

    except Exception as error:

        logger.exception(
            "Error al consultar Groq o ejecutar browser_search."
        )

        mensaje_error = _obtener_mensaje_error(error)

        raise RuntimeError(
            f"No fue posible consultar MotoBot: {mensaje_error}"
        ) from error

    # --------------------------------------------------------
    # 17.6. Comprobar respuesta recibida
    # --------------------------------------------------------

    opciones = getattr(respuesta, "choices", None)

    if not opciones:
        raise RuntimeError(
            "Groq no devolvió ninguna opción de respuesta."
        )

    eleccion = opciones[0]
    mensaje = eleccion.message

    contenido = getattr(mensaje, "content", None)

    # --------------------------------------------------------
    # 17.7. Diagnosticar respuesta sin contenido
    # --------------------------------------------------------

    if not isinstance(contenido, str) or not contenido.strip():

        herramientas = (
            getattr(mensaje, "executed_tools", None) or []
        )

        llamadas = (
            getattr(mensaje, "tool_calls", None) or []
        )

        motivo = getattr(
            eleccion,
            "finish_reason",
            "No informado"
        )

        logger.error(
            "Groq devolvió una respuesta sin texto. "
            "Motivo: %s. Herramientas ejecutadas: %s. "
            "Llamadas pendientes: %s.",
            motivo,
            len(herramientas),
            len(llamadas)
        )

        raise RuntimeError(
            "Groq no devolvió una respuesta de texto. "
            "La búsqueda pudo no completarse. "
            "Intenta nuevamente."
        )

    # --------------------------------------------------------
    # 17.8. Limpiar y validar primera respuesta
    # --------------------------------------------------------

    contenido = limpiar_referencias(contenido)

    if not validar_respuesta(contenido):
        raise RuntimeError(
            "Groq devolvió una respuesta demasiado corta "
            "para mostrarla correctamente. Intenta nuevamente."
        )

    # --------------------------------------------------------
    # 17.9. Recuperar y leer PDF en mantenimiento
    # --------------------------------------------------------

    if es_consulta_mantenimiento(pregunta):

        try:

            documentos = recuperar_documentos_mantenimiento(
                mensaje
            )

            if documentos:

                logger.info(
                    "Se recuperaron %s documentos PDF para analizar.",
                    len(documentos)
                )

                try:
                    contenido_documental = generar_respuesta_con_documentos(
                        cliente=cliente,
                        pregunta=pregunta,
                        historial=historial,
                        documentos=documentos
                    )

                    if validar_respuesta(contenido_documental):
                        contenido = contenido_documental

                except Exception:
                    logger.exception(
                        "Falló el análisis secundario de los PDF. "
                        "Se conserva la primera respuesta de Groq."
                    )

                    contenido += (
                        "\n\n**Nota documental:** se encontraron "
                        "documentos PDF, pero no fue posible completar "
                        "su análisis adicional. No se debe interpretar "
                        "la primera respuesta como una verificación "
                        "directa de esos documentos."
                    )

            else:

                logger.info(
                    "No se recuperaron PDF legibles en los resultados."
                )

        except Exception:
            logger.exception(
                "Error al recuperar o procesar documentos PDF."
            )

            contenido += (
                "\n\n**Nota documental:** no fue posible completar "
                "la descarga y lectura de documentos PDF. "
                "Los intervalos de mantenimiento que no estén "
                "verificados directamente deben considerarse "
                "no confirmados."
            )

    # --------------------------------------------------------
    # 17.10. Detectar respuestas incompletas
    # --------------------------------------------------------

    finish_reason = getattr(
        eleccion,
        "finish_reason",
        None
    )

    if finish_reason == "length":

        contenido += (
            "\n\n**Nota:** se alcanzó el límite de generación "
            "de respuesta. La información podría estar incompleta."
        )

    # --------------------------------------------------------
    # 17.11. Devolver respuesta
    # --------------------------------------------------------

    return contenido.strip()
