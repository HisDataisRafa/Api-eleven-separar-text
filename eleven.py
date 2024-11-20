import streamlit as st
import librosa
import soundfile as sf
import numpy as np
import io
import os
import tempfile
import scipy.io.wavfile
from scipy.signal import find_peaks

def analyze_pitch_distribution(y, sr, frame_length=2048, hop_length=512):
    pitches, magnitudes = librosa.piptrack(
        y=y, 
        sr=sr,
        n_fft=frame_length,
        hop_length=hop_length,
        fmin=50,  # Lowered to catch deeper voices
        fmax=400  # Adjusted for multilingual range
    )
    
    pitch_values = []
    for i in range(magnitudes.shape[1]):
        index = magnitudes[:, i].argmax()
        if magnitudes[index, i] > 0:
            pitch_values.append(pitches[index, i])
    
    pitch_values = np.array(pitch_values)
    hist, bins = np.histogram(pitch_values, bins=100, range=(50, 400))
    hist_smooth = np.convolve(hist, np.hamming(10), mode='same')
    peaks, _ = find_peaks(hist_smooth, distance=20, prominence=max(hist_smooth)*0.1)
    
    peak_frequencies = bins[peaks]
    peak_magnitudes = hist_smooth[peaks]
    sorted_indices = np.argsort(peak_magnitudes)[::-1]
    
    return peak_frequencies[sorted_indices][:2]

def separate_voice_by_pitch(y, sr, target_pitch, stability=0.5, similarity=0.75):
    frame_length = 2048
    hop_length = 512
    
    # Adjust window size based on stability
    window_size = int(2048 * (1 - stability))  # Smaller window for more variable output
    
    pitches, magnitudes = librosa.piptrack(
        y=y, 
        sr=sr,
        n_fft=frame_length,
        hop_length=hop_length,
        fmin=50,
        fmax=400,
        win_length=window_size
    )
    
    pitch_mean = []
    for i in range(magnitudes.shape[1]):
        index = magnitudes[:, i].argmax()
        pitch_mean.append(pitches[index, i])
    
    pitch_mean = np.array(pitch_mean)
    
    # Adjust tolerance based on similarity
    tolerance = 30 * (1 - similarity)  # Tighter tolerance for higher similarity
    
    mask = np.abs(pitch_mean - target_pitch) <= tolerance
    mask_smooth = np.convolve(mask.astype(float), np.ones(15)/15, mode='same')
    mask_full = np.repeat(mask_smooth, hop_length)[:len(y)]
    
    voice_separated = y * mask_full
    return librosa.util.normalize(voice_separated)

def process_audio(audio_file):
    try:
        temp_dir = tempfile.mkdtemp()
        temp_input = os.path.join(temp_dir, "input.mp3")
        
        with open(temp_input, "wb") as f:
            f.write(audio_file.getvalue())
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        status_text.text("Analyzing audio...")
        progress_bar.progress(20)
        y, sr = librosa.load(temp_input, sr=None)
        y = librosa.util.normalize(y)
        
        dominant_pitches = analyze_pitch_distribution(y, sr)
        progress_bar.progress(40)
        
        status_text.text("Separating voices...")
        voices = []
        for i, pitch in enumerate(dominant_pitches):
            separated = separate_voice_by_pitch(y, sr, pitch, stability=0.5, similarity=0.75)
            voice_int = np.int16(separated * 32767)
            voice_buffer = io.BytesIO()
            scipy.io.wavfile.write(voice_buffer, sr, voice_int)
            voices.append((pitch, voice_buffer.getvalue()))
            progress_bar.progress(60 + i*20)
        
        progress_bar.progress(100)
        status_text.text("Done!")
        
        return voices
        
    finally:
        for file in os.listdir(temp_dir):
            try:
                os.remove(os.path.join(temp_dir, file))
            except:
                pass
        try:
            os.rmdir(temp_dir)
        except:
            pass

st.title("Voice Separator (Eleven Multilingual v2)")
st.write("Optimized for multilingual voice separation with enhanced stability and similarity control")

uploaded_file = st.file_uploader("Choose MP3 file", type=['mp3'])

if uploaded_file:
    if st.button("Process Audio"):
        voices = process_audio(uploaded_file)
        
        for i, (pitch, voice_data) in enumerate(voices, 1):
            st.download_button(
                label=f"Download Voice {i} (Pitch: {pitch:.1f}Hz)",
                data=voice_data,
                file_name=f"voice_{i}_{pitch:.1f}hz.wav",
                mime="audio/wav"
            )
