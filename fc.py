import io
import re
import pandas as pd
import streamlit as st
from pypdf import PdfReader

# Configuración de la página web
st.set_page_config(page_title="Lector Profesional de Facturas", page_icon="📄", layout="wide")

# --- SISTEMA DE CRÉDITOS ANÓNIMOS POR NAVEGADOR ---
if "creditos_anonimos" not in st.session_state:
    st.session_state.creditos_anonimos = 15

st.title("📄 Lector Automático de Facturas y Albaranes")
st.markdown("Sube tus archivos PDF digitales para extraer **Proveedor, CIF, Fecha y Total**.")

# Barra lateral informativa
with st.sidebar:
    st.header("⚡ Tus Pruebas Gratis")
    st.metric(label="Facturas disponibles ahora", value=st.session_state.creditos_anonimos)
    
    if st.session_state.creditos_anonimos <= 0:
        st.error("¡Has agotado tus 15 facturas gratuitas!")
        st.markdown("---")
        st.subheader("🔓 Versión Ilimitada")
        st.markdown("Desbloquea procesamiento ilimitado para tu negocio.")
        st.link_button("💳 Suscribirse a Pro (15€/mes)", "https://buy.stripe.com/tu-enlace-de-pago")
    else:
        st.info("💡 No necesitas registrarte. Disfruta de tus facturas de prueba gratuitas.")

def extraer_texto_pdf_digital(archivo_pdf) -> str:
    texto = ""
    try:
        lector = PdfReader(archivo_pdf)
        for pagina in lector.pages:
            t = pagina.extract_text()
            if t: texto += t + "\n"
    except Exception as e:
        pass
    return texto

def analizar_factura_texto(texto: str):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    # --- 1. DETECCIÓN DE PROVEEDOR ---
    proveedor = "No encontrado"
    for linea in lineas[:10]:
        if (len(linea) > 3 and 
            not re.search(r'\d{2}:\d{2}', linea) and 
            not re.search(r'\d{4}-\d{2}-\d{2}', linea) and
            not any(w in linea.lower() for w in ['factura', 'ticket', 'fecha', 'cif', 'nif', 'entrada', 'salida', 'albarán', 'página'])):
            proveedor = linea
            break
            
    if proveedor == "No encontrado" and lineas:
        proveedor = lineas[0]

    # --- 2. DETECCIÓN DE CIF / NIF ---
    cif = "No encontrado"
    cif_match = re.search(r'(?:cif|nif|id|sociedad|empresa|rut)[\s.:]*([ABCDEFGHJKLMNPQRSUVW][0-9]{7}[0-9A-J]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE])', texto, re.IGNORECASE)
    if cif_match:
        cif = cif_match.group(1)
    else:
        cif_gen = re.search(r'\b([ABCDEFGHJKLMNPQRSUVW][0-9]{7}[0-9A-J]|[0-9]{8}[TRWAGMYFPDXBNJZSQVHLCKE])\b', texto, re.IGNORECASE)
        if cif_gen: 
            cif = cif_gen.group(0)

    # --- 3. DETECCIÓN DE FECHA ---
    fecha = "No encontrada"
    patrones_fecha = [
        r'\b(20\d{2})[-/.](0[1-9]|1[012])[-/.](0[1-9]|[12][0-9]|3[01])\b',
        r'\b(0[1-9]|[12][0-9]|3[01])[-/.](0[1-9]|1[012])[-/.](20\d{2})\b',
        r'\b(0[1-9]|[12][0-9]|3[01])\s+(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+(?:de\s+)?20\d{2}\b'
    ]
    
    for patron in patrones_fecha:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            fecha = match.group(0)
            break

    # --- 4. DETECCIÓN DE TOTAL (Estricta y Segura) ---
    total = "No encontrado"
    
    # Buscamos de abajo hacia arriba la línea que contenga la palabra total explícita
    for linea in reversed(lineas):
        ll = linea.lower()
        if any(p in ll for p in ['total', 'a pagar', 'importe total', 'total factura', 'total a pagar']):
            if 'subtotal' not in ll and 'base' not in ll and 'iva' not in ll:
                nums = re.findall(r'\d{1,3}(?:[.,]\d{3})*[.,]\d{2}', linea)
                if nums:
                    total = nums[-1]
                    break

    return {"proveedor": proveedor, "cif_proveedor": cif, "fecha_emision": fecha, "total_factura": total}

# --- ZONA DE CARGA EN LA WEB ---
uploaded_files = st.file_uploader(
    "Arrastra y suelta tus facturas PDF aquí", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    if st.session_state.creditos_anonimos <= 0:
        st.error("⚠️ Has agotado tus 15 pruebas gratuitas. Adquiere la versión ilimitada en la barra lateral.")
    else:
        num_archivos = len(uploaded_files)
        
        if num_archivos > st.session_state.creditos_anonimos:
            st.warning(f"⚠️ Intentas procesar {num_archivos} archivos, pero solo te quedan {st.session_state.creditos_anonimos} créditos gratuitos.")
        else:
            st.markdown("### 📊 Resultados del Análisis")
            resultados_globales = []

            for f in uploaded_files:
                texto = extraer_texto_pdf_digital(f)
                datos = analizar_factura_texto(texto)
                
                resultados_globales.append({
                    "Archivo": f.name,
                    "Proveedor": datos["proveedor"],
                    "CIF": datos["cif_proveedor"],
                    "Fecha": datos["fecha_emision"],
                    "Total (€)": datos["total_factura"]
                })

            # Descontar créditos usados
            st.session_state.creditos_anonimos -= num_archivos

            df_resultados = pd.DataFrame(resultados_globales)
            st.dataframe(df_resultados, use_container_width=True)
            
            st.success(f"¡Se han procesado {num_archivos} archivos correctamente! Te quedan {st.session_state.creditos_anonimos} créditos de prueba.")

            # --- BOTONES DE DESCARGA ---
            col1, col2 = st.columns(2)

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_resultados.to_excel(writer, index=False, sheet_name='Facturas')
            excel_data = output.getvalue()

            with col1:
                st.download_button(
                    label="📥 Descargar resultados en EXCEL (.xlsx)",
                    data=excel_data,
                    file_name="facturas_procesadas.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            csv_data = df_resultados.to_csv(index=False).encode('utf-8')
            with col2:
                st.download_button(
                    label="📥 Descargar resultados en CSV",
                    data=csv_data,
                    file_name="facturas_procesadas.csv",
                    mime="text/csv"
                )
