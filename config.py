"""Globale Konfigurationseinstellungen für die 9 Freunde App."""
import streamlit as st
import os

# Standard-Zeitzone
DEFAULT_TIMEZONE = "Europe/Berlin"
# OpenAI Modell falls nicht anders konfiguriert
DEFAULT_OPENAI_MODEL = "text-davinci-003"
# Optionale Einstellungen aus Umgebungsvariablen (Fallbacks)
OPENAI_API_KEY = st.secrets.get('openai', {}).get('api_key', os.getenv('OPENAI_API_KEY'))
GOOGLE_PHOTOS_FOLDER = st.secrets.get('gcp', {}).get('photos_folder_id')
