# SecureEntry – Sistema Inteligente de Control de Aforo

Sistema inteligente de control de aforo en tiempo real usando visión por computadora, YOLOv8 y comunicación serial con ESP8266.

---

# Autores

- Neider Cuesta
- Arianna Mora

---

# Descripción

# Descripción

SecureEntry es un sistema inteligente de control de aforo que utiliza visión por computadora e inteligencia artificial para detectar y contar personas en tiempo real mediante una cámara.

El sistema fue desarrollado en Python utilizando YOLOv8 y OpenCV para la detección de personas.

La arquitectura del proyecto funciona de la siguiente manera:

1. Python realiza la detección y conteo de personas.
2. Python envía datos mediante comunicación serial al Arduino.
3. Arduino procesa la información recibida.
4. Arduino envía señales al ESP32.
5. El ESP32 activa los actuadores correspondientes:
   - LEDs
   - Servo motor
   - Buzzer

dependiendo del estado del aforo.

---

# Tecnologías utilizadas

- Python
- OpenCV
- YOLOv8
- Tkinter
- Pillow
- PySerial
- Arduino
- ESP32

---

# Estructura del proyecto

SecureEntry-Control-Aforo-IA/
│
├── ProyectoV3.py
├── README.md
├── requirements.txt
├── .gitignore
├── MobileNetSSD_deploy.prototxt
│
└── assets/
```

---

# Instalación

## 1. Clonar repositorio

```bash
git clone https://github.com/TU-USUARIO/SecureEntry-Control-Aforo-IA.git
```

---

## 2. Entrar a la carpeta

```bash
cd SecureEntry-Control-Aforo-IA
```

---

## 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

---

# Dependencias

```txt
opencv-python
pillow
ultralytics
pyserial
numpy
```

---

# Descargar modelos

Por temas de peso, los modelos NO están incluidos en el repositorio.

Descargar:

- yolov8n.pt
- MobileNetSSD_deploy.caffemodel

y colocarlos en la raíz del proyecto.

---

# Ejecución

```bash
python ProyectoV3.py
```

---

# Funcionalidades

- Detección de personas en tiempo real
- Conteo automático
- Control de aforo
- Estados dinámicos:
  - Disponible
  - Casi lleno
  - Lleno
  - Excedido
- Interfaz gráfica moderna
- Comunicación serial con ESP8266
- Visualización de cámara en vivo

---

# Funcionamiento

1. El usuario establece el límite máximo.
2. El sistema activa la cámara.
3. YOLOv8 detecta personas.
4. Se calcula el porcentaje de ocupación.
5. El sistema activa alertas según el aforo.

---

# Estado del sistema

| Estado | Descripción |
|---|---|
| Disponible | Aforo dentro del límite |
| Casi lleno | Cerca del límite |
| Lleno | Capacidad alcanzada |
| Excedido | Capacidad superada |

---

# Proyecto académico

Proyecto desarrollado con fines educativos y académicos.