import random
import barcode
from barcode.writer import ImageWriter

# Establecer los primeros 5 dígitos de 1 a 5, pero comenzando con 1
first_digits = '34251'

# Los siguientes 7 dígitos se generan aleatoriamente
remaining_digits = ''.join(str(random.randint(0, 9)) for _ in range(7))

# El número completo EAN-13
ean_base = first_digits + remaining_digits

# Crear código EAN-13 (el paquete calcula automáticamente el dígito de control)
ean = barcode.get('ean13', ean_base, writer=ImageWriter())

# Guardar el EAN-13 en un archivo
filename = 'ean13_code'
full_path = ean.save(filename)

# Mostrar el código base y la ubicación del archivo
print('Código base:', ean_base)
print('Guardado en:', full_path)
