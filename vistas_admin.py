
import streamlit as st, pandas as pd, io
from datetime import datetime

def mostrar_editar(cargar_inv, f_inv, modulos, estados):
    df = cargar_inv()
    if df.empty:
        st.info("No hay artículos cargados todavía para editar.")
    else:
        sel = st.selectbox("Seleccioná el Número de Serie:", df["numero_serie"].tolist())
        idx = df.index[df["numero_serie"] == sel].tolist()[0]
        c1, c2 = st.columns(2)
        enom = c1.text_input("Artículo:", value=str(df.at[idx, "articulo"]))
        emod = c2.selectbox("Módulo:", modulos, index=modulos.index(df.at[idx, "modulo"]) if df.at[idx, "modulo"] in modulos else 7)
        ecat = c1.text_input("Categoría:", value=str(df.at[idx, "categoria"]))
        eest = c2.selectbox("Estado:", estados, index=estados.index(df.at[idx, "estado"]) if df.at[idx, "estado"] in estados else 0)
        ecant = c1.number_input("Cantidad:", min_value=0, value=int(df.at[idx, "cantidad"]))
        if st.button("Guardar Cambios", type="primary"):
            df.at[idx, "articulo"], df.at[idx, "modulo"], df.at[idx, "categoria"], df.at[idx, "estado"], df.at[idx, "cantidad"] = enom.strip(), emod, ecat.strip(), eest, int(ecant)
            df.to_csv(f_inv, index=False); st.success("✅ Actualizado."); st.rerun()

def mostrar_backup(cargar_inv, cargar_glo, cargar_usu, f_inv, f_glo, f_usu):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        cargar_inv().to_excel(w, sheet_name="Inventario", index=False)
        cargar_glo().to_excel(w, sheet_name="Glosario", index=False)
        pd.DataFrame(cargar_usu()).to_excel(w, sheet_name="Usuarios", index=False)
    buf.seek(0)
    st.download_button("📥 Descargar Backup Excel (.xlsx)", data=buf.getvalue(), file_name=f"Backup_Stock_{datetime.now().strftime('%Y-%m-%d')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")
    up = st.file_uploader("Restaurar Backup (.xlsx)", type=["xlsx"])
    if up and st.button("Restaurar Datos"):
        xls = pd.ExcelFile(up)
        if "Inventario" in xls.sheet_names: pd.read_excel(xls, "Inventario").to_csv(f_inv, index=False)
        if "Glosario" in xls.sheet_names: pd.read_excel(xls, "Glosario").to_csv(f_glo, index=False)
        if "Usuarios" in xls.sheet_names: pd.read_excel(xls, "Usuarios").to_csv(f_usu, index=False)
        st.success("✅ Restaurado."); st.rerun()

def mostrar_usuarios(cargar_usu, f_usu, vistas):
    lu = cargar_usu()
    st.dataframe(pd.DataFrame(lu)[["usuario", "nombre", "rol", "permisos"]], use_container_width=True, hide_index=True)
    st.subheader("➕ Crear Usuario y Elegir Permisos")
    c1, c2, c3, c4 = st.columns(4)
    un, uu, up, ur = c1.text_input("Nombre:"), c2.text_input("Usuario:"), c3.text_input("Clave:", type="password"), c4.selectbox("Perfil Base:", ["Revisor", "Stock", "Administrador"])
    p_cols = st.columns(4)
    elegidos = [v for i, v in enumerate(vistas) if p_cols[i % 4].checkbox(v, value=(ur=="Administrador" or (ur=="Stock" and i<6) or (ur=="Revisor" and i<3)), key=f"c_{v}")]
    if st.button("Guardar Usuario", type="primary") and uu.strip() and up.strip():
        if not any(x["usuario"] == uu.strip() for x in lu):
            lu.append({"nombre": un.strip() or uu.strip(), "usuario": uu.strip(), "clave": up.strip(), "rol": ur, "permisos": "|".join(elegidos)})
            pd.DataFrame(lu).to_csv(f_usu, index=False); st.success("✅ Usuario creado."); st.rerun()
        else: st.error("Ese usuario ya existe.")
