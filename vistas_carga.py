import streamlit as st
import pandas as pd

def mostrar_cargar_stock(cargar_inv, F_INV, MODULOS, ESTADOS):
    tab1, tab2 = st.tabs(["✍️ Carga Manual", "📥 Carga Masiva (Excel / CSV)"])

    with tab1:
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
                fila = pd.DataFrame([{"numero_serie": cod.strip(), "articulo": nom.strip(), "modulo": mod, "categoria": cat.strip(), "estado": est, "cantidad": int(cant)}])
                pd.concat([df, fila], ignore_index=True).to_csv(F_INV, index=False)
                st.success("✅ Artículo guardado.")
                st.rerun()

    with tab2:
        st.info("Columnas requeridas: numero_serie, articulo, modulo, categoria, estado, cantidad")
        archivo = st.file_uploader("Subir archivo (.xlsx o .csv)", type=["xlsx", "csv"], key="up_excel")
        if archivo is not None:
            df_sub = pd.read_csv(archivo, dtype={"numero_serie": str}) if archivo.name.endswith(".csv") else pd.read_excel(archivo, dtype={"numero_serie": str})
            df_sub.columns = [c.strip().lower() for c in df_sub.columns]
            cols = ["numero_serie", "articulo", "modulo", "categoria", "estado", "cantidad"]
            if all(col in df_sub.columns for col in cols):
                st.dataframe(df_sub[cols].head(10), use_container_width=True, hide_index=True)
                if st.button("Importar al Inventario", type="primary"):
                    df_act = cargar_inv()
                    df_lim = df_sub[cols].dropna(subset=["numero_serie", "articulo"]).copy()
                    df_lim["numero_serie"] = df_lim["numero_serie"].str.strip()
                    df_lim["modulo"] = df_lim["modulo"].fillna("General")
                    df_lim["estado"] = df_lim["estado"].fillna("Nuevo")
                    df_lim["cantidad"] = pd.to_numeric(df_lim["cantidad"], errors="coerce").fillna(1).astype(int)
                    df_nuevos = df_lim[~df_lim["numero_serie"].isin(df_act["numero_serie"])]
                    if not df_nuevos.empty:
                        pd.concat([df_act, df_nuevos], ignore_index=True).to_csv(F_INV, index=False)
                        st.success(f"✅ Se importaron {len(df_nuevos)} artículos nuevos.")
                    else:
                        st.warning("Todos los códigos ya existen en el inventario.")
            else:
                st.error(f"Faltan columnas. Tu archivo tiene: {list(df_sub.columns)}")

def mostrar_entregas(cargar_inv, F_INV, pdf_remito):
    df = cargar_inv()
    disp = df[df["cantidad"] > 0]
    if disp.empty:
        st.info("No hay artículos con stock disponible.")
        return
    opciones_art = {f"{r['articulo']} (Serie: {r['numero_serie']} | Disp: {r['cantidad']})": r["numero_serie"] for _, r in disp.iterrows()}
    sel = st.selectbox("Seleccionar Artículo:", list(opciones_art.keys()))
    ser_sel = opciones_art[sel]
    fila = disp[disp["numero_serie"] == ser_sel].iloc[0]
    c1, c2 = st.columns(2)
    receptor = c1.text_input("Receptor / Área destino*:")
    cant_ent = c2.number_input("Cantidad a entregar:", min_value=1, max_value=int(fila["cantidad"]), value=1)
    obs = st.text_input("Observaciones:")
    if st.button("Confirmar Entrega y Generar Remito", type="primary") and receptor.strip():
        df.loc[df["numero_serie"] == ser_sel, "cantidad"] -= int(cant_ent)
        df.to_csv(F_INV, index=False)
        pdf_bytes = pdf_remito(receptor.strip(), ser_sel, int(cant_ent), obs.strip(), fila["articulo"])
        st.success("✅ Entrega registrada.")
        st.download_button("📄 Descargar Remito PDF", data=pdf_bytes, file_name=f"remito_{ser_sel}.pdf", mime="application/pdf", type="primary")
