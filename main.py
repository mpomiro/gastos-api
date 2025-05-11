
from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, date
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import re
import os
import json

app = FastAPI()

class Gasto(BaseModel):
    descripcion: str
    monto: float
    fecha: str = None  # opcional

@app.post("/registro-gasto")
def registrar_gasto(gasto: Gasto):
    # Usar fecha actual si no se proporciona
    if gasto.fecha:
        try:
            fecha = datetime.strptime(gasto.fecha, "%d/%m/%Y").date()
        except ValueError:
            fecha = date.today()
    else:
        fecha = date.today()

    descripcion = gasto.descripcion
    monto = gasto.monto

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

    categoria = "Otros"
    for palabra, cat in categorias.items():
        if palabra in descripcion.lower():
            categoria = cat
            break

    # Conexión con Google Sheets
    credentials_json = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)

    # Abrir la hoja
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1pmChlg5qv3TWx2yN8M_KONPCK2M4kybOamKsv6RWYzs/edit")
    worksheet = sheet.worksheet("Movimientos")

    # Registrar la fila
    fila = [fecha, descripcion, categoria, float(monto)]
    worksheet.append_row(fila, value_input_option="USER_ENTERED")

    return {"status": "ok", "data": fila}
