import streamlit as st
import requests
import io
from datetime import datetime
import json
import time

def split_text_for_tts(text, max_chars=250):
    """
    Divide el texto en fragmentos más pequeños respetando:
    1. Puntos finales
    2. Máximo de caracteres
    3. Estructura de párrafos
    4. División por comas en oraciones largas
    """
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    fragments = []
    current_fragment = ""
    
    for paragraph in paragraphs:
        if len(paragraph) <= max_chars:
            fragments.append(paragraph)
            continue
            
        sentences = [s.strip() + '.' for s in paragraph.replace('. ', '.').split('.') if s.strip()]
        
        for sentence in sentences:
            if len(sentence) > max_chars:
                parts = sentence.split(',')
                current_part = ""
                
                for part in parts:
                    part = part.strip()
                    if len(current_part) + len(part) + 2 <= max_chars:
                        current_part = (current_part + ", " + part).strip(", ")
                    else:
                        if current_part:
                            fragments.append(current_part + ".")
                        current_part = part
                
                if current_part:
                    fragments.append(current_part + ".")
                    
            elif len(current_fragment + sentence) > max_chars:
                if current_fragment:
                    fragments.append(current_fragment.strip())
                current_fragment = sentence
            else:
                current_fragment = (current_fragment + " " + sentence).strip()
        
        if current_fragment:
            fragments.append(current_fragment)
            current_fragment = ""
    
    if current_fragment:
        fragments.append(current_fragment)
    
    return fragments

def generate_audio(text, api_key, voice_id, model_id="eleven_monolingual_v1"):
    """
    Genera audio usando la API de Eleven Labs
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Error en la generación de audio: {response.status_code}")
            return None
    except Exception as e:
        st.error(f"Error en la solicitud: {str(e)}")
        return None

def get_available_voices(api_key):
    """
    Obtiene la lista de voces disponibles de Eleven Labs
    """
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            voices = response.json()["voices"]
            return {voice["name"]: voice["voice_id"] for voice in voices}
        return {}
    except:
        return {}

def main():
    st.title("🎙️ Generador de Audio con Eleven Labs")
    st.write("Divide tu texto y genera audio de alta calidad")
    
    # Configuración en la barra lateral
    st.sidebar.header("Configuración")
    
    # Explicación del proceso de división
    st.sidebar.markdown("""
    ### 📝 Reglas de división del texto
    El texto se divide siguiendo estas reglas:
    1. ✅ Respeta los puntos finales
    2. ✅ Mantiene la estructura de párrafos
    3. ✅ Divide oraciones largas por comas
    4. ✅ No excede el límite de caracteres
    """)
    
    api_key = st.sidebar.text_input("API Key de Eleven Labs", type="password")
    
    # Configuración de caracteres con explicación
    st.sidebar.markdown("""
    ### ⚙️ Configuración de fragmentos
    Ajusta el número máximo de caracteres por fragmento.
    Para mejor calidad, se recomienda entre 200-250 caracteres.
    """)
    
    max_chars = st.sidebar.number_input("Máximo de caracteres por fragmento", 
                                      min_value=100, 
                                      max_value=500, 
                                      value=250,
                                      help="Se respetarán los puntos finales y la estructura del texto")
    
    # Obtener voces disponibles si hay API key
    if api_key:
        voices = get_available_voices(api_key)
        if voices:
            st.sidebar.markdown("### 🎤 Selección de voz")
            selected_voice_name = st.sidebar.selectbox("Seleccionar voz", 
                                                     list(voices.keys()))
            voice_id = voices[selected_voice_name]
        else:
            st.sidebar.error("No se pudieron cargar las voces. Verifica tu API key.")
            return
    
    # Área principal
    text_input = st.text_area("Ingresa tu texto", height=200)
    
    if st.button("Procesar texto"):
        if not text_input:
            st.warning("Por favor ingresa algún texto.")
            return
            
        if not api_key:
            st.warning("Por favor ingresa tu API key de Eleven Labs.")
            return
        
        # Dividir el texto
        fragments = split_text_for_tts(text_input, max_chars)
        
        # Mostrar fragmentos con análisis
        st.subheader("📊 Análisis de fragmentos")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"Total de fragmentos: {len(fragments)}")
        with col2:
            st.info(f"Promedio de caracteres: {sum(len(f) for f in fragments)/len(fragments):.1f}")
        
        for i, fragment in enumerate(fragments, 1):
            with st.expander(f"Fragmento {i} - {len(fragment)} caracteres"):
                st.write(fragment)
                st.markdown("---")
                st.caption("✓ Termina en punto" if fragment.strip().endswith(".") else "")
                
        # Generar audio para cada fragmento
        st.subheader("🎵 Generación de audio")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_audios = []
        for i, fragment in enumerate(fragments, 1):
            status_text.text(f"Generando audio {i}/{len(fragments)}...")
            audio_content = generate_audio(fragment, api_key, voice_id)
            
            if audio_content:
                all_audios.append(audio_content)
                with st.expander(f"Audio fragmento {i}"):
                    st.audio(audio_content, format="audio/mp3")
                    st.write(fragment)
            
            progress_bar.progress(i/len(fragments))
            time.sleep(1)  # Pequeña pausa para evitar límites de rate
        
        status_text.text("¡Proceso completado!")
        
        # Opción para descargar todos los audios
        if all_audios:
            st.subheader("💾 Descargar audios")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            for i, audio in enumerate(all_audios, 1):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"Fragmento {i}")
                with col2:
                    st.download_button(
                        label=f"⬇️ Descargar",
                        data=audio,
                        file_name=f"audio_{timestamp}_parte_{i}.mp3",
                        mime="audio/mp3"
                    )

if __name__ == "__main__":
    main()
