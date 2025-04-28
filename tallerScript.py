import traceback
from pyzbar import pyzbar
import paho.mqtt.client as mqtt
import cv2
import yagmail
import numpy as np
import os
from barcode import get
from barcode.writer import ImageWriter
from io import BytesIO

# %%
# Información imagen
class InfoImg:
    def __init__(self, tipo, datos, imagen=None):
        self.tipo = tipo
        self.datos = datos
        self.imagen = imagen

# %%
def decode(image):
    # Decodes all barcodes from an image
    decoded_objects = pyzbar.decode(image)

    if not decoded_objects:
        print("No barcodes detected.")
        return None  # Retorna None si no hay códigos de barras

    # Procesar solo el primer código de barras detectado
    obj = decoded_objects[0]
    print("Detected barcode:", obj)
    
    # Decodificar el tipo y los datos
    tipo = obj.type
    datos = obj.data.decode("utf-8")  # Decodificar los datos a texto
    print("Type:", tipo)
    print("Data:", datos)
    print()

    # Retornar una instancia de InfoImg con la imagen original
    return InfoImg(tipo, datos, image)

def draw_barcode(decoded, image):
    image = cv2.rectangle(image, (decoded.rect.left, decoded.rect.top),
                          (decoded.rect.left + decoded.rect.width, decoded.rect.top + decoded.rect.height),
                          color=(0, 255, 0),
                          thickness=5)
    return image

def generate_barcode_image(payload):
    """Generate EAN-13 barcode image using python-barcode, without temporary files"""
    if ImageWriter is None:
        raise RuntimeError("Instala Pillow: pip install Pillow")
    
    # Ajustar el payload a 12 dígitos (el checksum se añadirá automáticamente)
    if len(payload) == 13:
        payload = payload[:12]
    elif len(payload) != 12:
        payload = payload.zfill(12)[:12]
    
    # Crear el código de barras en memoria
    ean = get('ean13', payload, writer=ImageWriter())
    virtual_file = BytesIO()
    ean.write(virtual_file)  # Escribir en el buffer
    virtual_file.seek(0)  # Rebobinar el buffer
    
    # Convertir BytesIO a imagen OpenCV
    file_bytes = np.asarray(bytearray(virtual_file.read()), dtype=np.uint8)
    barcode_image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    
    return barcode_image


def publicador(infoImg, numeroGrupo):
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)  # Usar API V2
    client.connect("test.mosquitto.org", 1883, 60)

    # Caso 1: Grupo inicial (3)
    if str(infoImg.datos)[0] == str(numeroGrupo):
        siguiente_grupo = str(infoImg.datos)[1]  # Obtener el siguiente dígito (1)
        nuevo_dato = int(infoImg.datos) + 10  # 312546789760 → 312546789770
        client.publish(f"PATRONES2025/all", "Del grupo 3 al grupo "+ siguiente_grupo)
        client.publish(f"PATRONES2025/G{siguiente_grupo}", nuevo_dato)
        print(f"Enviando {nuevo_dato} al grupo {siguiente_grupo}")
        client.disconnect()

    else:
        # Caso 2: Grupo intermedio (1)
        def on_message(client, userdata, message):
            print(f"Mensaje recibido: {message.payload.decode()}")
            nuevo_dato = int(message.payload.decode()) + 10
            datos_str = str(infoImg.datos)

            if str(numeroGrupo) not in datos_str:
                print("Grupo no está en los datos")
                client.disconnect()
                return

            index_actual = datos_str.index(str(numeroGrupo))

            # Caso 3: En caso de recibir el mensaje para G1, envía el correo con un nuevo código de barras
            if index_actual == 4:
                send_email(str(nuevo_dato))
                client.publish(f"PATRONES2025/all", f"Enviado al correo")
                client.disconnect()
                return

            siguiente_grupo = datos_str[index_actual + 1]
            client.publish(f"PATRONES2025/G{siguiente_grupo}", nuevo_dato)
            print(f"Publicado a G{siguiente_grupo}: {nuevo_dato}")
            client.disconnect()

        client.on_message = on_message
        client.subscribe(f"PATRONES2025/G{numeroGrupo}")
        print(f"Escuchando en PATRONES2025/G{numeroGrupo}...")
        client.loop_forever()


def send_email(payload):
    try:
        if not (len(payload)) in (12, 13) and payload.isdigit():
            raise ValueError("El código debe contener 12 o 13 dígitos numéricos.")

        barcode_image = generate_barcode_image(payload)
        
        if barcode_image is None:
            raise ValueError("La imagen del código de barras no se generó correctamente.")
        
        filename = "barcode_imagen.png"
        cv2.imwrite(filename, barcode_image)

        user = "sierraincollege@gmail.com"
        # Pasa la contraseña como segundo parámetro posicional
        gmail = yagmail.SMTP(user, "bsok bfqe atlu omjy")

        # Aquí le decimos:
        # to: destinatario
        # subject: asunto
        # contents: cuerpo de texto (puede ser cadena o lista)
        # attachments: ruta o lista de rutas a adjuntar
        gmail.send(
            to="simondiaz@javeriana.edu.co",
            subject="Código Taller G1",
            contents="Adjunto te envío el nuevo código de barras.",
            attachments=filename
        )
        print("Correo enviado.")
    
    except Exception as e:
        traceback.print_exc()                # <-- muestra el error completo
        print(f"Error al enviar correo: {e}")

# %%
if __name__ == "__main__":
    from glob import glob

    numeroGrupo = int(input("Ingrese el numero de grupo: "))
    barcodes = glob("Caso3.png")

    for barcode_file in barcodes:
        # Cargar la imagen con OpenCV
        img = cv2.imread(barcode_file)

        # Decodificar el primer código de barras detectado
        decoded_info = decode(img)

        if decoded_info is not None:
            print(f"Tipo: {decoded_info.tipo}, Datos: {decoded_info.datos}")
            try:
                datos = int(decoded_info.datos)  # Convertir los datos a un número entero si es posible
                publicador(decoded_info, numeroGrupo)
            except ValueError:
                print("No contiene datos, terminado programa")
        else:
            print("No se detectaron códigos de barras.")