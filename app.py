
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import streamlit as st
from bs4 import BeautifulSoup

from services.groq_service import consultar_motobot


# ============================================================
# 1. CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="MotoBot Colombia",
    page_icon="🏍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

RUTA_IMAGEN = Path(__file__).parent / "assets" / "motobot_hero.png"


# ============================================================
# 2. ESTILOS VISUALES
# ============================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');

:root {
    --bg: #081321;
    --panel: #101f32;
    --panel2: #172a40;
    --text: #f4f7fb;
    --muted: #aebdd0;
    --orange: #ff7847;
    --border: rgba(155,180,210,.22);
}

/* ------------------------------------------------
   FONDO GENERAL
------------------------------------------------ */

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"] {
    background: #081321 !important;
    color: var(--text) !important;
    font-family: 'DM Sans', sans-serif !important;
}

.stApp {
    background:
        radial-gradient(
            ellipse at 85% 0%,
            rgba(30,75,120,.20),
            transparent 35%
        ),
        #081321 !important;
}

[data-testid="stHeader"] {
    background: #081321 !important;
}

[data-testid="stMainBlockContainer"] {
    max-width: 1450px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}

/* ------------------------------------------------
   BARRA LATERAL
------------------------------------------------ */

[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg,
        #101f32,
        #091321
    ) !important;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
    color: #edf3fa;
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #b7c5d6 !important;
}

/* Texto descriptivo de la barra lateral */

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {
    color: #c3d0df !important;
    font-size: 1rem !important;
    line-height: 1.5 !important;
}

/* Avisos de la barra lateral */

[data-testid="stSidebar"] [data-testid="stAlert"],
[data-testid="stSidebar"] [data-testid="stAlert"] > div {
    background: #142a40 !important;
    border: 1px solid #294966 !important;
    border-radius: 14px !important;
}

[data-testid="stSidebar"] [data-testid="stAlert"] p,
[data-testid="stSidebar"] [data-testid="stAlert"] div {
    color: #e7f0fa !important;
}

/* ------------------------------------------------
   IMAGEN PRINCIPAL
------------------------------------------------ */

[data-testid="stImage"] img {
    border-radius: 16px;
}

.hero-caption {
    color: #aebdd0;
    font-size: .82rem;
    margin-top: .35rem;
}

/* ------------------------------------------------
   TEXTOS Y SECCIONES
------------------------------------------------ */

h1, h2, h3, h4, p, label {
    color: var(--text);
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li {
    color: #d8e2ed;
}

.section-kicker {
    color: #ff9a72 !important;
    font-size: 1.05rem;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
    margin-top: 1.5rem;
    margin-bottom: .65rem;
}

.section-description {
    color: #aebdd0 !important;
    font-size: 1.08rem;
    margin-bottom: 1rem;
}

/* ------------------------------------------------
   BOTONES DE LA INTERFAZ
------------------------------------------------ */

div.stButton > button {
    width: 100%;
    min-height: 3.1rem;
    border-radius: 13px;
    border: 1px solid rgba(155,180,210,.28);
    background: #172a40;
    color: #f5f7fb !important;
    font-weight: 700;
    transition: all .18s ease;
}

/* Botones principales de funciones */

[data-testid="stHorizontalBlock"] [data-testid="column"] div.stButton > button {
    min-height: 3.7rem;
    font-size: 1.08rem;
}

div.stButton > button:hover {
    background: #213a55 !important;
    border-color: #ff895b !important;
    color: #ffffff !important;
}

div.stButton > button[kind="primary"] {
    background: linear-gradient(
        100deg,
        #e95e32,
        #ff895b
    ) !important;
    border-color: #ff9a72 !important;
    color: #ffffff !important;
}

/* ------------------------------------------------
   MENSAJES DEL CHAT
------------------------------------------------ */

[data-testid="stChatMessage"] {
    background: #101f32 !important;
    border: 1px solid var(--border) !important;
    border-radius: 17px !important;
    padding: .9rem 1rem !important;
    margin-bottom: .8rem;
}

/* Texto de las respuestas */

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"],
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] span,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] strong,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] em,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] blockquote,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h1,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h2,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h3,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h4,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h5,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] h6,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th {
    color: #f4f7fb !important;
}

/* Enlaces de las fuentes */

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] a {
    color: #ff9a72 !important;
    text-decoration: underline;
}

/* Tablas */

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] table {
    color: #f4f7fb !important;
    border-color: rgba(155,180,210,.30) !important;
}

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] th,
[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] td {
    border-color: rgba(155,180,210,.30) !important;
}

/* Código dentro de las respuestas */

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] code {
    color: #ffd2bd !important;
    background: #172a40 !important;
}

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] pre {
    background: #091725 !important;
    border: 1px solid var(--border) !important;
}

[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] pre code {
    color: #f4f7fb !important;
    background: transparent !important;
}

/* ------------------------------------------------
   CAMPO DE PREGUNTA
------------------------------------------------ */

/* Contenedor inferior */

[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottomBlockContainer"] {
    background: #081321 !important;
}

/* Caja exterior */

[data-testid="stChatInput"],
[data-testid="stChatInput"] > div {
    background: #172a40 !important;
    border: 1px solid rgba(255,120,71,.70) !important;
    border-radius: 17px !important;
    box-shadow: 0 8px 25px rgba(0,0,0,.22) !important;
}

/* Contenedor interno */

[data-testid="stChatInput"] [data-baseweb="textarea"],
[data-testid="stChatInput"] [data-baseweb="base-input"],
[data-testid="stChatInput"] div {
    background-color: transparent !important;
}

/* Texto escrito por el usuario */

[data-testid="stChatInput"] textarea,
[data-testid="stChatInput"] textarea:focus {
    background: transparent !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    caret-color: #ff895b !important;
    opacity: 1 !important;
}

/* Texto de ejemplo */

[data-testid="stChatInput"] textarea::placeholder {
    color: #b9c7d7 !important;
    -webkit-text-fill-color: #b9c7d7 !important;
    opacity: 1 !important;
}

/* Botón de enviar */

[data-testid="stChatInput"] button {
    background: #ff7847 !important;
    color: #ffffff !important;
    border-radius: 50% !important;
}

/* Al enfocar el campo */

[data-testid="stChatInput"]:focus-within {
    border-color: #ff9a72 !important;
    box-shadow: 0 0 0 2px rgba(255,120,71,.18) !important;
}

/* ------------------------------------------------
   AVISOS Y MENSAJES GLOBALES
------------------------------------------------ */

/* Fondo azul para st.error, st.warning y st.info */

[data-testid="stAlert"],
[data-testid="stAlert"] > div,
[data-testid="stAlert"] [data-testid="stAlertContent"] {
    background: #142a40 !important;
    background-color: #142a40 !important;
    border: 1px solid #294966 !important;
    border-radius: 13px !important;
}

/* Texto de los avisos */

[data-testid="stAlert"] p,
[data-testid="stAlert"] span,
[data-testid="stAlert"] div {
    color: #e7f0fa !important;
}

/* Iconos de los avisos */

[data-testid="stAlert"] svg {
    color: #ff9a72 !important;
}

/* ------------------------------------------------
   EXPANSORES Y OTROS COMPONENTES
------------------------------------------------ */

[data-testid="stExpander"] {
    background: #101f32 !important;
    border: 1px solid var(--border) !important;
    border-radius: 13px !important;
}

[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {
    color: #edf3fa !important;
}

hr {
    border-color: var(--border) !important;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 3. ESTADO DE LA APLICACIÓN
# ============================================================

if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

if "modo_consulta" not in st.session_state:
    st.session_state.modo_consulta = "Libre"


# ============================================================
# 4. FUNCIONES DE CONTROL DE LA CONVERSACIÓN
# ============================================================

def seleccionar_modo(modo):
    st.session_state.modo_consulta = modo


def quitar_modo():
    st.session_state.modo_consulta = "Libre"


def nueva_conversacion():
    st.session_state.mensajes = []
    st.session_state.modo_consulta = "Libre"


# ============================================================
# 5. FUNCIONES DE RECUPERACIÓN Y VISUALIZACIÓN DE IMÁGENES
# ============================================================

@st.cache_data(ttl=3600, max_entries=64, show_spinner=False)
def obtener_imagen_de_pagina(url):

    try:
        respuesta = requests.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; MotoBotColombia/1.0)"
            },
            timeout=8,
        )

        respuesta.raise_for_status()

        if "html" not in respuesta.headers.get(
            "Content-Type", ""
        ).lower():
            return None

        soup = BeautifulSoup(respuesta.text, "html.parser")

        titulo = ""

        etiqueta = soup.find(
            "meta",
            attrs={"property": "og:title"}
        )

        if etiqueta:
            titulo = etiqueta.get("content", "")

        if not titulo and soup.title:
            titulo = soup.title.get_text(" ", strip=True)

        imagen = None

        for selector in (
            {"property": "og:image"},
            {"name": "twitter:image"},
            {"property": "og:image:url"},
        ):

            etiqueta = soup.find("meta", attrs=selector)

            if etiqueta and etiqueta.get("content"):
                imagen = etiqueta["content"]
                break

        if not imagen:
            return None

        imagen = urljoin(respuesta.url, imagen)

        if urlparse(imagen).scheme not in ("http", "https"):
            return None

        verificacion = requests.get(
            imagen,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
            stream=True,
        )

        tipo = verificacion.headers.get("Content-Type", "").lower()
        verificacion.close()

        if not tipo.startswith("image/"):
            return None

        return {
            "url": imagen,
            "titulo": titulo or urlparse(url).netloc,
        }

    except requests.RequestException:
        return None

    except Exception:
        return None


def extraer_enlaces_de_fuentes(respuesta):

    coincidencia = re.search(
        r"(?:\*\*)?Fuentes consultadas(?:\*\*)?\s*([\s\S]*)$",
        respuesta,
        flags=re.IGNORECASE,
    )

    if not coincidencia:
        return []

    enlaces = re.findall(
        r"https?://[^\s)\]>]+",
        coincidencia.group(1),
    )

    resultado = []
    vistos = set()

    for enlace in enlaces:

        enlace = enlace.rstrip(".,;:!?\"'`)")

        if enlace.startswith("https://") and enlace not in vistos:
            vistos.add(enlace)
            resultado.append(enlace)

    return resultado


def tipo_de_consulta(pregunta):

    texto = pregunta.lower()

    patrones_masivos = (
        r"\btodas\b",
        r"\btodos\b",
        r"cat[aá]logo",
        r"inventario",
        r"listado",
        r"lista completa",
        r"hasta\s*\d+\s*cc",
        r"identifica (las )?motocicletas",
    )

    if any(re.search(p, texto) for p in patrones_masivos):
        return "masiva"

    patrones_comparacion = (
        r"compar",
        r"\bvs\b",
        r"versus",
        r"diferencias",
        r"cu[aá]l es mejor",
        r"cu[aá]l conviene",
        r"mejor moto",
        r"entre .+ y .+",
    )

    if any(re.search(p, texto) for p in patrones_comparacion):
        return "comparacion"

    patrones_individual = (
        r"ficha t[eé]cnica",
        r"caracter[ií]sticas",
        r"especificaciones",
        r"informaci[oó]n de",
        r"qu[eé] tal es",
        r"consumo de",
        r"precio de",
    )

    if any(re.search(p, texto) for p in patrones_individual):
        return "individual"

    return "ninguna"


def recuperar_imagenes(pregunta, respuesta):

    tipo = tipo_de_consulta(pregunta)

    if tipo not in ("individual", "comparacion"):
        return []

    enlaces = extraer_enlaces_de_fuentes(respuesta)

    if not enlaces:
        return []

    limite = 4 if tipo == "comparacion" else 1

    imagenes = []
    urls_vistas = set()

    for enlace in enlaces[:8]:

        dato = obtener_imagen_de_pagina(enlace)

        if not dato:
            continue

        if dato["url"] in urls_vistas:
            continue

        urls_vistas.add(dato["url"])
        imagenes.append(dato)

        if len(imagenes) >= limite:
            break

    return imagenes


def mostrar_imagenes(imagenes):

    if not imagenes:
        return

    st.markdown("#### Imágenes encontradas en las fuentes")

    columnas = st.columns(min(len(imagenes), 3))

    for indice, dato in enumerate(imagenes):

        with columnas[indice % len(columnas)]:

            st.image(
                dato["url"],
                use_container_width=True,
            )

            st.caption(dato["titulo"])


# ============================================================
# 6. INSTRUCCIONES DE LOS MODOS DE CONSULTA
# ============================================================

def instrucciones_del_modo(modo):

    instrucciones = {

        "Investigar": (
            "ENFOQUE: INVESTIGACIÓN. "
            "Responde directamente sobre el modelo, marca, versión, año o tema solicitado. "
            "Prioriza datos verificables y fuentes oficiales. "
            "No agregues comparaciones o recomendaciones si no fueron solicitadas."
        ),

        "Comparar": (
            "ENFOQUE: COMPARACIÓN. "
            "Identifica todas las motocicletas mencionadas. "
            "Compáralas con criterios equivalentes y presenta diferencias, ventajas, "
            "desventajas y una conclusión. No omitas modelos."
        ),

        "Recomendar": (
            "ENFOQUE: RECOMENDACIÓN. "
            "Concéntrate en seleccionar opciones adecuadas al presupuesto, necesidades "
            "y tipo de uso del usuario. Si falta un dato esencial, pregunta por él."
        ),

        "Asesorar": (
            "ENFOQUE: ASESORÍA. "
            "Atiende preguntas sobre mantenimiento, diagnóstico orientativo, repuestos, "
            "seguridad o normativa. Distingue información confirmada de orientación general."
        ),
    }

    return instrucciones.get(modo, "")


# ============================================================
# 7. PRESENTACIÓN DE LA BARRA LATERAL
# ============================================================

with st.sidebar:

    st.markdown("## 🏍️ MotoBot Colombia")

    st.caption(
        "Tu asistente para investigar el mercado colombiano de motocicletas."
    )

    st.divider()

    st.markdown("### Especialidades")

    st.markdown("""
    - 🔎 Investigación de modelos y fichas técnicas.
    - ⚖️ Comparación de motocicletas.
    - 🧭 Recomendaciones de compra.
    - 🔧 Mantenimiento, repuestos y diagnóstico.
    """)

    st.divider()

    st.button(
        "＋ Nueva conversación",
        type="primary",
        use_container_width=True,
        on_click=nueva_conversacion,
    )

    st.divider()

    with st.container(border=True):

        st.markdown("**Información de MotoBot**")

        st.markdown(
            "MotoBot investiga información disponible en Internet. "
            "Verifica precios y disponibilidad con el distribuidor."
        )

    st.caption("MotoBot Colombia · Asistente en evolución")


# ============================================================
# 8. PRESENTACIÓN DE LA IMAGEN PRINCIPAL
# ============================================================

if RUTA_IMAGEN.exists():

    st.image(
        str(RUTA_IMAGEN),
        use_container_width=True,
    )

else:

    st.warning(
        "No se encontró la imagen del encabezado. "
        "Guarda motobot_hero.png dentro de la carpeta assets."
    )


# ============================================================
# 9. PRESENTACIÓN DE LAS FUNCIONES PRINCIPALES
# ============================================================

st.markdown(
    '<div class="section-kicker">⚡ SELECCIONA EL TIPO DE AYUDA</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="section-description">'
    'Selecciona una función para orientar la respuesta del agente.'
    '</div>',
    unsafe_allow_html=True,
)

modos = [
    ("Investigar", "🔎 Investigar", "Fichas técnicas, modelos, versiones y años."),
    ("Comparar", "⚖️ Comparar", "Diferencias, ventajas y desventajas."),
    ("Recomendar", "🧭 Recomendar", "Opciones según presupuesto y tipo de uso."),
    ("Asesorar", "🔧 Asesorar", "Mantenimiento, repuestos y diagnóstico."),
]

columnas = st.columns(4)

for indice, (modo, etiqueta, descripcion) in enumerate(modos):

    with columnas[indice]:

        st.button(
            etiqueta,
            key=f"modo_{modo}",
            type=(
                "primary"
                if st.session_state.modo_consulta == modo
                else "secondary"
            ),
            use_container_width=True,
            on_click=seleccionar_modo,
            args=(modo,),
        )

        st.caption(descripcion)


# Indicador de función seleccionada

if st.session_state.modo_consulta != "Libre":

    with st.container(border=True):

        st.markdown(
            f"**🏍️ Enfoque seleccionado: {st.session_state.modo_consulta}**"
        )

        st.caption(
            "La consulta se centrará en esta función."
        )

    st.button(
        "✕ Quitar selección y usar consulta libre",
        key="quitar_modo",
        on_click=quitar_modo,
    )


# ============================================================
# 10. EJEMPLOS DE CONSULTA
# ============================================================

if not st.session_state.mensajes:

    st.markdown(
        '<h3 style="color:#ff7847; font-size:15px; margin-bottom:5px;">'
        '💡 ¿QUÉ QUIERES CONSULTAR?</h3>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):

        st.markdown("""
        - **Ficha técnica:** ¿Cuáles son las características de la AKT NKD 125 modelo 2027?

        - **Comparación:** ¿Qué diferencias hay entre la Yamaha FZ 2.0 y la Suzuki Gixxer 150?

        - **Recomendación:** Recomiéndame una moto para trabajar en ciudad.

        - **Asesoría:** ¿Qué mantenimiento necesita una motocicleta de 150 cc?
        """)

    st.caption(
        "También puedes escribir cualquier otra pregunta. "
        "Si no seleccionas una función, MotoBot responderá en modo libre."
    )


# ============================================================
# 11. HISTORIAL DE CONVERSACIÓN
# ============================================================

for mensaje in st.session_state.mensajes:

    with st.chat_message(mensaje["role"]):

        st.markdown(mensaje["content"])

        if mensaje["role"] == "assistant":
            mostrar_imagenes(mensaje.get("images", []))


# ============================================================
# 12. CAMPO DE PREGUNTA
# ============================================================

pregunta = st.chat_input(
    "Escribe tu pregunta aquí...",
    key="entrada_chat",
)


# ============================================================
# 13. PROCESAMIENTO DE CONSULTAS Y MANEJO DE ERRORES
# ============================================================

if pregunta:

    modo_actual = st.session_state.modo_consulta

    st.session_state.mensajes.append({
        "role": "user",
        "content": pregunta,
    })

    with st.chat_message("user"):

        if modo_actual != "Libre":
            st.caption(f"Enfoque: {modo_actual}")

        st.markdown(pregunta)

    with st.chat_message("assistant"):

        try:

            pregunta_agente = pregunta

            instruccion = instrucciones_del_modo(modo_actual)

            if instruccion:

                pregunta_agente = (
                    f"{instruccion}\n\n"
                    f"PREGUNTA DEL USUARIO:\n{pregunta}"
                )

            with st.spinner(
                "MotoBot está investigando en Internet..."
            ):

                historial = st.session_state.mensajes[:-1]

                respuesta = consultar_motobot(
                    pregunta_agente,
                    historial,
                )

            if respuesta and respuesta.strip():

                st.markdown(respuesta)

                imagenes = recuperar_imagenes(
                    pregunta,
                    respuesta,
                )

                mostrar_imagenes(imagenes)

                st.session_state.mensajes.append({
                    "role": "assistant",
                    "content": respuesta,
                    "images": imagenes,
                })

            else:

                st.warning(
                    "No se recibió una respuesta del servicio de inteligencia artificial."
                )

                st.session_state.mensajes.pop()

        except Exception as error:

            tipo_error = type(error).__name__
            detalle_error = str(error)

            if (
                tipo_error == "RateLimitError"
                or "rate_limit_exceeded" in detalle_error
                or "Error code: 429" in detalle_error
            ):

                st.warning(
                    "MotoBot alcanzó temporalmente el límite de consumo de Groq."
                )

                st.info(
                    "Espera el tiempo indicado por Groq y vuelve a realizar la consulta."
                )

            else:

                st.error(
                    "No fue posible completar la consulta."
                )

            with st.expander("Detalle técnico del error"):

                st.code(tipo_error)
                st.code(detalle_error)

            if (
                st.session_state.mensajes
                and st.session_state.mensajes[-1]["role"] == "user"
            ):

                st.session_state.mensajes.pop()


# ============================================================
# 14. PIE DE PÁGINA
# ============================================================

st.divider()

st.caption(
    "MotoBot Colombia | Investigación y recomendación "
    "de motocicletas para el mercado colombiano."
)
    