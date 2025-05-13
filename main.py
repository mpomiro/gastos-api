from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import os
import gspread
import requests
import openai
from oauth2client.service_account import ServiceAccountCredentials

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

# Conexión con Google Sheets
def conectar_hoja(nombre_hoja):
    credentials_json = json.loads(os.environ['GOOGLE_SHEETS_CREDENTIALS'])
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_json, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1_WxcW9ByLABZsppABJb9mD7711KOSbbm6YHGP-fx-aA/edit")
    return sheet.worksheet(nombre_hoja)

@app.post("/registro-gasto")
async def registrar_gasto(request: Request):
    body = await request.json()
    descripcion = body.get("descripcion")
    monto = body.get("monto")
    fecha_raw = body.get("fecha")

    if not descripcion or not monto:
        return {"error": "Faltan datos requeridos: descripción o monto."}

    if fecha_raw:
        try:
            fecha = datetime.strptime(fecha_raw, "%d/%m/%Y")
        except ValueError:
            return {"error": "Formato de fecha inválido. Usá DD/MM/YYYY."}
    else:
        fecha = datetime.today()

    categoria = "Otros"
    for palabra, cat in categorias.items():
        if palabra in descripcion.lower():
            categoria = cat
            break

    worksheet = conectar_hoja("Movimientos")
    fila = [fecha.strftime("%d/%m/%Y"), descripcion, categoria, float(monto)]
    worksheet.append_row(fila, value_input_option="USER_ENTERED")

    return {"status": "ok", "data": fila}

class Ingreso(BaseModel):
    descripcion: str
    monto: float
    fuente: str
    cuenta: str
    fecha: str = None

@app.post("/registro-ingreso")
def registrar_ingreso(ingreso: Ingreso):
    fecha = ingreso.fecha or datetime.today().strftime('%d/%m/%Y')
    fila = [fecha, ingreso.descripcion, ingreso.monto, ingreso.fuente, ingreso.cuenta]
    hoja = conectar_hoja("Ingresos")
    hoja.append_row(fila, value_input_option="USER_ENTERED")
    return {"status": "ok", "data": fila}

class Saldo(BaseModel):
    cuenta: str
    saldo: float
    tipo: str
    moneda: str
    fecha: str = None

@app.post("/actualizar-saldo")
def actualizar_saldo(saldo: Saldo):
    fecha = saldo.fecha or datetime.today().strftime('%d/%m/%Y')
    fila = [saldo.cuenta, saldo.saldo, saldo.tipo, saldo.moneda, fecha]
    hoja = conectar_hoja("Saldos")
    cuentas = hoja.col_values(1)

    try:
        idx = cuentas.index(saldo.cuenta) + 1
        hoja.update(f'A{idx}:E{idx}', [fila])
        return {"status": "actualizado", "data": fila}
    except ValueError:
        hoja.append_row(fila, value_input_option="USER_ENTERED")
        return {"status": "agregado", "data": fila}

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    try:
        data = await request.form()
        mensaje = data.get("Body")
        numero = data.get("From")

        print("📩 Mensaje recibido desde WhatsApp:", mensaje)
        print("📱 Número:", numero)

        if not mensaje:
            return Response(content="<Response><Message>No se recibió ningún mensaje.</Message></Response>", media_type="application/xml")

    openai.api_key = os.environ["OPENAI_API_KEY"]

    prompt = f"""
    Clasificá el siguiente mensaje como gasto, ingreso, saldo o tenencia. Devolveme un JSON como este:
    {{
      "tipo": "gasto",
      "data": {{
        "descripcion": "...",
        "monto": ...
      }}
    }}
    Mensaje: "{mensaje}"
    """

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Sos un asistente financiero que transforma texto en JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    contenido = completion.choices[0].message["content"]

    try:
        estructura = eval(contenido)
    except:
        return Response(content="<Response><Message>No entendí el mensaje.</Message></Response>", media_type="application/xml")

    tipo = estructura.get("tipo")
    datos = estructura.get("data")

    endpoint_map = {
        "gasto": "registro-gasto",
        "ingreso": "registro-ingreso",
        "saldo": "actualizar-saldo",
        "tenencia": "actualizar-tenencia"
    }

    if tipo not in endpoint_map:
        return Response(content=f"<Response><Message>Tipo no reconocido: {tipo}</Message></Response>", media_type="application/xml")

    api_url = f"https://gastos-api-xhwa.onrender.com/{endpoint_map[tipo]}"
    response = requests.post(api_url, json=datos)

    return Response(
        content=f"<Response><Message>{tipo.title()} registrado correctamente.</Message></Response>",
        media_type="application/xml"
    )

 except Exception as e:
        print("❌ Error en webhook:", str(e))
        return Response(content=f"<Response><Message>Error interno: {str(e)}</Message></Response>", media_type="application/xml")
