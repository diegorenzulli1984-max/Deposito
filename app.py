import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from supabase import create_client, Client
import io
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Stock y Depósito", page_icon="📦", layout="wide")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def iniciar_conexion():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = iniciar_conexion()

# --- LISTAS MAESTRAS ---
ESTADOS_PERMITIDOS = ["Nuevo", "Usado", "A revisar", "Baja", "Reciclaje"]
MODULOS_PERMITIDOS = [
    "Entretenimiento",
    "Capacitación",
    "Microcine",
    "Robótica",
    "Cartelería",
    "Impresión 3D",
    "Mobiliario",
    "General",
]

# --- FUNCIONES DE DATOS ---
def obtener_inventario():
    res = supabase.table("inventario_deposito").select("*").execute()
    df = pd.DataFrame(res.data)
    if not df.empty and "modulo" not in df.columns:
        df["modulo"] = "General"
    elif not df.empty:
        df["modulo"] = df["modulo"].fillna("General")
    return df

def obtener_usuarios():
    usuarios_base = [
        {"usuario": "admin", "clave": "Stock2026!", "rol": "Administrador", "nombre": "Responsable de Área"}
    ]
    try:
        res = supabase.table("usuarios_stock").select("*").execute()
        if res.data:
            for u in res.data:
                if u["usuario"] != "admin":
                    usuarios_base.append(u)
    except Exception:
        pass
    return usuarios_base

def obtener_glosario():
    try:
        res = supabase.table("glosario_codigos").select("*").execute()
        if res.data:
            return pd.DataFrame(res.data)
    except Exception:
        pass
    return pd.DataFrame(columns=["codigo", "articulo", "modulo", "descripcion"])

def generar_pdf_remito(cliente, serie, cantidad, obs, articulo_nombre):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.setFillColorRGB(0.12, 0.23, 0.54)
    p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL")

    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.drawString(50, 675, f"Cliente / Receptor de la entrega: {cliente}")
    p.drawString(50, 650, f"Artículo Despachado: {articulo_nombre}")
    p.drawString(50, 625, f"Número de Serie: {serie}")
    p.drawString(50, 600, f"Cantidad: {cantidad} unidades")
    p.drawString(50, 575, f"Observaciones: {obs}")

    p.setLineWidth(1)
    p.line(50, 470, 250, 470)
    p.drawString(50, 450, "Firma del Receptor")

    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

def generar_excel_backup(df_inv, df_glosario, df_usuarios):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_inv.to_excel(writer, sheet_name="Inventario_Actual", index=False)
        df_glosario.to_excel(writer, sheet_name="Glosario_Codigos", index=False)
        if not df_usuarios.empty:
            df_u_seguro = df_usuarios.drop(columns=["clave"], errors="ignore")
            df_u_seguro.to_excel(writer, sheet_name="Usuarios_Registrados", index=False)
    buffer.seek(0)
    return buffer.getvalue()

# --- SISTEMA DE LOGUEO ---
if "usuario_actual" not in st.session_state:
    st.session_state["usuario_actual"] = None

if st.session_state["usuario_actual"] is None:
    st.title("🔐 Acceso al Sistema de Control de Stock")
    st.markdown("Ingresá tus credenciales asignadas por el responsable de área.")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            user_input = st.text_input("Usuario").strip()
            pass_input = st.text_input("Contraseña", type="password").strip()
            btn_login = st.form_submit_button("Ingresar", use_container_width=True)

            if btn_login:
                lista_usuarios = obtener_usuarios()
                encontrado = next(
                    (u for u in lista_usuarios if u["usuario"] == user_input and u["clave"] == pass_input),
                    None,
                )
                if encontrado:
                    st.session_state["usuario_actual"] = encontrado
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    st.stop()

# --- DATOS DE SESIÓN ACTIVA ---
usuario = st.session_state["usuario_actual"]
rol = usuario["rol"]

st.sidebar.markdown(f"👤 **{usuario.get('nombre', usuario['usuario'])}**")
st.sidebar.caption(f"Rol: **{rol}**")
if st.sidebar.button("Cerrar Sesión", use_container_width=True):
    st.session_state["usuario_actual"] = None
    st.rerun()
st.sidebar.divider()

# --- MENÚ SEGÚN ROL ---
if rol == "Revisor":
    menu = ["📊 Tablero e Inventario", "🤖 Asistente MIA (Consultas)", "📖 Glosario de Códigos"]
elif rol == "Stock":
    menu = [
        "📊 Tablero e Inventario",
        "➕ Carga / Inserción de Stock",
        "📤 Entregas y Remitos",
        "✏️ Editar / Actualizar Stock",
        "🤖 Asistente MIA (Consultas)",
        "📖 Glosario de Códigos",
    ]
else:
    menu = [
        "📊 Tablero e Inventario",
        "➕ Carga / Inserción de Stock",
        "📤 Entregas y Remitos",
        "✏️ Editar / Actualizar Stock",
        "🤖 Asistente MIA (Consultas)",
        "📖 Glosario de Códigos",
        "💾 Backup Oficina",
        "👥 Administrar Usuarios",
    ]

eleccion = st.sidebar.radio("Navegación", menu)

# ==============================================================================
# 1. TABLERO E INVENTARIO
# ==============================================================================
if eleccion == "📊 Tablero e Inventario":
    st.title("📦 Inventario General de Depósito")
    df = obtener_inventario()

    if df.empty:
        st.info("No hay artículos cargados todavía en el inventario.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Artículos Registrados", len(df))
        c2.metric("Unidades Totales", int(df["cantidad"].sum()))
        c3.metric("Módulos Activos", df["modulo"].nunique())
        a_revisar = len(df[df["estado"].isin(["A revisar", "Baja"])])
        c4.metric("A revisar / Baja", a_revisar)

        st.divider()
        f1, f2, f3 = st.columns(3)
        filtro_mod = f1.selectbox("Filtrar por Módulo:", ["Todos"] + MODULOS_PERMITIDOS)
        filtro_est = f2.selectbox("Filtrar por Estado:", ["Todos"] + ESTADOS_PERMITIDOS)
        busqueda = f3.text_input("Buscar por Serie o Artículo:")

        df_filtrado = df.copy()
        if filtro_mod != "Todos":
            df_filtrado = df_filtrado[df_filtrado["modulo"] == filtro_mod]
        if filtro_est != "Todos":
            df_filtrado = df_filtrado[df_filtrado["estado"] == filtro_est]
        if busqueda:
            mask = df_filtrado.astype(str).apply(lambda x: x.str.contains(busqueda, case=False, na=False)).any(axis=1)
            df_filtrado = df_filtrado[mask]

        st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

# ==============================================================================
# 2. CARGA / INSERCIÓN DE STOCK (CON COLUMNA MÓDULO)
# ==============================================================================
elif eleccion == "➕ Carga / Inserción de Stock":
    st.title("➕ Carga / Inserción de Stock")
    with st.form("form_carga_stock", clear_on_submit=True):
        col1, col2 = st.columns(2)
        cod = col1.text_input("Número de Serie / Código *:")
        nom = col2.text_input("Nombre del Artículo *:")
        mod = col1.selectbox("Módulo *:", MODULOS_PERMITIDOS)
        cat = col2.text_input("Categoría:")
        est = col1.selectbox("Estado en Depósito:", ESTADOS_PERMITIDOS)
        cant = col2.number_input("Cantidad Inicial:", min_value=1, value=1, step=1)

        submitted = st.form_submit_button("Guardar Artículo en Stock", use_container_width=True)
        if submitted:
            if not cod.strip() or not nom.strip():
                st.error("El Número de Serie y el Nombre del Artículo son obligatorios.")
            else:
                existe = supabase.table("inventario_deposito").select("numero_serie").eq("numero_serie", cod.strip()).execute()
                if existe.data:
                    st.warning("Ese Número de Serie ya existe. Usá la pestaña 'Editar / Actualizar Stock' para sumar unidades.")
                else:
                    nuevo_item = {
                        "numero_serie": cod.strip(),
                        "articulo": nom.strip(),
                        "modulo": mod,
                        "categoria": cat.strip(),
                        "estado": est,
                        "cantidad": int(cant),
                    }
                    supabase.table("inventario_deposito").insert(nuevo_item).execute()
                    st.success(f"✅ Artículo '{nom}' cargado correctamente en el módulo **{mod}**.")

# ==============================================================================
# 3. ENTREGAS Y REMITOS
# ==============================================================================
elif eleccion == "📤 Entregas y Remitos":
    st.title("📤 Despacho de Mercadería y Remitos")
    with st.form("form_entrega"):
        cliente = st.text_input("Cliente / Receptor de la entrega:")
        codigo_scan = st.text_input("Número de Serie escaneado o ingresado:")
        cantidad_entrega = st.number_input("Cantidad a entregar:", min_value=1, value=1, step=1)
        observaciones = st.text_area("Observaciones:")
        btn_entregar = st.form_submit_button("Confirmar Entrega y Generar Remito", use_container_width=True)

        if btn_entregar:
            if not cliente.strip() or not codigo_scan.strip():
                st.error("Completá el receptor y el número de serie.")
            else:
