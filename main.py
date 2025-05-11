from fastapi import FastAPI
from pydantic import BaseModel
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import json
from datetime import datetime

app = FastAPI()

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

class Gasto(BaseModel):
    fecha: str
    descripcion: str
    monto: float

@app.post("/registro-gasto")
async def registrar_gasto(gasto: Gasto):
    descripcion = gasto.descripcion
    monto = gasto.monto

    try:
        fecha = datetime.strptime(gasto.fecha, "%d/%m/%Y")
    except:
        fecha = datetime.today()

    categoria = 'Otra'
    for palabra, cat in categorias.items():
        if palabra in descripcion.lower():
            categoria = cat
            break

    credentials_json = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1pmChlg5qv3TWx2yN8M_KONPCK2M4kybOamKsv6RWYzs/edit")
    worksheet = sheet.worksheet("Movimientos")

    fila = [fecha.strftime("%d/%m/%Y"), descripcion, categoria, float(monto)]
    worksheet.append_row(fila, value_input_option="USER_ENTERED")

    return {
        "status": "ok",
        "data": fila
    }
