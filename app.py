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
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Receptor: {cli}")
    p.drawString(50, 670, f"Artículo: {art} (Serie: {ser}) | Cantidad: {cant}")
    p.drawString(50, 640, f"Observaciones: {obs}")
    p.line(50, 500, 250, 500)
    p.drawString(50, 480, "Firma del Receptor")
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
    u = st.text_input("Usuario").strip()
    p = st.text_input("Contraseña", type="password").strip()
    if st.button("Ingresar"):
        ok = next((x for x in cargar_usu() if x["usuario"] == u and x["clave"] == p), None)
        if ok:
            st.session_state["user"] = ok
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")
    st.stop()

usr = st.session_state["user"]
rol = usr["rol"]
st.title(f"📦 Control de Stock — {usr.get('nombre', usr['usuario'])} ({rol})")
if st.button("Cerrar Sesión"):
    st.session_state["user"] = None
    st.rerun()

opciones = ["Inventario", "Asistente MIA", "Glosario"]
if rol in ["Stock", "Administrador"]: opciones += ["Cargar Stock", "Entregas", "Editar Stock"]
if rol == "Administrador": opciones += ["Backup Oficina", "Usuarios"]
vista = st.radio("Sección:", opciones, horizontal=True)
st.divider()

if vista == "Inventario":
    df = cargar_inv()
    if df.empty:
        st.info("Inventario vacío.")
    else:
        c1, c2, c3 = st.columns(3)
        fm = c1.selectbox("Módulo:", ["Todos"] + MODULOS)
        fe = c2.selectbox("Estado:", ["Todos"] + ESTADOS)
        fb = c3.text_input("Buscar:")
        if fm != "Todos": df = df[df["modulo"] == fm]
        if fe != "Todos": df = df[df["estado"] == fe]
        if fb: df = df[df.astype(str).apply(lambda x: x.str.contains(fb, case=False, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif vista == "Asistente MIA":
    df = cargar_inv()
    q = st.selectbox("Consulta rápida MIA:", ["Resumen por Módulo", "Ver Módulo específico", "Equipos A revisar / Baja", "Stock crítico (<=1)"])
    if df.empty: st.warning("Sin datos.")
    elif q == "Resumen por Módulo": st.dataframe(df.groupby("modulo", as_index=False)["cantidad"].sum(), use_container_width=True, hide_index=True)
    elif q == "Ver Módulo específico":
        ms = st.selectbox("Módulo:", MODULOS)
        st.dataframe(df[df["modulo"] == ms], use_container_width=True, hide_index=True)
    elif q == "Equipos A revisar / Baja": st.dataframe(df[df["estado"].isin(["A revisar", "Baja"])], use_container_width=True, hide_index=True)
    elif q == "Stock crítico (<=1)": st.dataframe(df[df["cantidad"] <= 1], use_container_width=True, hide_index=True)

elif vista == "Glosario":
    dfg = cargar_glo()
    bg = st.text_input("Buscar código o descripción:")
    st.dataframe(dfg[dfg.astype(str).apply(lambda x: x.str.contains(bg, case=False, na=False)).any(axis=1)] if (bg and not dfg.empty) else dfg, use_container_width=True, hide_index=True)
    if rol in ["Stock", "Administrador"]:
        gc, ga, gm, gd = st.text_input("Código*:"), st.text_input("Artículo*:"), st.selectbox("Módulo:", MODULOS), st.text_input("Descriptivo*:")
        if st.button("Guardar en Glosario") and gc and ga and gd:
            pd.concat([dfg, pd.DataFrame([{"codigo": gc.strip(), "articulo": ga.strip(), "modulo": gm, "descripcion": gd.strip()}])], ignore_index=True).to_csv(F_GLO, index=False)
            st.rerun()

elif vista == "Cargar Stock":
    cod, nom = st.text_input("Número de Serie / Código*:"), st.text_input("Nombre del Artículo*:")
    mod, cat = st.selectbox("Módulo*:", MODULOS), st.text_input("Categoría:")
    est, cant = st.selectbox("Estado:", ESTADOS), st.number_input("Cantidad:", min_value=1, value=1)
    if st.button("Guardar Artículo"):
        df = cargar_inv()
        if not cod.strip() or not nom.strip(): st.error("Completá Serie y Artículo.")
        elif cod.strip() in df["numero_serie"].values: st.warning("Ese código ya existe.")
        else:
            fila = pd.DataFrame([{"numero_serie": cod.strip(), "articulo": nom.strip(), "modulo": mod, "categoria": cat.strip(), "estado": est, "cantidad": int(cant)}])
            pd.concat([df, fila], ignore_index=True).to_csv(F_INV, index=False)
            st.success(f"Guardado en {mod}.")

elif vista == "Entregas":
    cli, ser, ce, obs = st.text_input("Receptor:"), st.text_input("Serie:"), st.number_input("Cantidad:", min_value=1, value=1), st.text_area("Observaciones:")
    if st.button("Confirmar Entrega"):
        df = cargar_inv()
        m = df.index[df["numero_serie"] == ser.strip()].tolist()
        if m and cli.strip() and int(df.at[m.pop(0), "cantidad"]) >= ce:
            idx = df.index[df["numero_serie"] == ser.strip()].tolist().pop(0)
            df.at[idx, "cantidad"] = int(df.at[idx, "cantidad"]) - ce
            df.to_csv(F_INV, index=False)
            st.session_state["pdf"] = pdf_remito(cli, ser.strip(), ce, obs, str(df.at[idx, "articulo"]))
            st.success("Entrega registrada.")
        else: st.error("Verificá datos o stock disponible.")
    if "pdf" in st.session_state: st.download_button("Descargar Remito PDF", data=st.session_state["pdf"], file_name="Remito.pdf", mime="application/pdf")

elif vista == "Editar Stock":
    df = cargar_inv()
    if df.empty: st.info("Sin artículos.")
    else:
        sel = st.selectbox("Serie a editar:", df["numero_serie"].tolist())
        idx = df.index[df["numero_serie"] == sel].tolist().pop(0)
        enom = st.text_input("Artículo:", value=str(df.at[idx, "articulo"]))
        emod = st.selectbox("Módulo:", MODULOS, index=MODULOS.index(df.at[idx, "modulo"]) if df.at[idx, "modulo"] in MODULOS else 7)
        eest = st.selectbox("Estado:", ESTADOS, index=ESTADOS.index(df.at[idx, "estado"]) if df.at[idx, "estado"] in ESTADOS else 0)
        ecant = st.number_input("Cantidad:", min_value=0, value=int(df.at[idx, "cantidad"]))
        if st.button("Actualizar Registro"):
            df.at[idx, "articulo"], df.at[idx, "modulo"], df.at[idx, "estado"], df.at[idx, "cantidad"] = enom.strip(), emod, eest, int(ecant)
            df.to_csv(F_INV, index=False)
            st.success("Actualizado.")
            st.rerun()

elif vista == "Backup Oficina":
    xb = excel_backup(cargar_inv(), cargar_glo(), pd.DataFrame(cargar_usu()))
    st.download_button("📥 Descargar Backup Excel (.xlsx)", data=xb, file_name=f"Backup_Stock_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    up = st.file_uploader("Restaurar Backup (.xlsx)", type=["xlsx"])
    if up and st.button("Restaurar"):
        xls = pd.ExcelFile(up)
        if "Inventario" in xls.sheet_names: pd.read_excel(xls, "Inventario").to_csv(F_INV, index=False)
        if "Glosario" in xls.sheet_names: pd.read_excel(xls, "Glosario").to_csv(F_GLO, index=False)
        if "Usuarios" in xls.sheet_names: pd.read_excel(xls, "Usuarios").to_csv(F_USU, index=False)
        st.success("Restaurado.")
        st.rerun()

elif vista == "Usuarios":
    lu = cargar_usu()
    st.dataframe(pd.DataFrame(lu)[["usuario", "nombre", "rol"]], use_container_width=True, hide_index=True)
    un, uu, up, ur = st.text_input("Nombre:"), st.text_input("Usuario:"), st.text_input("Clave:", type="password"), st.selectbox("Rol:", ["Revisor", "Stock", "Administrador"])
    if st.button("Crear Usuario") and uu.strip() and up.strip():
        lu.append({"nombre": un.strip() or uu.strip(), "usuario": uu.strip(), "clave": up.strip(), "rol": ur})
        pd.DataFrame(lu).to_csv(F_USU, index=False)
        st.success("Usuario creado.")
        st.rerun()
