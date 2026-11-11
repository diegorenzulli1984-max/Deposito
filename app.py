import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from supabase import create_client, Client
import io

# 🔑 CONEXIÓN ESTABLECIDA CON TU BASE DE DATOS EN LA NUBE:
SUPABASE_URL = "https://supabase.co"
SUPABASE_KEY = "sb_publishable_WNWNgvGer-DBYdmNmfislw_rzj1b-x6"

@st.cache_resource
def iniciar_conexion():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception:
        return None

supabase = iniciar_conexion()

st.set_page_config(page_title="Control de Stock", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; }
    h1 { color: #1E3A8A; font-family: 'Helvetica Neue', sans-serif; }
    .metric-value { font-size: 2.5rem; font-weight: bold; color: #10B981; }
    .metric-label { font-size: 1rem; color: #4B5563; }
    .detalle-box { padding: 1.5rem; border-left: 5px solid #1E3A8A; background-color: #F3F4F6; margin-top: 1rem; border-radius: 4px; }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Control de Stock - Depósito Conectado")

menu = ["📊 Panel de Informes", "🚚 Emitir Remito de Entrega", "➕ Alta/Modificación de Artículos"]
eleccion = st.sidebar.radio("Navegación", menu)

def generar_pdf_remito(cliente, serie, cantidad, obs, articulo_nombre):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.setFillColorRGB(0.12, 0.23, 0.54)
    p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL")
    
    p.setFont("Helvetica", 12)
    p.setFillColorRGB(0, 0, 0)
    p.drawString(50, 700, f"Cliente / Receptor de la entrega: {cliente}")
    p.drawString(50, 670, f"Articulo Despachado: {articulo_nombre}")
    p.drawString(50, 640, f"Numero de Serie: {serie}")
    p.drawString(50, 610, f"Cantidad: {cantidad} unidades")
    p.drawString(50, 580, f"Observaciones: {obs}")
    
    p.setLineWidth(1)
    p.line(50, 480, 250, 480)
    p.drawString(50, 460, "Firma del Receptor")
    
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer.getvalue()

estados_permitidos = ["Nuevo", "Usado", "Baja", "Reciclaje"]

def obtener_inventario_real():
    columnas_vacias = ["Número de Serie", "Artículo", "Categoría", "Estado", "Cantidad", "Ubicación"]
    if supabase is None:
        return pd.DataFrame(columns=columnas_vacias)
    try:
        res = supabase.table("inventario_deposito").select("*").execute()
        if not res.data:
            return pd.DataFrame(columns=columnas_vacias)
        
        df = pd.DataFrame(res.data)
        df = df.rename(columns={
            "numero_serie": "Número de Serie",
            "articulo": "Artículo",
            "categoria": "Categoría",
            "estado": "Estado",
            "cantidad": "Cantidad",
            "ubicacion": "Ubicación"
        })
        return df[columnas_vacias]
    except Exception:
        return pd.DataFrame(columns=columnas_vacias)

inventario_actual = obtener_inventario_real()

if eleccion == "📊 Panel de Informes":
    st.subheader("Estado General del Inventario en la Nube")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<p class="metric-label">Total de Unidades Disponibles</p>', unsafe_allow_html=True)
        cant_total = inventario_actual["Cantidad"].sum() if "Cantidad" in inventario_actual.columns else 0
        st.markdown(f'<p class="metric-value">{cant_total}</p>', unsafe_allow_html=True)
    with col2:
        st.markdown('<p class="metric-label">Total de Artículos Únicos</p>', unsafe_allow_html=True)
        st.markdown(f'<p class="metric-value">{len(inventario_actual)}</p>', unsafe_allow_html=True)
    with col3:
        st.markdown('<p class="metric-label">Artículos en Estado "Baja"</p>', unsafe_allow_html=True)
        cant_baja = len(inventario_actual[inventario_actual["Estado"] == "Baja"]) if "Estado" in inventario_actual.columns else 0
        st.markdown(f'<p class="metric-value" style="color: #EF4444;">{cant_baja}</p>', unsafe_allow_html=True)
        
    st.write("---")
    
    busqueda = st.text_input("🔍 Escanear Nro de Serie o buscar de forma predictiva:")
    filtro_estado = st.multiselect("Filtrar informes por Estado en Depósito:", estados_permitidos)
    
    df_filtrado = inventario_actual
    if filtro_estado and "Estado" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Estado"].isin(filtro_estado)]
    if busqueda and "Número de Serie" in df_filtrado.columns:
        df_filtrado = df_filtrado[
            df_filtrado["Número de Serie"].astype(str).str.contains(busqueda) | 
            df_filtrado["Artículo"].astype(str).str.contains(busqueda, case=False)
        ]
        
    if not df_filtrado.empty and busqueda:
        st.markdown("### 📋 Información del Artículo Seleccionado")
        for _, fila in df_filtrado.iterrows():
            st.markdown(f"""
            <div class="detalle-box">
                <strong>⚙️ Número de Serie:</strong> {fila['Número de Serie']}<br>
                <strong>📦 Artículo:</strong> {fila['Artículo']}<br>
                <strong>📁 Categoría:</strong> {fila['Categoría']}<br>
                <strong>📌 Estado en Depósito:</strong> {fila['Estado']}<br>
                <strong>🔢 Cantidad Disponible:</strong> {fila['Cantidad']} unidades<br>
                <strong>📍 Ubicación Almacén:</strong> {fila['Ubicación']}
            </div>
            """, unsafe_allow_html=True)
        st.write("---")

    st.dataframe(df_filtrado, use_container_width=True)
    
    if not inventario_actual.empty:
        buffer_excel = io.BytesIO()
        with pd.ExcelWriter(buffer_excel, engine='openpyxl') as writer:
            inventario_actual.to_excel(writer, index=False, sheet_name="Inventario")
        st.download_button(label="📥 Exportar Inventario Completo a Excel", data=buffer_excel.getvalue(), file_name="inventario_stock.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

elif eleccion == "🚚 Emitir Remito de Entrega":
    st.subheader("Generación de Remito Oficial")
    
    with st.form("formulario_remito", clear_on_submit=False):
        cliente = st.text_input("Cliente / Receptor de la entrega:")
        codigo_scan = st.text_input("Pistola Láser (Hacé clic acá antes de escanear):")
        cantidad_entrega = st.number_input("Cantidad a entregar:", min_value=1, step=1)
        observaciones = st.text_area("Notas / Observaciones del remito:")
        emitir = st.form_submit_button("Validar y Procesar Remito")
        
    if emitir:
        if not cliente or not codigo_scan:
            st.error("Por favor, completa el nombre del cliente y escanea un número de serie válido.")
        elif supabase is None:
            st.error("No hay conexión activa con la base de datos.")
        else:
            res_item = supabase.table("inventario_deposito").select("*").eq("numero_serie", codigo_scan).execute()
            if res_item.data:
                item = res_item.data[0] if isinstance(res_item.data, list) else res_item.data
                stock_actual = int(item["cantidad"])
                articulo_nombre = item["articulo"]
                
                if stock_actual >= cantidad_entrega:
                    nueva_cantidad = stock_actual - cantidad_entrega
                    supabase.table("inventario_deposito").update({"cantidad": nueva_cantidad}).eq("numero_serie", codigo_scan).execute()
                    
                    st.session_state["pdf_listo"] = generar_pdf_remito(cliente, codigo_scan, cantidad_entrega, observaciones, articulo_nombre)
                    st.session_state["cliente_remito"] = cliente
                    st.success(f"¡Sincronizado! Stock descontado en la nube. Quedan {nueva_cantidad} unidades de {articulo_nombre}.")
                else:
                    st.error(f"Stock insuficiente en internet. Solo quedan {stock_actual} unidades de {articulo_nombre}.")
            else:
                st.error("El Número de Serie escaneado no existe en la base de datos de internet.")

    if "pdf_listo" in st.session_state:
        st.write("---")
        st.download_button(
            label="📥 Descargar e Imprimir Remito en PDF", 
            data=st.session_state["pdf_listo"], 
            file_name=f"remito_{st.session_state['cliente_remito']}.pdf", 
            mime="application/pdf"
        )

elif eleccion == "➕ Alta/Modificación de Artículos":
    st.subheader("Administración de Productos")
    
    st.markdown("### 📥 Carga masiva desde planilla Excel")
    archivo_subido = st.file_uploader("Seleccioná tu archivo .xlsx", type=["xlsx"])
    if archivo_subido is not None and supabase is not None:
        try:
            df_excel = pd.read_excel(archivo_subido)
            contador_cargas = 0
            for _, fila in df_excel.iterrows():
                datos_db = {
                    "numero_serie": str(fila["Número de Serie"]),
                    "articulo": str(fila["Artículo"]),
                    "categoria": str(fila["Categoría"]),
                    "estado": str(fila["Estado"]),
                    "cantidad": int(fila["Cantidad"]),
                    "ubicacion": str(fila["Ubicación"])
                }
                supabase.table("inventario_deposito").upsert(datos_db, on_conflict="numero_serie").execute()
                contador_cargas += 1
            st.success(f"¡Éxito! Se subieron e integraron {contador_cargas} artículos desde el Excel a la nube.")
        except Exception as e:
            st.error(f"Error al procesar el Excel: {e}.")
            
    st.write("---")
    st.markdown("### ➕ Carga Manual de un Artículo")
    with st.form("alta_articulo", clear_on_submit=True):
        cod = st.text_input("Número de Serie:")
        nom = st.text_input("Nombre del Artículo:")
        cat = st.text_input("Categoría:")
        est = st.selectbox("Estado en Depósito:", estados_permitidos)

