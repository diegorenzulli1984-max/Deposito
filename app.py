import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io, os
from datetime import datetime

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")

st.markdown("""<style>
div.stButton > button[kind="primary"], div.stDownloadButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {
    background-color: #1D4ED8 !important; border-color: #1D4ED8 !important; color: white !important;
}
div.stButton > button[kind="primary"]:hover { background-color: #1E40AF !important; border-color: #1E40AF !important; }
</style>""", unsafe_allow_html=True)

F_INV, F_USU, F_GLO = "inventario_deposito.csv", "usuarios_stock.csv", "glosario_codigos.csv"
ESTADOS = ["Nuevo", "Usado", "A revisar", "Baja", "Reciclaje"]
MODULOS = ["Entretenimiento", "Capacitación", "Microcine", "Robótica", "Cartelería", "Impresión 3D", "Mobiliario", "General"]
VISTAS = ["📊 Inventario", "🤖 Asistente MIA", "📖 Glosario", "➕ Cargar Stock", "📤 Entregas", "✏️ Editar Stock", "💾 Backup Oficina", "👥 Usuarios"]

def cargar_inv():
    if os.path.exists(F_INV):
        df = pd.read_csv(F_INV, dtype={"numero_serie": str})
        if "modulo" not in df.columns: df["modulo"] = "General"
        df["modulo"] = df["modulo"].fillna("General")
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
        return df
    return pd.DataFrame(columns=["numero_serie", "articulo", "modulo", "categoria", "estado", "cantidad"])

def cargar_usu():
    base = [{"usuario": "admin", "clave": "Stock2026!", "rol": "Administrador", "nombre": "Responsable de Área", "permisos": "|".join(VISTAS)}]
    if os.path.exists(F_USU):
        for _, r in pd.read_csv(F_USU, dtype=str).fillna("").iterrows():
            if r["usuario"] != "admin":
                d = r.to_dict()
                if not d.get("permisos"): d["permisos"] = "|".join(VISTAS[:3])
                base.append(d)
    return base

def cargar_glo():
    return pd.read_csv(F_GLO, dtype=str).fillna("") if os.path.exists(F_GLO) else pd.DataFrame(columns=["codigo", "articulo", "modulo", "descripcion"])

def pdf_remito(cli, ser, cant, obs, art):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 18); p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL")
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Receptor: {cli}")
    p.drawString(50, 670, f"Artículo: {art} (Serie: {ser}) | Cantidad: {cant}")
    p.drawString(50, 640, f"Observaciones: {obs}")
    p.line(50, 500, 250, 500); p.drawString(50, 480, "Firma del Receptor")
    p.showPage(); p.save(); buf.seek(0)
    return buf.getvalue()

def excel_backup(df_i, df_g, df_u):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df_i.to_excel(w, sheet_name="Inventario", index=False)
        df_g.to_excel(w, sheet_name="Glosario", index=False)
        df_u.to_excel(w, sheet_name="Usuarios", index=False)
    buf.seek(0)
    return buf.getvalue()

if "user" not in st.session_state: st.session_state["user"] = None
if "vista" not in st.session_state: st.session_state["vista"] = "📊 Inventario"

if not st.session_state["user"]:
    st.write(""); st.write("")
    _, centro, _ = st.columns([1.2, 1, 1.2])
    with centro:
        with st.container(border=True):
            st.markdown("### 🔐 Control de Stock")
            with st.form("login_box"):
                u, p = st.text_input("Usuario").strip(), st.text_input("Contraseña", type="password").strip()
                if st.form_submit_button("Ingresar al Sistema", type="primary", use_container_width=True):
                    ok = next((x for x in cargar_usu() if x["usuario"] == u and x["clave"] == p), None)
                    if ok:
                        st.session_state["user"] = ok
                        st.session_state["vista"] = ok["permisos"].split("|")[0]
                        st.rerun()
                    else: st.error("Usuario o contraseña incorrectos.")
    st.stop()

usr = st.session_state["user"]
opciones = [v for v in VISTAS if v in usr.get("permisos", "").split("|")] or ["📊 Inventario"]
c_tit, c_salir = st.columns([5, 1])
c_tit.markdown(f"### 📦 Control de Stock — {usr.get('nombre', usr['usuario'])} `{usr['rol']}`")
if c_salir.button("Cerrar Sesión", use_container_width=True):
    st.session_state["user"] = None; st.rerun()

cols_nav = st.columns(len(opciones))
for i, op in enumerate(opciones):
    if cols_nav[i].button(op, type=("primary" if st.session_state["vista"] == op else "secondary"), use_container_width=True):
        st.session_state["vista"] = op; st.rerun()

st.divider()
vista = st.session_state["vista"]

if vista == "✏️ Editar Stock":
    df = cargar_inv()
    if df.empty: st.info("No hay artículos cargados todavía para editar.")
    else:
        sel = st.selectbox("Seleccioná el Número de Serie a modificar:", df["numero_serie"].tolist())
        idx = df.index[df["numero_serie"] == sel].tolist()[0]
        c1, c2 = st.columns(2)
        enom = c1.text_input("Artículo:", value=str(df.at[idx, "articulo"]))
        emod = c2.selectbox("Módulo:", MODULOS, index=MODULOS.index(df.at[idx, "modulo"]) if df.at[idx, "modulo"] in MODULOS else 7)
        ecat = c1.text_input("Categoría:", value=str(df.at[idx, "categoria"]))
        eest = c2.selectbox("Estado:", ESTADOS, index=ESTADOS.index(df.at[idx, "estado"]) if df.at[idx, "estado"] in ESTADOS else 0)
        ecant = c1.number_input("Cantidad en Stock:", min_value=0, value=int(df.at[idx, "cantidad"]))
        if st.button("Guardar Cambios", type="primary"):
            df.at[idx, "articulo"], df.at[idx, "modulo"], df.at[idx, "categoria"], df.at[idx, "estado"], df.at[idx, "cantidad"] = enom.strip(), emod, ecat.strip(), eest, int(ecant)
            df.to_csv(F_INV, index=False); st.success("✅ Registro actualizado."); st.rerun()

elif vista == "👥 Usuarios":
    lu = cargar_usu()
    st.dataframe(pd.DataFrame(lu)[["usuario", "nombre", "rol", "permisos"]], use_container_width=True, hide_index=True)
    st.subheader("➕ Crear Usuario y Elegir Permisos")
    c1, c2 = st.columns(2)
    un, uu = c1.text_input("Nombre y Apellido:"), c2.text_input("Usuario:")
    up, ur = c1.text_input("Contraseña:", type="password"), c2.selectbox("Perfil Base:", ["Revisor", "Stock", "Administrador"])
    p_cols = st.columns(4)
    elegidos = [v for i, v in enumerate(VISTAS) if p_cols[i % 4].checkbox(v, value=(ur=="Administrador" or (ur=="Stock" and i<6) or (ur=="Revisor" and i<3)), key=f"c_{v}")]
    if st.button("Crear Usuario", type="primary") and uu.strip() and up.strip():
        if not any(x["usuario"] == uu.strip() for x in lu):
            lu.append({"nombre": un.strip() or uu.strip(), "usuario": uu.strip(), "clave": up.strip(), "rol": ur, "permisos": "|".join(elegidos)})
            pd.DataFrame(lu).to_csv(F_USU, index=False); st.success("Usuario creado."); st.rerun()
        else: st.error("Ese usuario ya existe.")

elif vista == "💾 Backup Oficina":
    xb = excel_backup(cargar_inv(), cargar_glo(), pd.DataFrame(cargar_usu()))
    st.download_button("📥 Descargar Backup Excel (.xlsx)", data=xb, file_name=f"Backup_Stock_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    up = st.file_uploader("Restaurar Backup (.xlsx)", type=["xlsx"])
    if up and st.button("Restaurar"):
        xls = pd.ExcelFile(up)
        if "Inventario" in xls.sheet_names: pd.read_excel(xls, "Inventario").to_csv(F_INV, index=False)
        if "Glosario" in xls.sheet_names: pd.read_excel(xls, "Glosario").to_csv(F_GLO, index=False)
        if "Usuarios" in xls.sheet_names: pd.read_excel(xls, "Usuarios").to_csv(F_USU, index=False)
        st.success("Restaurado."); st.rerun()

elif vista == "📤 Entregas":
    df = cargar_inv()
    cli = st.text_input("Receptor / Destinatario:")
    lista_art = [f"{r['numero_serie']} - {r['articulo']} (Disp: {r['cantidad']})" for _, r in df.iterrows()] if not df.empty else ["Sin artículos cargados aún"]
    sel_art = st.selectbox("Artículo / Serie:", lista_art)
    ce, obs = st.number_input("Cantidad a entregar:", min_value=1, value=1), st.text_area("Observaciones:")
    if st.button("Confirmar Entrega y Generar Remito", type="primary"):
        if df.empty: st.warning("Primero cargá al menos un artículo en '➕ Cargar Stock'.")
        else:
            ser = sel_art.split(" - ")[0].strip()
            idx = df.index[df["numero_serie"] == ser].tolist()[0]
            if cli.strip() and int(df.at[idx, "cantidad"]) >= ce:
                df.at[idx, "cantidad"] = int(df.at[idx, "cantidad"]) - ce; df.to_csv(F_INV, index=False)
                st.session_state["pdf"] = pdf_remito(cli, ser, ce, obs, str(df.at[idx, "articulo"]))
                st.success("✅ Entrega registrada. Descargá el remito abajo:")
            else: st.error("Completá el receptor o verificá stock disponible.")
    if "pdf" in st.session_state:
        st.download_button("📄 Descargar Remito PDF", data=st.session_state["pdf"], file_name="Remito_Entrega.pdf", mime="application/pdf", type="primary")

elif vista == "📊 Inventario":
    df = cargar_inv()
    if df.empty: st.info("Inventario vacío. Cargá artículos en '➕ Cargar Stock'.")
    else:
        c1, c2, c3 = st.columns(3)
        fm, fe, fb = c1.selectbox("Módulo:", ["Todos"] + MODULOS), c2.selectbox("Estado:", ["Todos"] + ESTADOS), c3.text_input("Buscar:")
        if fm != "Todos": df = df[df["modulo"] == fm]
        if fe != "Todos": df = df[df["estado"] == fe]
        if fb: df = df[df.astype(str).apply(lambda x: x.str.contains(fb, case=False, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif vista == "🤖 Asistente MIA":
