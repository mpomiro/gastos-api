
from fastapi import FastAPI, Request
import openai
import os
import requests

app = FastAPI()

# Reemplazar con tu propia clave de OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

@app.post("/whatsapp-webhook")
async def whatsapp_webhook(request: Request):
    data = await request.form()
    mensaje = data.get("Body", "")
    numero = data.get("From", "")

    if not mensaje:
        return {"status": "error", "detail": "Mensaje vacío"}

    prompt = f"""Tu función es clasificar y estructurar mensajes financieros personales. A partir del siguiente mensaje, devolveme un JSON con los siguientes campos:
- tipo: uno de ["gasto", "ingreso", "saldo", "tenencia"]
- data: un objeto con los datos que correspondan al tipo (por ejemplo, descripcion, monto, cuenta, etc.)
Ejemplo: 
Input: "Gasté 20000 en el super con la Visa"
Output: {{ "tipo": "gasto", "data": {{ "descripcion": "super", "monto": 20000 }} }}
Mensaje: "{mensaje}"
"""

    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Sos un analista financiero que estructura datos en JSON."},
            {"role": "user", "content": prompt}
        ]
    )

    contenido = completion.choices[0].message["content"]

    try:
        estructura = eval(contenido)
    except:
        return {"status": "error", "detail": "No se pudo interpretar el JSON generado"}

    tipo = estructura.get("tipo")
    datos = estructura.get("data")

    endpoint_map = {
        "gasto": "registro-gasto",
        "ingreso": "registro-ingreso",
        "saldo": "actualizar-saldo",
        "tenencia": "actualizar-tenencia"
    }

    if tipo not in endpoint_map:
        return {"status": "error", "detail": f"Tipo no reconocido: {tipo}"}

    api_url = f"https://gastos-api-xhwa.onrender.com/{endpoint_map[tipo]}"
    response = requests.post(api_url, json=datos)

    return {
        "status": "ok",
        "mensaje": mensaje,
        "gpt_entendio": estructura,
        "respuesta_api": response.json()
    }
