import streamlit as st
import openai
from datetime import datetime
from docx import Document

class DocumentAgent:
    def __init__(self):
        # OpenAI API-Schlüssel setzen
        api_key = None
        if 'openai' in st.secrets and 'api_key' in st.secrets['openai']:
            api_key = st.secrets['openai']['api_key']
        elif 'openai_api_key' in st.secrets:
            api_key = st.secrets['openai_api_key']
        if api_key:
            openai.api_key = api_key
        # Modell setzen (optional via Config)
        model = None
        if 'openai' in st.secrets and 'model' in st.secrets['openai']:
            model = st.secrets['openai']['model']
        self.model = model or 'text-davinci-003'

    def generate_document(self, child_data: dict, notes: str):
        """Generiert einen Dokumenttext mit OpenAI und erstellt ein Word-Dokument (als Bytes)."""
        child_name = child_data.get('name', 'Ihr Kind')
        prompt = (f"Schreibe einen kurzen Bericht für die Eltern von {child_name}.\n" 
                  f"Hier sind Notizen der Betreuungsperson: {notes}\n" 
                  "Formuliere den Text warmherzig, professionell und verständlich.")
        # API-Aufruf an OpenAI
        response = openai.Completion.create(
            engine=self.model,
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        text = response.choices[0].text.strip()
        # Word-Dokument erstellen
        doc = Document()
        doc.add_heading(f"Bericht für {child_name}", level=1)
        today_str = datetime.now().strftime("%d.%m.%Y")
        doc.add_paragraph(f"Datum: {today_str}")
        doc.add_paragraph("")  # Leerzeile
        doc.add_paragraph(text)
        # Als Bytes speichern
        from io import BytesIO
        output = BytesIO()
        doc.save(output)
        doc_bytes = output.getvalue()
        # Dateiname generieren
        safe_name = child_name.replace(" ", "_")
        date_stamp = datetime.now().strftime("%Y%m%d")
        file_name = f"Bericht_{safe_name}_{date_stamp}.docx"
        return doc_bytes, file_name
