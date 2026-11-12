import streamlit as st, pandas as pd, io, os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime
from vistas_admin import mostrar_chat, mostrar_editar, mostrar_backup, mostrar_usuarios

st.set_page_config(page_title="Control de Stock", page_icon="📦", layout="wide")
st.markdown("""<style>div.stButton>button[kind="primary"],div.stDownloadButton>button[kind="primary"]{background-color:#1D4ED8!important;border-color:#1D4ED8!important;color:white!important;}</style>""", unsafe_allow_html=True)

F_INV, F_USU, F_GLO = "inventario_deposito.csv", "usuarios_stock.csv", "glosario_codigos.csv"
ESTADOS = ["Nuevo", "Usado", "A revisar", "Baja", "Reciclaje"]
MODULOS = ["Entretenimiento", "Capacitación", "Microcine", "Robótica", "Cartelería", "Impresión 3D", "Mobiliario", "General"]
VISTAS = ["📊 Inventario", "💬 Chat LÍA", "📖 Glosario", "➕ Cargar Stock", "📤 Entregas", "✏️ Editar Stock", "💾 Backup Oficina", "👥 Usuarios"]

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
        df_u = pd.read_csv(F_USU, dtype=str).fillna("")
        for _, r in df_u.iterrows():
            d = r.to_dict()
            d["permisos"] = d.get("permisos") or "|".join(VISTAS[:3])
            if d["usuario"] == "admin":
                base = d
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
    return pd.read_csv(F_GLO, dtype=str).fillna("") if os.path.exists(F_GLO) else pd.DataFrame(columns=["codigo", "articulo", "modulo", "descripcion"])

def pdf_remito(cli, ser, cant, obs, art):
    buf = io.BytesIO(); p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 18); p.drawCentredString(300, 750, "REMITO DE ENTREGA OFICIAL"); p.setFont("Helvetica", 12)
    p.drawString(50, 700, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')} | Receptor: {cli}")
    p.drawString(50, 670, f"Artículo: {art} (Serie: {ser}) | Cantidad: {cant}"); p.drawString(50, 640, f"Observaciones: {obs}")
    p.line(50, 500, 250, 500); p.drawString(50, 480, "Firma del Receptor"); p.showPage(); p.save(); buf.seek(0); return buf.getvalue()

if "user" not in st.session_state: st.session_state["user"] = None
if "vista" not in st.session_state: st.session_state["vista"] = "📊 Inventario"

if not st.session_state["user"]:
    st.write(""); _, centro, _ = st.columns([1.3, 1, 1.3])
    with centro:
        with st.container(border=True):
            st.markdown("### 🔐 Control de Stock")
            u = st.text_input("Usuario:", autocomplete="off", key="inp_u").strip()
            p = st.text_input("Clave:", type="password", autocomplete="new-password", key="inp_p").strip()
            if st.button("Ingresar", type="primary", use_container_width=True):
                ok = next((x for x in cargar_usu() if x["usuario"] == u and x["clave"] == p), None)
                if ok: st.session_state["user"], st.session_state["vista"] = ok, ok["permisos"].split("|")[0]; st.rerun()
                else: st.error("Usuario o clave incorrectos.")
    st.stop()

usr = st.session_state["user"]
opciones = [v for v in VISTAS if v in usr.get("permisos", "").split("|")] or ["📊 Inventario"]

# --- ENCABEZADO Y MENÚ DE USUARIO ---
c_tit, c_menu = st.columns([4.5, 0.5])
c_tit.markdown(f"### 📦 Control de Stock — {usr.get('nombre', usr['usuario'])} `{usr['rol']}`")

with c_menu:
    with st.popover(f"👤 {usr['usuario']}"):
        nombre_mostrar = usr.get("nombre", usr["usuario"]).replace(" ", "+")
        avatar_url = f"https://ui-avatars.com{nombre_mostrar}&background=1D4ED8&color=fff&rounded=true&size=64"
        
        col_img, col_info = st.columns([1, 2.5])
        col_img.image(avatar_url, width=48)
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
        st.session_state["vista"] = op; st.rerun()
st.divider()
vista = st.session_state["vista"]

if vista == "📊 Inventario":
    df = cargar_inv()
    if df.empty: st.info("Inventario vacío. Cargá artículos en '➕ Cargar Stock'.")
    else:
        c1, c2, c3 = st.columns(3)
        fm, fe, fb = c1.selectbox("Módulo:", ["Todos"] + MODULOS), c2.selectbox("Estado:", ["Todos"] + ESTADOS), c3.text_input("Buscar:")
        if fm != "Todos": df = df[df["modulo"] == fm]
        if fe != "Todos": df = df[df["estado"] == fe]
        if fb: df = df[df.astype(str).apply(lambda x: x.str.contains(fb, case=False, na=False)).any(axis=1)]
        st.dataframe(df, use_container_width=True, hide_index=True)

elif vista == "💬 Chat LÍA": mostrar_chat(cargar_inv, MODULOS, ESTADOS, usr)

elif vista == "📖 Glosario":
    dfg = cargar_glo(); bg = st.text_input("Buscar código o descripción:")
    st.dataframe(dfg[dfg.astype(str).apply(lambda x: x.str.contains(bg, case=False, na=False)).any(axis=1)] if (bg and not dfg.empty) else dfg, use_container_width=True, hide_index=True)
    if "➕ Cargar Stock" in opciones:
        c1, c2, c3, c4 = st.columns(4)
        gc, ga, gm, gd = c1.text_input("Código*:"), c2.text_input("Artículo*:"), c3.selectbox("Módulo:", MODULOS), c4.text_input("Descriptivo*:")
        if st.button("Guardar en Glosario", type="primary") and gc and ga and gd:
            pd.concat([dfg, pd.DataFrame([{"codigo": gc.strip(), "articulo": ga.strip(), "modulo": gm, "descripcion": gd.strip()}])], ignore_index=True).to_csv(F_GLO, index=False); st.rerun()

elif vista == "➕ Cargar Stock":
    c1, c2 = st.columns(2)
    cod, nom = c1.text_input("Número de Serie / Código*:"), c2.text_input("Nombre del Artículo*:")
    mod, cat = c1.selectbox("Módulo*:", MODULOS), c2.text_input("Categoría:")
    est, cant = c1.selectbox("Estado:", ESTADOS), c2.number_input("Cantidad:", min_value=1, value=1)
    if st.button("Guardar Artículo", type="primary") and cod.strip() and nom.strip():
        df = cargar_inv()
        if cod.strip() in df["numero_serie"].values: st.warning("Ese código ya existe.")
        else:
            pd.concat([df, pd.DataFrame([{"numero_serie": cod.strip(), "articulo": nom.strip(), "modulo": mod, "categoria": cat.strip(), "estado": est, "cantidad": int(cant)}])], ignore_index=True).to_csv(F_INV, index=False); st.success(f"✅ Guardado en {mod}.")

elif vista == "📤 Entregas":
    df = cargar_inv(); cli = st.text_input("Receptor / Destinatario:")
    lista_art = [f"{r['numero_serie']} - {r['articulo']} (Disp: {r['cantidad']})" for _, r in df.iterrows()] if not df.empty else ["Sin artículos cargados aún"]
    sel_art = st.selectbox("Artículo / Serie:", lista_art); ce, obs = st.number_input("Cantidad:", min_value=1, value=1), st.text_area("Observaciones:")
    if st.button("Confirmar Entrega y Generar Remito", type="primary") and not df.empty and cli.strip():
        ser = sel_art.split(" - ")[0].strip(); idx = df.index[df["numero_serie"] == ser].tolist()[0]
        if int(df.at[idx, "cantidad"]) >= ce:
            df.at[idx, "cantidad"] = int(df.at[idx, "cantidad"]) - ce; df.to_csv(F_INV, index=False)
            st.session_state["pdf"] = pdf_remito(cli, ser, ce, obs, str(df.at[idx, "articulo"])); st.success("✅ Entrega registrada:")
        else: st.error("Stock insuficiente.")
    if "pdf" in st.session_state: st.download_button("📄 Descargar Remito PDF", data=st.session_state["pdf"], file_name="Remito.pdf", mime="application/pdf", type="primary")

elif vista == "✏️ Editar Stock": mostrar_editar(cargar_inv, F_INV, MODULOS, ESTADOS)
elif vista == "💾 Backup Oficina": mostrar_backup(cargar_inv, cargar_glo, cargar_usu, F_INV, F_GLO, F_USU)
elif vista == "👥 Usuarios": mostrar_usuarios(cargar_usu, F_USU, VISTAS)
