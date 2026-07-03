# Authenticated child photo upload MVP

## Feature-Name

Authenticated child photo upload MVP.

## Ziel

- Admins koennen Fotos fuer jedes Kind hochladen und ansehen.
- Eltern koennen Fotos nur fuer ihr eigenes Kind hochladen und ansehen.
- Speicherung erfolgt im bestehenden Drive-Ordner des Kindes ueber `child["folder_id"]`.

## Nicht-Ziele

- Keine oeffentlichen Google-Drive-Links.
- Keine neuen Drive-Permissions pro Foto.
- Kein neuer OAuth-Flow.
- Keine Gesichtserkennung.
- Kein automatisches Tagging fremder Kinder.
- Keine Aenderung am Stammdaten-Schema ausser Nutzung bestehender Felder.

## Security/Privacy

- Keine Secrets im Repo.
- Keine Klartext-E-Mail im Dateinamen.
- Keine PII in Logs.
- Service Account bleibt ueber bestehende Secrets konfiguriert.

## Erlaubte Uploads

- `image/jpeg`
- `image/png`
- `image/webp`
- Maximal 15 MB pro Datei.

## Akzeptanzkriterien

- Admin sieht neues Menue "Fotos & Medien / Photos & media".
- Parent sieht neues Menue "Fotos & Medien / Photos & media".
- Parent kann kein anderes Kind auswaehlen.
- Upload nutzt DriveAgent.
- Galerie nutzt `DriveAgent.list_files` und `DriveAgent.download_file`.
- `python -m compileall app.py services/photo_share_service.py ui/photos.py` laeuft fehlerfrei.
- `python -m streamlit run app.py` startet.
