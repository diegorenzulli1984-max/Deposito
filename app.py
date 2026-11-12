import streamlit as st
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io, os
from datetime import datetime

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")

F_INV, F_USU, F_GLO = "inventario_deposito.csv", "usuarios_stock.csv", "glosario_codigos.csv"
ESTADOS = ["Nuevo", "Usado", "A revisar", "Baja", "Reciclaje"]
MODULOS = ["Entretenimiento", "Capacitación", "Microcine", "Robótica", "Cartelería", "Impresión 3D", "Mobiliario", "General"]

def cargar_inv():
    if os.path.exists(F_INV):
        df = pd.read_csv(F_INV, dtype={"numero_serie": str})
        if "modulo" not in df.columns: df["modulo"] = "General"
        df["modulo"] = df["modulo"].fillna("General")
        df["cantidad"] = pd.to_numeric(df["cantidad"], errors="coerce").fillna(0).astype(int)
        return df
    return pd.DataFrame(columns=["numero_serie", "articulo", "modulo", "categoria", "estado", "cantidad"])

def cargar_usu():
    base = [{"usuario": "admin", "clave": "Stock2026!", "rol": "Administrador", "nombre": "Responsable de Área"}]
    if os.path.exists(F_USU):
        for _, r in pd.read_csv(F_USU, dtype=str).fillna("").iterrows():
            if r["usuario"] != "admin": base.append(r.to_dict())
    return base

def cargar_glo():
    return pd.read_csv(F_GLO, dtype=str).fillna("") if os.path.exists(F_GLO) else pd.DataFrame(columns=["codigo", "articulo", "modulo", "descripcion"])

def pdf_remito(cli, ser, cant, obs, art):
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL")
    p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    p.drawString(50, 675, f"Receptor: {cli}")
    p.drawString(50, 650, f"Artículo: {art} (Serie: {ser})")
    p.drawString(50, 625, f"Cantidad: {cant} unidades")
    p.drawString(50, 600, f"Observaciones: {obs}")
    p.line(50, 480, 250, 480)
    p.drawString(50, 460, "Firma del Receptor")
    p.showPage()
    p.save()
    buf.seek(0)
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

if not st.session_state["user"]:
    st.title("🔐 Acceso al Control de Stock")
    _, c2, _ = st.columns()
    with c2:
        with st.form("login"):
            u = st.text_input("Usuario").strip()
            p = st.text_input("Contraseña", type="password").strip()
            if st.form_submit_button("Ingresar", use_container_width=True):
                ok = next((x for x in cargar_usu() if x["usuario"] == u and x["clave"] == p), None)
                if ok:
                    st.session_state["user"] = ok
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")
    st.stop()

usr = st.session_state["user"]
rol = usr["rol"]
c_tit, c_btn = st.columns()
c_tit.title("📦 Control de Stock y Depósito")
c_tit.caption(f"👤 **{usr.get('nombre', usr['usuario'])}** | Rol: **{rol}**")
if c_btn.button("Cerrar Sesión", use_container_width=True):
    st.session_state["user"] = None
    st.rerun()

tabs_nombres = ["📊 Inventario", "🤖 Asistente MIA", "📖 Glosario"]
if rol in ["Stock", "Administrador"]:
    tabs_nombres += ["➕ Cargar Stock", "📤 Entregas", "✏️ Editar Stock"]
if rol == "Administrador":
    tabs_nombres += ["💾 Backup Oficina", "👥 Usuarios"]

tabs = st.tabs(tabs_nombres)

with tabs:
    df = cargar_inv()
    if df.empty:
        st.info("Inventario vacío. Cargá artículos o restaurá un Backup en Excel.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Artículos", len(df))
        m2.metric("Unidades Totales", int(df["cantidad"].sum()))
        m3.metric("Módulos", df["modulo"].nunique())
        m4.metric("A revisar / Baja", len(df[df["estado"].isin(["A revisar", "Baja"])]))
        f1, f2, f3 = st.columns(3)
        fm = f1.selectbox("Módulo:", ["Todos"] + MODULOS)
        fe = f2.selectbox("Estado:", ["Todos"] + ESTADOS)
        fb = f3.text_input("Buscar:")
        if fm != "Todos": df = df[df["modulo"] == fm]
        if fe != "Todos": df = df[df["estado"] == fe]
        if fb: df = df[df.astype(str).apply(lambda x: x.str.contains(fb, case=False, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)

with tabs:
    st.subheader("🤖 Asistente MIA — Consultas Guiadas")
    df = cargar_inv()
    if df.empty:
        st.warning("No hay datos cargados aún.")
    else:
        q = st.selectbox("Elegí una consulta:", ["1. Resumen por Módulo", "2. Artículos de un Módulo", "3. Estado 'A revisar' o 'Baja'", "4. Buscar artículo o serie", "5. Stock crítico (<= 1)"])
        if q.startswith("1."):
            st.dataframe(df.groupby("modulo", as_index=False)["cantidad"].sum(), use_container_width=True, hide_index=True)
        elif q.startswith("2."):
            ms = st.selectbox("Módulo a ver:", MODULOS)
            st.dataframe(df[df["modulo"] == ms], use_container_width=True, hide_index=True)
        elif q.startswith("3."):
            st.dataframe(df[df["estado"].isin(["A revisar", "Baja"])], use_container_width=True, hide_index=True)
        elif q.startswith("4."):
            t = st.text_input("Nombre o código:")
            if t: st.dataframe(df[df.astype(str).apply(lambda x: x.str.contains(t, case=False, na=False)).any(axis=1)], use_container_width=True, hide_index=True)
        elif q.startswith("5."):
            st.dataframe(df[df["cantidad"] <= 1], use_container_width=True, hide_index=True)

with tabs:
    st.subheader("📖 Glosario de Códigos")
    dfg = cargar_glo()
    bg = st.text_input("Buscar en glosario:")
    if not dfg.empty:
        ver_g = dfg[dfg.astype(str).apply(lambda x: x.str.contains(bg, case=False, na=False)).any(axis=1)] if bg else dfg
        st.dataframe(ver_g, use_container_width=True, hide_index=True)
    else:
        st.info("Glosario vacío.")
    if rol in ["Stock", "Administrador"]:
        with st.form("f_glo", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            gc, ga, gm = c1.text_input("Código*:"), c2.text_input("Artículo*:"), c3.selectbox("Módulo:", MODULOS)
            gd = st.text_input("Descriptivo*:")
            if st.form_submit_button("Agregar Código") and gc and ga and gd:
                dfg = pd.concat([dfg, pd.DataFrame([{"codigo": gc.strip(), "articulo": ga.strip(), "modulo": gm, "descripcion": gd.strip()}])], ignore_index=True)
                dfg.to_csv(F_GLO, index=False)
                st.rerun()
        up_g = st.file_uploader("Importar Glosario (Excel/CSV con columnas: codigo, articulo, modulo, descripcion)", type=["xlsx", "csv"])
        if up_g and st.button("Subir Glosario"):
            nuevo_g = pd.read_excel(up_g) if up_g.name.endswith(".xlsx") else pd.read_csv(up_g)
            nuevo_g.columns = [c.strip().lower() for c in nuevo_g.columns]
            pd.concat([dfg, nuevo_g.fillna("")], ignore_index=True).to_csv(F_GLO, index=False)
            st.rerun()

if rol in ["Stock", "Administrador"]:
    with tabs:
        st.subheader("➕ Carga / Inserción de Stock")
        with st.form("f_carga", clear_on_submit=True):
            c1, c2 = st.columns(2)
            cod, nom = c1.text_input("Número de Serie / Código*:"), c2.text_input("Artículo*:")
            mod, cat = c1.selectbox("Módulo*:", MODULOS), c2.text_input("Categoría:")
            est, cant = c1.selectbox("Estado:", ESTADOS), c2.number_input("Cantidad:", min_value=1, value=1, step=1)
            if st.form_submit_button("Guardar en Stock", use_container_width=True):
                if cod.strip() and nom.strip():
                    df = cargar_inv()
                    if cod.strip() in df["numero_serie"].values:
                        st.warning("Ese código ya existe. Usá 'Editar Stock'.")
                    else:
                        fila = pd.DataFrame([{"numero_serie": cod.strip(), "articulo": nom.strip(), "modulo": mod, "categoria": cat.strip(), "estado": est, "cantidad": int(cant)}])
                        pd.concat([df, fila], ignore_index=True).to_csv(F_INV, index=False)
                        st.success(f"Cargado en módulo {mod}.")
                else:
                    st.error("Completá Serie y Artículo.")

    with tabs:
        st.subheader("📤 Entregas y Remitos")
        with st.form("f_ent"):
            cli, ser = st.text_input("Receptor:"), st.text_input("Número de Serie:")
            cant_e, obs = st.number_input("Cantidad:", min_value=1, value=1), st.text_area("Observaciones:")
            if st.form_submit_button("Confirmar Entrega", use_container_width=True):
                df = cargar_inv()
                match = df.index[df["numero_serie"] == ser.strip()].tolist()
                if match and cli.strip():
                    i = match
                    if int(df.at[i, "cantidad"]) >= cant_e:
                        df.at[i, "cantidad"] = int(df.at[i, "cantidad"]) - cant_e
                        df.to_csv(F_INV, index=False)
                        st.session_state["remito"] = pdf_remito(cli, ser.strip(), cant_e, obs, str(df.at[i, "articulo"]))
                        st.success("Entrega registrada.")
                    else:
                        st.error("Stock insuficiente.")
                else:
                    st.error("Verificá receptor y número de serie.")
        if "remito" in st.session_state:
            st.download_button("📄 Descargar Remito PDF", data=st.session_state["remito"], file_name="Remito_Entrega.pdf", mime="application/pdf")

    with tabs:
