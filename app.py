import streamlit as st
import pandas as pd
import io
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from vistas_admin import mostrar_chat, mostrar_editar, mostrar_backup, mostrar_usuarios

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")
st.markdown("""<style>div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"]{background-color:#1D4ED8!important;border-color:#1D4ED8!important;color:white!important;}</style>""", unsafe_allow_html=True)

F_INV = "inventario_deposito.csv"
F_USU = "usuarios_stock.csv"
F_GLO = "glosario_codigos.csv"

ESTADOS = ["Nuevo", "Usado", "A revisar", "Baja", "Reciclaje"]
MODULOS = ["Entretenimiento", "Capacitación", "Microcine", "Robótica", "Cartelería", "Impresión 3D", "Mobiliario", "General"]
VISTAS = ["📊 Inventario", "💬 Chat LÍA", "📖 Glosario", "➕ Cargar Stock", "📤 Entregas", "✏️ Editar Stock", "💾 Backup Oficina", "👥 Usuarios"]

def cargar_inv():
    if os.path.exists(F_INV):
        df = pd.read_csv(F_INV, dtype={"numero_serie": str})
        if "modulo" not in df.columns:
            df["modulo"] = "General"
        df["modulo"] = df["modulo"].fillna("General")
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
        return df
    return pd.DataFrame(columns=["numero_serie", "articulo", "modulo", "categoria", "estado", "cantidad"])

def cargar_usu():
    base = [{"usuario": "admin", "clave": "Stock2026!", "rol": "Administrador", "nombre": "Responsable de Área", "permisos": "|".join(VISTAS)}]
    if os.path.exists(F_USU):
        df_u = pd.read_csv(F_USU, dtype=str).fillna("")
        for _, r in df_u.iterrows():
            d = r.to_dict()
            d["permisos"] = d.get("permisos") or "|".join(VISTAS[:3])
            if d["usuario"] == "admin":
                base[0] = d
            else:
                base.append(d)
    return base

def cambiar_clave_usuario(usuario_actual, nueva_clave):
    lista_usuarios = cargar_usu()
    for u in lista_usuarios:
        if u["usuario"] == usuario_actual:
            u["clave"] = nueva_clave
            break
    pd.DataFrame(lista_usuarios).to_csv(F_USU, index=False)

def cargar_glo():
    if os.path.exists(F_GLO):
        return pd.read_csv(F_GLO, dtype=str).fillna("")
    return pd.DataFrame(columns=["codigo", "articulo", "modulo", "descripcion"])

def pdf_remito(cli, ser, cant, obs, art):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL")
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Receptor: {cli}")
    p.drawString(50, 670, f"Artículo: {art} (Serie: {ser}) | Cantidad: {cant}")
    p.drawString(50, 640, f"Observaciones: {obs}")
    p.line(50, 500, 250, 500)
    p.drawString(50, 480, "Firma del Receptor")
    p.showPage()
    p.save()
    buf.seek(0)
    return buf.getvalue()

if "user" not in st.session_state:
    st.session_state["user"] = None
if "vista" not in st.session_state:
    st.session_state["vista"] = "📊 Inventario"

if not st.session_state["user"]:
    st.write("")
    _, centro, _ = st.columns([1.3, 1, 1.3])
    with centro:
        with st.container(border=True):
            st.markdown("### 🔐 Control de Stock")
            u = st.text_input("Usuario:", autocomplete="off", key="inp_u").strip()
            p = st.text_input("Clave:", type="password", autocomplete="new-password", key="inp_p").strip()
            if st.button("Ingresar", type="primary", use_container_width=True):
                ok = next((x for x in cargar_usu() if x["usuario"] == u and x["clave"] == p), None)
                if ok:
                    st.session_state["user"] = ok
                    st.session_state["vista"] = ok["permisos"].split("|")[0]
                    st.rerun()
                else:
                    st.error("Usuario o clave incorrectos.")
    st.stop()

usr = st.session_state["user"]
opciones = [v for v in VISTAS if v in usr.get("permisos", "").split("|")] or ["📊 Inventario"]

# --- ENCABEZADO Y MENÚ DE USUARIO ---
c_tit, c_menu = st.columns([4.5, 0.5])
c_tit.markdown(f"### 📦 Control de Stock — {usr.get('nombre', usr['usuario'])} `{usr['rol']}`")

with c_menu:
    with st.popover(f"👤 {usr['usuario']}"):
        palabras = usr.get("nombre", usr["usuario"]).strip().split()
        iniciales = "".join([p[0].upper() for p in palabras[:2]]) if palabras else "US"
        
        col_img, col_info = st.columns([1, 2.5])
        col_img.markdown(
            f"""<div style="width:46px;height:46px;border-radius:50%;background-color:#1D4ED8;color:white;display:flex;align-items:center;justify-content:center;font-weight:bold;font-size:17px;">{iniciales}</div>""",
            unsafe_allow_html=True
        )
        col_info.markdown(f"**{usr.get('nombre', usr['usuario'])}**\n\n`{usr['rol']}`")
        
        st.divider()
        with st.expander("🔑 Cambiar clave"):
            c_act = st.text_input("Clave actual:", type="password", key="c_act")
            c_nva = st.text_input("Nueva clave:", type="password", key="c_nva")
            c_rep = st.text_input("Repetir nueva:", type="password", key="c_rep")
            if st.button("Guardar", type="primary", use_container_width=True):
                if c_act != usr["clave"]:
                    st.error("Clave actual incorrecta.")
                elif len(c_nva.strip()) < 4:
                    st.warning("Mínimo 4 caracteres.")
                elif c_nva != c_rep:
                    st.error("No coinciden.")
                else:
                    cambiar_clave_usuario(usr["usuario"], c_nva.strip())
                    st.session_state["user"]["clave"] = c_nva.strip()
                    st.success("✅ Clave cambiada.")
        st.divider()
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state["user"] = None
            st.rerun()

cols_nav = st.columns(len(opciones))
for i, op in enumerate(opciones):
    if cols_nav[i].button(op, type=("primary" if st.session_state["vista"] == op else "secondary"), use_container_width=True):
        st.session_state["vista"] = op
        st.rerun()
st.divider()
vista = st.session_state["vista"]

if vista == "📊 Inventario":
    df = cargar_inv()
    if df.empty:
        st.info("Inventario vacío. Cargá artículos en '➕ Cargar Stock'.")
    else:
        c1, c2, c3 = st.columns(3)
        fm = c1.selectbox("Módulo:", ["Todos"] + MODULOS)
        fe = c2.selectbox("Estado:", ["Todos"] + ESTADOS)
        fb = c3.text_input("Buscar:")
        if fm != "Todos":
            df = df[df["modulo"] == fm]
        if fe != "Todos":
            df = df[df["estado"] == fe]
        if fb:
            df = df[df.astype(str).apply(lambda x: x.str.contains(fb, case=False, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif vista == "💬 Chat LÍA":
    mostrar_chat(cargar_inv, MODULOS, ESTADOS, usr)

elif vista == "📖 Glosario":
    dfg = cargar_glo()
    bg = st.text_input("Buscar código o descripción:")
    st.dataframe(dfg[dfg.astype(str).apply(lambda x: x.str.contains(bg, case=False, na=False)).any(axis=1)] if (bg and not dfg.empty) else dfg, use_container_width=True, hide_index=True)
    if "➕ Cargar Stock" in opciones:
        c1, c2, c3, c4 = st.columns(4)
        gc = c1.text_input("Código*:")
        ga = c2.text_input("Artículo*:")
        gm = c3.selectbox("Módulo:", MODULOS)
        gd = c4.text_input("Descriptivo*:")
        if st.button("Guardar en Glosario", type="primary") and gc and ga and gd:
            nuevo_g = pd.DataFrame([{"codigo": gc.strip(), "articulo": ga.strip(), "modulo": gm, "descripcion": gd.strip()}])
            pd.concat([dfg, nuevo_g], ignore_index=True).to_csv(F_GLO, index=False)
            st.rerun()

elif vista == "➕ Cargar Stock":
    st.subheader("Carga Manual Individual")
    c1, c2 = st.columns(2)
    cod = c1.text_input("Número de Serie / Código*:")
    nom = c2.text_input("Nombre del Artículo*:")
    mod = c1.selectbox("Módulo*:", MODULOS)
    cat = c2.text_input("Categoría:")
    est = c1.selectbox("Estado:", ESTADOS)
    cant = c2.number_input("Cantidad:", min_value=1, value=1)
    if st.button("Guardar Artículo", type="primary") and cod.strip() and nom.strip():
        df = cargar_inv()
        if cod.strip() in df["numero_serie"].values:
            st.warning("Ese código ya existe en el inventario.")
        else:
            nueva_fila = pd.DataFrame([{
                "numero_serie": cod.strip(),
                "articulo": nom.strip(),
                "modulo": mod,
                "categoria": cat.strip(),
                "estado": est,
                "cantidad": int(cant)
            }])
            pd.concat([df, nueva_fila], ignore_index=True).to_csv(F_INV, index=False)
            st.success("✅ Artículo guardado correctamente.")
            st.rerun()

    st.divider()
    st.subheader("📥 Carga Masiva desde Excel o CSV")
    st.caption("Columnas requeridas: numero_serie, articulo, modulo, categoria, estado, cantidad")
    archivo = st.file_uploader("Seleccionar archivo (.xlsx o .csv)", type=["xlsx", "csv"])

    if archivo is not None:
        if archivo.name.endswith(".csv"):
            df_subido = pd.read_csv(archivo, dtype={"numero_serie": str})
        else:
            df_subido = pd.read_excel(archivo, dtype={"numero_serie": str})

        df_subido.columns = [c.strip().lower() for c in df_subido.columns]
        cols_req = ["numero_serie", "articulo", "modulo", "categoria", "estado", "cantidad"]

        if all(col in df_subido.columns for col in cols_req):
            st.dataframe(df_subido[cols_req].head(10), use_container_width=True, hide_index=True)
            if st.button("Importar al Inventario", type="primary"):
