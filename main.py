from fastapi import FastAPI, Request
from datetime import datetime
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clasificación automática por palabras clave
categorias = {
    'comida': 'Comida diaria',
    'vianda': 'Comida diaria',
    'almuerzo': 'Comida diaria',
    'asado': 'Comida con los pibes',
    'restaurante': 'Comida con los pibes',
    'super': 'Supermercado',
    'supermercado': 'Supermercado',
    'fútbol': 'Fútbol',
    'cancha': 'Fútbol',
    'fiesta': 'Fiesta / Salidas',
    'previa': 'Fiesta / Salidas',
    'birra': 'Fútbol'
}

@app.post("/registro-gasto")
async def registrar_gasto(request: Request):
    body = await request.json()
    descripcion = body.get("descripcion")
    monto = body.get("monto")
    fecha_raw = body.get("fecha")  # Puede ser None

    if not descripcion or not monto:
        return {"error": "Faltan datos requeridos: descripción o monto."}

    # Si no se proporciona fecha, usar fecha actual
    if fecha_raw:
        try:
            fecha = datetime.strptime(fecha_raw, "%d/%m/%Y")
        except ValueError:
            return {"error": "Formato de fecha inválido. Usá DD/MM/YYYY."}
    else:
        fecha = datetime.today()

    # Categoría automática
    categoria = "Otros"
    for palabra, cat in categorias.items():
        if palabra in descripcion.lower():
            categoria = cat
            break

    # Conexión a Google Sheets
    credentials_json = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)

    # Abrir hoja
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1pmChlg5qv3TWx2yN8M_KONPCK2M4kybOamKsv6RWYzs/edit")
    worksheet = sheet.worksheet("Movimientos")

    # Registrar
    fila = [fecha.strftime("%d/%m/%Y"), descripcion, categoria, float(monto)]
    worksheet.append_row(fila, value_input_option="USER_ENTERED")

    return {
        "status": "ok",
        "data": fila
    }
