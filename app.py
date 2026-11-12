# --- ENCABEZADO Y MENÚ DE USUARIO ---
c_tit, c_menu = st.columns([5, 1])
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
