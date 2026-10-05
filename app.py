import streamlit as st
import pandas as pd
import time
from curl_cffi import requests

# Configuración de la página
st.set_page_config(page_title="Control BCRA | FINETIA", page_icon="🔍", layout="centered")
st.title("🔍 Consulta de Situación y eCheqs BCRA")
st.markdown("Ingresá el CUIT del cliente para validar su situación crediticia y cheques rechazados.")

def verificar_cuit_bcra(cuit):
    cuit = str(cuit).replace("-", "").strip()
    urls = {
        "home": "https://www.bcra.gob.ar/",
        "deudas": f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/{cuit}",
        "cheques": f"https://api.bcra.gob.ar/centraldedeudores/v1.0/Deudas/ChequesRechazados/{cuit}"
    }
    
    peor_situacion = None
    denominacion = "Razón social no encontrada"
    df_deudas = pd.DataFrame()
    df_cheques = pd.DataFrame()
    mensaje_error = None
    
    sesion_bcra = requests.Session(impersonate="chrome120")
    sesion_bcra.headers.update({
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "es-AR,es;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "keep-alive"
    })
    
    try:
        # Calentamiento de sesión para evadir el WAF
        sesion_bcra.get(urls["home"], timeout=15)
        time.sleep(1.5)
        
        sesion_bcra.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Referer": urls["home"]
        })

        # Consulta Deudas
        res_deudas = sesion_bcra.get(urls["deudas"], timeout=20)
        if res_deudas.status_code == 200:
            respuesta = res_deudas.json()
            if respuesta.get("status") == 200 and "results" in respuesta:
                resultados = respuesta["results"]
                denominacion = resultados.get("denominacion", denominacion)
                periodos = resultados.get("periodos", [])
                if periodos:
                    entidades = periodos[0].get("entidades", [])
                    deudas_lista = []
                    peor_situacion = 1
                    for ent in entidades:
                        sit = int(ent.get("situacion", 1))
                        peor_situacion = max(peor_situacion, sit)
                        deudas_lista.append({
                            "Entidad": ent.get("entidad"),
                            "Monto (Miles $)": ent.get("monto"),
                            "Situación": sit
                        })
                    df_deudas = pd.DataFrame(deudas_lista)
        else:
            mensaje_error = f"Bloqueo HTTP en deudas: {res_deudas.status_code}"

        time.sleep(1.5)

        # Consulta Cheques
        res_cheques = sesion_bcra.get(urls["cheques"], timeout=20)
        if res_cheques.status_code == 200:
            respuesta = res_cheques.json()
            if respuesta.get("status") == 200 and "results" in respuesta:
                cheques_lista = []
                for causal in respuesta["results"].get("causales", []):
                    motivo_causal = causal.get("causal")
                    for entidad in causal.get("entidades", []):
                        for cheque in entidad.get("detalle", []):
                            cheques_lista.append({
                                "Nro Cheque": cheque.get("nroCheque"),
                                "Causal": motivo_causal,
                                "Fecha Rechazo": cheque.get("fechaRechazo"),
                                "Monto ($)": cheque.get("monto"),
                                "Estado": "Levantado" if cheque.get("fechaPago") else "Impago"
                            })
                df_cheques = pd.DataFrame(cheques_lista)

        return denominacion, peor_situacion, df_deudas, df_cheques, mensaje_error
        
    except Exception as e:
        return denominacion, None, pd.DataFrame(), pd.DataFrame(), f"Falla de red: {str(e)}"

# ==========================================
# INTERFAZ DE USUARIO
# ==========================================
cuit_input = st.text_input("CUIT del cliente (sin guiones):", placeholder="Ej: 33708633009")

if st.button("Consultar BCRA", type="primary"):
    if not cuit_input:
        st.warning("⚠️ Por favor, ingresá un número de CUIT.")
    else:
        with st.spinner("Conectando de forma segura con el BCRA (tomará unos segundos)..."):
            denominacion, peor_sit, tabla_deudas, tabla_cheques, error = verificar_cuit_bcra(cuit_input)
            
            if error:
                st.error(f"⚠️ Error detectado: {error}")
            else:
                st.success(f"Resultados para: **{denominacion}** (CUIT: {cuit_input})")
                
                # Sección Deudas
                st.subheader("Situación Crediticia")
                if peor_sit is not None:
                    color = "red" if peor_sit >= 3 else "orange" if peor_sit == 2 else "green"
                    st.markdown(f"**Peor Situación Registrada:** <span style='color:{color}; font-size:20px'><b>{peor_sit}</b></span>", unsafe_allow_html=True)
                    if not tabla_deudas.empty:
                        st.dataframe(tabla_deudas, use_container_width=True)
                else:
                    st.info("No se encontraron registros de deudas bancarias para este CUIT.")
                
                st.divider()
                
                # Sección Cheques
                st.subheader(f"Historial de Cheques Rechazados ({len(tabla_cheques)} registros)")
                if not tabla_cheques.empty:
                    # Función para pintar de rojo los impagos
                    def color_estado(val):
                        color = 'red' if val == 'Impago' else 'green'
                        return f'color: {color}; font-weight: bold'
                    
                    # Soporte automático para distintas versiones de Pandas
                    try:
                        st.dataframe(tabla_cheques.style.map(color_estado, subset=['Estado']), use_container_width=True)
                    except AttributeError:
                        st.dataframe(tabla_cheques.style.applymap(color_estado, subset=['Estado']), use_container_width=True)
                else:
                    st.info("El CUIT no registra antecedentes de cheques rechazados.")
