import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import google.auth
from pypdf import PdfReader

class DrivePDFReader:
    def __init__(self):
        """
        Inicializa el cliente de lectura de Google Drive.
        Usa las Application Default Credentials (ADC).
        """
        try:
            # Autenticación automática con ADC
            self.credentials, self.project = google.auth.default(
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
            self.service = build('drive', 'v3', credentials=self.credentials)
            print("✅ Conectado a Google Drive API.")
        except Exception as e:
            print(f"❌ Error al autenticar Google Drive: {e}")
            self.service = None

    def get_context_from_drive_folder(self, folder_id: str) -> str:
        """
        Busca archivos PDF en la carpeta dada, los descarga en memoria,
        extrae su texto y devuelve el contenido consolidado.
        """
        import re
        
        # Extraer ID si el usuario pegó la URL completa
        match = re.search(r'folders/([a-zA-Z0-9_-]+)', folder_id)
        if match:
            folder_id = match.group(1)
        elif "id=" in folder_id:
            match = re.search(r'id=([a-zA-Z0-9_-]+)', folder_id)
            if match:
                folder_id = match.group(1)

        if not self.service:
            print("⚠️ Cliente de Google Drive no inicializado.")
            return ""

        context_parts = []
        try:
            print(f"DEBUG: Buscando archivos PDF en la carpeta con ID '{folder_id}'...")
            # Filtrar por mimetype PDF y padre igual a la carpeta
            query = f"'{folder_id}' in parents and mimeType='application/pdf' and trashed=false"
            results = self.service.files().list(
                q=query, spaces='drive', fields='nextPageToken, files(id, name)'
            ).execute()
            items = results.get('files', [])

            if not items:
                print(f"⚠️ No se encontraron archivos PDF en la carpeta '{folder_id}'.")
                return ""

            print(f"✅ Se encontraron {len(items)} archivo(s) PDF.")

            for index, item in enumerate(items):
                file_id = item['id']
                file_name = item['name']
                print(f"📥 [{index+1}/{len(items)}] Descargando y procesando: {file_name}...")

                # Descargar en memoria
                request = self.service.files().get_media(fileId=file_id)
                fh = io.BytesIO()
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while done is False:
                    status, done = downloader.next_chunk()
                
                # Extraer texto del PDF en memoria
                fh.seek(0)
                try:
                    pdf = PdfReader(fh)
                    text = ""
                    for page_num in range(len(pdf.pages)):
                        page = pdf.pages[page_num]
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                            
                    if text.strip():
                        context_parts.append(f"--- INICIO DOCUMENTO: {file_name} ---\n{text.strip()}\n--- FIN DOCUMENTO: {file_name} ---")
                        print(f"✅ Texto extraído de {file_name} exitosamente.")
                    else:
                        print(f"⚠️ El archivo {file_name} está vacío o no contiene texto extraíble.")
                except Exception as pdf_err:
                    print(f"❌ Error al leer o extraer texto del PDF {file_name}: {pdf_err}")
                finally:
                    fh.close()

        except Exception as e:
            print(f"❌ Error al recuperar archivos de Google Drive: {e}")
            return ""

        final_context = "\n\n".join(context_parts)
        return final_context
