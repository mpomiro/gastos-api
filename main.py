
from fastapi import FastAPI, Request
from pydantic import BaseModel
from datetime import datetime
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
    # Fecha actual si no viene
    fecha = gasto.fecha if gasto.fecha else datetime.today().strftime('%d/%m/%Y')
    descripcion = gasto.descripcion
    monto = gasto.monto

    # Clasificación automática
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

    # Autenticación Google Sheets
    credentials_json = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)

    # Abrir hoja
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1pmChlg5qv3TWx2yN8M_KONPCK2M4kybOamKsv6RWYzs/edit")
    worksheet = sheet.worksheet("Movimientos")

    fila = [fecha, descripcion, categoria, str(monto)]
    worksheet.append_row(fila)

    return {"status": "ok", "data": fila}
