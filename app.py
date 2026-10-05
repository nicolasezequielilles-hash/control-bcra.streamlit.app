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
                            "Entidad": ent.get
