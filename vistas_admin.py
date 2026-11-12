import streamlit as st, pandas as pd, io, os
from datetime import datetime

def mostrar_chat(cargar_inv, modulos, estados, usr):
    f_hist = "historial_consultas.csv"
    df_h = pd.read_csv(f_hist, dtype=str).fillna("") if os.path.exists(f_hist) else pd.DataFrame(columns=["fecha", "usuario", "pregunta", "util"])
    c_chat, c_mem = st.columns([2, 1])
    with c_mem:
        st.markdown("#### 📌 Consultas Guardadas")
        utiles = df_h[df_h["util"] == "Si"]["pregunta"].drop_duplicates().tolist()
        if utiles:
            for idx_u, u_q in enumerate(utiles):
                if st.button(f"⭐ {u_q}", key=f"u_{idx_u}", use_container_width=True): st.session_state["q_rapida"] = u_q
        else: st.caption("Todavía no marcaste consultas útiles.")
        st.divider()
        st.markdown("#### 🕒 Últimas Preguntas")
        for idx_r, r in df_h.tail(6).iloc[::-1].iterrows():
            col_q, col_s = st.columns([4, 1])
            col_q.caption(f"**{r['usuario']}**: {r['pregunta']}")
            if col_s.button("⭐", key=f"star_{idx_r}", help="Guardar como útil"):
                df_h.at[idx_r, "util"] = "Si"; df_h.to_csv(f_hist, index=False); st.rerun()
    with c_chat:
        pregunta = st.chat_input("Escribí tu consulta (ej: 'stock en Robótica', 'equipos en Baja', 'resumen')...")
        if not pregunta and "q_rapida" in st.session_state: pregunta = st.session_state.pop("q_rapida")
        if pregunta:
            df = cargar_inv(); q_low = pregunta.lower()
            df_h = pd.concat([df_h, pd.DataFrame([{"fecha": datetime.now().strftime("%d/%m %H:%M"), "usuario": usr.get("nombre", "Usuario"), "pregunta": pregunta, "util": "No"}])], ignore_index=True)
            df_h.to_csv(f_hist, index=False)
            with st.chat_message("user"): st.write(pregunta)
            with st.chat_message("assistant"):
                if df.empty: st.write("El inventario está vacío por el momento.")
                elif "resumen" in q_low or "total" in q_low:
                    st.write(f"Hay **{int(df['cantidad'].sum())}** unidades en total distribuidas así:")
                    st.dataframe(df.groupby("modulo", as_index=False)["cantidad"].sum(), use_container_width=True, hide_index=True)
                elif "critico" in q_low or "crítico" in q_low or "agotado" in q_low or "poco" in q_low:
                    sub = df[df["cantidad"] <= 1]; st.write(f"Encontré **{len(sub)}** artículos con stock crítico (1 unidad o menos):")
                    st.dataframe(sub, use_container_width=True, hide_index=True)
                else:
                    mod_hit = next((m for m in modulos if m.lower() in q_low), None)
                    est_hit = next((e for e in estados if e.lower() in q_low), None)
                    sub = df.copy()
                    if mod_hit: sub = sub[sub["modulo"] == mod_hit]
                    if est_hit: sub = sub[sub["estado"] == est_hit]
                    palabras = [w for w in q_low.replace("?", "").split() if len(w) > 3 and w not in ["stock", "hay", "cuantos", "cuántos", "modulo", "módulo", "estado", "mostrar", "ver", "que", "qué", "los", "las", "del", "para"]]
                    if not mod_hit and not est_hit and palabras:
                        mask = sub.astype(str).apply(lambda x: x.str.contains("|".join(palabras), case=False, na=False)).any(axis=1)
                        sub = sub[mask]
                    st.write(f"Encontré **{len(sub)}** coincidencias (**{int(sub['cantidad'].sum())}** unidades en total):")
                    st.dataframe(sub, use_container_width=True, hide_index=True)

def mostrar_editar(cargar_inv, f_inv, modulos, estados):
    df = cargar_inv()
    if df.empty: st.info("No hay artículos cargados todavía para editar.")
    else:
        sel = st.selectbox("Seleccioná el Número de Serie:", df["numero_serie"].tolist())
        idx = df.index[df["numero_serie"] == sel].tolist()[0]; c1, c2 = st.columns(2)
        enom, emod = c1.text_input("Artículo:", value=str(df.at[idx, "articulo"])), c2.selectbox("Módulo:", modulos, index=modulos.index(df.at[idx, "modulo"]) if df.at[idx, "modulo"] in modulos else 7)
        ecat, eest = c1.text_input("Categoría:", value=str(df.at[idx, "categoria"])), c2.selectbox("Estado:", estados, index=estados.index(df.at[idx, "estado"]) if df.at[idx, "estado"] in estados else 0)
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
        if os.path.exists("historial_consultas.csv"): pd.read_csv("historial_consultas.csv").to_excel(w, sheet_name="Historial_Chat", index=False)
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
