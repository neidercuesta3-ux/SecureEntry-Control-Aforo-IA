import cv2
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
from ultralytics import YOLO
import serial
import time

# CARGAR MODELO YOLO

model = YOLO("yolov8n.pt")

# CONFIGURACIÓN SERIAL

try:
    arduino = serial.Serial('COM5', 115200, timeout=1)
    print("ESP8266 conectado")
except:
    arduino = None
    print("ESP8266 no conectado")

# COLORES

BG_DARK      = "#111827"
BG_CARD      = "#1f2937"
BG_CARD2     = "#273549"
ACCENT_BLUE  = "#2563eb"
ACCENT_GREEN = "#16a34a"
ACCENT_RED   = "#b91c1c"
ACCENT_AMBER = "#ca8a04"
TEXT_PRIMARY = "#e5e7eb"
TEXT_MUTED   = "#9ca3af"
BORDER_COLOR = "#374151"


# VARIABLES GLOBALES

max_personas_val = 0
cap           = None
running       = False
ultimo_envio  = 0
total_actual  = 0

# APAGADO DE COMPONENTES

def apagar_actuadores():
    """Envía un estado especial al Arduino para apagar LEDs, Servo y Buzzer."""
    global arduino
    if arduino:
        try:
            arduino.write(f"c,0\n".encode())
            time.sleep(0.1)
        except:
            pass

# DETECCIÓN + TRACKING

def detectar_personas(frame):
    global max_personas_val, ultimo_envio, total_actual

    resultados = model.track(frame, persist=True, verbose=False)
    ids_activos = set()

    for r in resultados:
        boxes = r.boxes
        if boxes.id is not None:
            for box, track_id in zip(boxes, boxes.id):
                clase = int(box.cls[0])
                if clase == 0:
                    track_id = int(track_id)
                    ids_activos.add(track_id)
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    color = (
                        (track_id * 50) % 255,
                        (track_id * 80) % 255,
                        (track_id * 110) % 255,
                    )
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    cv2.putText(
                        frame, f"ID: {track_id}",
                        (x1 + 4, y1 - 8),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2,
                    )

    total_actual = len(ids_activos)

    estado = "a" if total_actual > max_personas_val else "b"
    tiempo_actual = time.time()
    if tiempo_actual - ultimo_envio > 1:
        if arduino:
            try:
                arduino.write(f"{estado},{total_actual}\n".encode())
                ultimo_envio = tiempo_actual
            except:
                pass

    return frame

# ESTADO DE AFORO

def calcular_estado(personas, maximo):
    if maximo == 0:
        pct = 0
    else:
        pct = (personas / maximo) * 100

    if pct <= 74:
        return "DISPONIBLE", ACCENT_GREEN, "El aforo está dentro del límite permitido.", pct
    elif pct <= 99:
        return "CASI LLENO", ACCENT_AMBER, "El aforo está próximo al límite.", pct
    elif pct == 100:
        return "LLENO", ACCENT_RED, "Se ha alcanzado el límite de aforo.", pct
    else:
        return "EXCEDIDO", "#ff0000", "¡Se ha superado el límite de aforo!", pct


def draw_gauge(canvas, cx, cy, r, pct, color):
    canvas.delete("gauge")
    canvas.create_arc(
        cx - r, cy - r, cx + r, cy + r,
        start=0, extent=359.9,
        outline=BORDER_COLOR, width=8, style="arc", tags="gauge"
    )

    if pct > 100:
        canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-359.9,
            outline="#ff0000", width=8, style="arc", tags="gauge"
        )
        canvas.create_text(cx, cy - 10, text="⚠",
                           font=("Helvetica", 22, "bold"),
                           fill="#ff0000", tags="gauge")
        canvas.create_text(cx, cy + 14, text="EXCEDIDO",
                           font=("Helvetica", 9, "bold"),
                           fill="#ff0000", tags="gauge")
    else:
        extent = (pct / 100) * 359.9
        canvas.create_arc(
            cx - r, cy - r, cx + r, cy + r,
            start=90, extent=-extent,
            outline=color, width=8, style="arc", tags="gauge"
        )
        pct_text = f"{int(pct)}%"
        canvas.create_text(cx, cy - 8, text=pct_text,
                           font=("Helvetica", 20, "bold"),
                           fill=TEXT_PRIMARY, tags="gauge")
        canvas.create_text(cx, cy + 14, text="de capacidad",
                           font=("Helvetica", 9),
                           fill=TEXT_MUTED, tags="gauge")

# ACTUALIZAR PANEL DERECHO

def actualizar_panel():
    global total_actual, max_personas_val

    # Si el sistema no está corriendo, mostrar estado inactivo y resetear todo a cero
    if not running:
        lbl_personas_count.config(text="0")
        draw_gauge(gauge_canvas, 60, 60, 50, 0, ACCENT_BLUE)
        lbl_estado_badge.config(text="● INACTIVO", fg=TEXT_MUTED, bg=BG_CARD2)
        lbl_estado_desc.config(text="El sistema está detenido.")
        lbl_max_display.config(text="—")
        return

    estado_txt, color, desc, pct = calcular_estado(total_actual, max_personas_val)

    lbl_personas_count.config(text=str(total_actual))
    draw_gauge(gauge_canvas, 60, 60, 50, pct, color)
    lbl_estado_badge.config(text=f"● {estado_txt}", fg=color, bg=BG_CARD2)
    lbl_estado_desc.config(text=desc)
    lbl_max_display.config(text=str(max_personas_val))

# LOOP CÁMARA

def update_frame():
    global cap, running

    if running:
        ret, frame = cap.read()
        if ret:
            frame = detectar_personas(frame)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            img = img.resize((860, 480), Image.LANCZOS)
            imgtk = ImageTk.PhotoImage(image=img)
            video_label.imgtk = imgtk
            video_label.configure(image=imgtk)
            actualizar_panel()

        video_label.after(10, update_frame)

# GUARDAR CAMBIOS / INICIAR

def guardar_cambios():
    global cap, running, max_personas_val

    if running:
        messagebox.showwarning(
            "Sistema activo",
            "Primero debes detener el sistema para intentar modificar el número de personas permitidos.",
        )
        return

    try:
        val_str = spinbox_var.get().strip()

        if val_str == "" or int(val_str) == 0:
            messagebox.showerror("Error", "La capacidad máxima debe ser un número mayor a cero (mínimo 1).")
            return

        nuevo_max = int(val_str)
        if nuevo_max < 1:
            raise ValueError

    except ValueError:
        messagebox.showerror("Error", "Ingrese un número válido mayor a cero.")
        return

    max_personas_val = nuevo_max
    lbl_max_display.config(text=str(max_personas_val))

    # Abrir cámara
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        messagebox.showerror("Error", "No se pudo abrir la cámara.")
        return

    running = True
    lbl_sistema_estado.config(text="● ACTIVO", fg=ACCENT_GREEN)
    lbl_sistema_desc.config(text="El sistema está contando personas.")
    lbl_header_estado.config(text="● Sistema activo", fg=ACCENT_GREEN)
    btn_detener.config(state="normal")
    btn_guardar.config(text="  Iniciado ✓")
    lbl_vivo.config(text="● EN VIVO", fg=ACCENT_GREEN)
    lbl_cam_title.config(text="CÁMARA ACTIVA")

    entry_personas.config(state="readonly")
    lbl_cam_placeholder.place_forget()

    update_frame()

# DETENER SISTEMA

def detener_sistema():
    global cap, running, total_actual  # ← se agrega total_actual

    running = False
    if cap:
        cap.release()
        cap = None

    # APAGAR HARDWARE AL DETENER
    apagar_actuadores()

    # Resetear contadores a cero y actualizar panel
    total_actual = 0
    actualizar_panel()

    video_label.configure(image="")
    video_label.imgtk = None

    lbl_sistema_estado.config(text="● INACTIVO", fg=TEXT_MUTED)
    lbl_sistema_desc.config(text="El sistema está detenido.")
    lbl_header_estado.config(text="● Sistema detenido", fg=TEXT_MUTED)
    btn_guardar.config(text="  Iniciar sistema")
    lbl_vivo.config(text="", fg=BG_CARD)
    lbl_cam_title.config(text="CÁMARA INACTIVA")
    lbl_cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")

    entry_personas.config(state="normal")


# VALIDACIÓN TECLADO

def solo_numeros(char):
    if char == "":
        return True
    if char.isdigit():
        if char.startswith("0"):
            return False
        return True
    return False


# VENTANA PRINCIPAL

root = tk.Tk()
root.title("SecureEntry – Sistema de Control de Aforo")
root.configure(bg=BG_DARK)
root.resizable(False, False)

valida_digitos = root.register(solo_numeros)
spinbox_var = tk.StringVar(value="")

# HEADER

header = tk.Frame(root, bg=BG_CARD, height=64)
header.pack(fill="x")
header.pack_propagate(False)

frm_logo = tk.Frame(header, bg=BG_CARD)
frm_logo.pack(side="left", padx=20, pady=10)

logo_icon = tk.Label(frm_logo, text="👥", font=("Helvetica", 22), bg=BG_CARD, fg=ACCENT_BLUE)
logo_icon.pack(side="left")

frm_titles = tk.Frame(frm_logo, bg=BG_CARD)
frm_titles.pack(side="left", padx=8)
tk.Label(frm_titles, text="SecureEntry", font=("Helvetica", 14, "bold"),
         bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w")
tk.Label(frm_titles, text="Sistema de Control de Aforo", font=("Helvetica", 9),
         bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

frm_header_right = tk.Frame(header, bg=BG_CARD)
frm_header_right.pack(side="right", padx=20)

lbl_header_estado = tk.Label(frm_header_right, text="● Sistema detenido",
                              font=("Helvetica", 10), bg=BG_CARD, fg=TEXT_MUTED)
lbl_header_estado.pack(side="left", padx=(0, 16))

btn_detener = tk.Button(
    frm_header_right, text="⏹  Detener sistema",
    font=("Helvetica", 10, "bold"),
    bg=BG_DARK, fg=ACCENT_RED,
    activebackground="#1f1f1f", activeforeground=ACCENT_RED,
    relief="flat", bd=0, padx=14, pady=6,
    highlightthickness=1, highlightbackground=ACCENT_RED,
    cursor="hand2", command=detener_sistema, state="disabled"
)
btn_detener.pack(side="left")

tk.Frame(root, bg=BORDER_COLOR, height=1).pack(fill="x")

# CUERPO PRINCIPAL

body = tk.Frame(root, bg=BG_DARK)
body.pack(fill="both", expand=True, padx=16, pady=12)

# Cámara

col_left = tk.Frame(body, bg=BG_DARK)
col_left.pack(side="left", fill="both", expand=True)

cam_card = tk.Frame(col_left, bg=BG_CARD, bd=0, highlightthickness=1,
                    highlightbackground=BORDER_COLOR)
cam_card.pack(fill="both", expand=True, pady=(0, 8))

cam_header = tk.Frame(cam_card, bg=BG_CARD)
cam_header.pack(fill="x", padx=14, pady=10)

tk.Label(cam_header, text="", font=("Helvetica", 13), bg=BG_CARD, fg=ACCENT_BLUE).pack(side="left")
lbl_cam_title = tk.Label(cam_header, text="CÁMARA INACTIVA",
                          font=("Helvetica", 11, "bold"), bg=BG_CARD, fg=TEXT_PRIMARY)
lbl_cam_title.pack(side="left", padx=8)

lbl_vivo = tk.Label(cam_header, text="", font=("Helvetica", 9, "bold"),
                    bg=BG_CARD, fg=BG_CARD, padx=8, pady=3)
lbl_vivo.pack(side="right")

cam_container = tk.Frame(cam_card, bg="#000000", width=860, height=480)
cam_container.pack(padx=12, pady=(0, 12))
cam_container.pack_propagate(False)

video_label = tk.Label(cam_container, bg="#000000")
video_label.place(relwidth=1, relheight=1)

lbl_cam_placeholder = tk.Label(
    cam_container,
    text="\n\nCámara inactiva\nInicia el sistema para comenzar",
    font=("Helvetica", 13), bg="#000000", fg=TEXT_MUTED, justify="center"
)
lbl_cam_placeholder.place(relx=0.5, rely=0.5, anchor="center")

# COLUMNA DERECHA

col_right = tk.Frame(body, bg=BG_DARK, width=270)
col_right.pack(side="right", fill="y", padx=(12, 0))
col_right.pack_propagate(False)

estado_card = tk.Frame(col_right, bg=BG_CARD, bd=0, highlightthickness=1,
                        highlightbackground=BORDER_COLOR)
estado_card.pack(fill="x", pady=(0, 8))

tk.Label(estado_card, text="ESTADO ACTUAL", font=("Helvetica", 10, "bold"),
         bg=BG_CARD, fg=TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(12, 8))

tk.Frame(estado_card, bg=BORDER_COLOR, height=1).pack(fill="x", padx=14)

frm_metrics = tk.Frame(estado_card, bg=BG_CARD)
frm_metrics.pack(fill="x", padx=14, pady=12)

frm_pcount = tk.Frame(frm_metrics, bg=BG_CARD)
frm_pcount.pack(side="left")
tk.Label(frm_pcount, text="", font=("Helvetica", 22), bg=BG_CARD, fg=ACCENT_BLUE).pack()
lbl_personas_count = tk.Label(frm_pcount, text="0",
                               font=("Helvetica", 36, "bold"), bg=BG_CARD, fg=TEXT_PRIMARY)
lbl_personas_count.pack()
tk.Label(frm_pcount, text="personas\nactuales", font=("Helvetica", 9),
         bg=BG_CARD, fg=TEXT_MUTED, justify="center").pack()

gauge_canvas = tk.Canvas(frm_metrics, width=120, height=120, bg=BG_CARD,
                          highlightthickness=0)
gauge_canvas.pack(side="right")
draw_gauge(gauge_canvas, 60, 60, 50, 0, ACCENT_BLUE)

frm_badge = tk.Frame(estado_card, bg=BG_CARD2, pady=10)
frm_badge.pack(fill="x", padx=14, pady=(0, 6))

lbl_estado_badge = tk.Label(frm_badge, text="● INACTIVO",
                             font=("Helvetica", 13, "bold"),
                             bg=BG_CARD2, fg=TEXT_MUTED)
lbl_estado_badge.pack()
lbl_estado_desc = tk.Label(frm_badge, text="El sistema está detenido.",
                            font=("Helvetica", 9), bg=BG_CARD2, fg=TEXT_MUTED,
                            wraplength=220, justify="center")
lbl_estado_desc.pack(pady=(4, 0))

tk.Frame(estado_card, bg=BORDER_COLOR, height=1).pack(fill="x", padx=14, pady=6)

tk.Label(estado_card, text="Capacidad máxima permitida",
         font=("Helvetica", 9), bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(0, 2))
lbl_max_display = tk.Label(estado_card, text="—",
                            font=("Helvetica", 30, "bold"), bg=BG_CARD, fg=TEXT_PRIMARY)
lbl_max_display.pack()
tk.Label(estado_card, text="personas", font=("Helvetica", 9),
         bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(0, 12))

# PANEL CONFIGURACIÓN

tk.Frame(root, bg=BORDER_COLOR, height=1).pack(fill="x", padx=0)

config_bar = tk.Frame(root, bg=BG_CARD, height=140)
config_bar.pack(fill="x")
config_bar.pack_propagate(False)

inner_cfg = tk.Frame(config_bar, bg=BG_CARD)
inner_cfg.pack(side="left", padx=20, pady=14)

frm_cfg_title = tk.Frame(inner_cfg, bg=BG_CARD)
frm_cfg_title.pack(anchor="w")
tk.Label(frm_cfg_title, text="", font=("Helvetica", 14), bg=BG_CARD, fg=ACCENT_BLUE).pack(side="left")
tk.Label(frm_cfg_title, text="  CONFIGURACIÓN DEL SISTEMA",
         font=("Helvetica", 11, "bold"), bg=BG_CARD, fg=TEXT_PRIMARY).pack(side="left")

frm_cfg_cols = tk.Frame(inner_cfg, bg=BG_CARD)
frm_cfg_cols.pack(anchor="w", pady=(8, 0))

frm_cap = tk.Frame(frm_cfg_cols, bg=BG_CARD)
frm_cap.pack(side="left", padx=(0, 40))

tk.Label(frm_cap, text="Capacidad máxima de personas permitidas",
         font=("Helvetica", 9), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

frm_spinner = tk.Frame(frm_cap, bg=BG_CARD2, padx=8, pady=8)
frm_spinner.pack(anchor="w", pady=6)

entry_frame = tk.Frame(frm_spinner, bg=ACCENT_BLUE, padx=2, pady=2)
entry_frame.pack(side="left", padx=4)

entry_personas = tk.Entry(
    entry_frame,
    textvariable=spinbox_var,
    font=("Helvetica", 28, "bold"),
    bg="#0d1b2e", fg="#ffffff",
    insertbackground="#ffffff",
    readonlybackground="#0d1b2e",
    relief="flat", bd=0,
    width=6,
    justify="center",
    state="normal",
    validate="key",
    validatecommand=(valida_digitos, '%P')
)
entry_personas.pack(ipady=6, ipadx=4)

def al_hacer_clic_entry(event):
    if running:
        messagebox.showwarning(
            "Sistema activo",
            "Primero debe detener el sistema para intentar modificar el número de personas permitidas."
        )

entry_personas.bind("<Button-1>", al_hacer_clic_entry)

tk.Label(frm_cap, text="Ingresa el límite máximo de aforo con tu teclado.",
         font=("Helvetica", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

# Estado sistema

frm_est = tk.Frame(frm_cfg_cols, bg=BG_CARD)
frm_est.pack(side="left", padx=(0, 40))

tk.Label(frm_est, text="Estado del sistema",
         font=("Helvetica", 9), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w")

frm_est_badge = tk.Frame(frm_est, bg=BG_CARD2, padx=14, pady=6)
frm_est_badge.pack(anchor="w", pady=4)

lbl_sistema_estado = tk.Label(frm_est_badge, text="● INACTIVO",
                               font=("Helvetica", 11, "bold"),
                               bg=BG_CARD2, fg=TEXT_MUTED)
lbl_sistema_estado.pack()

lbl_sistema_desc = tk.Label(frm_est, text="El sistema está detenido.",
                             font=("Helvetica", 8), bg=BG_CARD, fg=TEXT_MUTED)
lbl_sistema_desc.pack(anchor="w")

# Botón iniciar

frm_btn = tk.Frame(config_bar, bg=BG_CARD)
frm_btn.pack(side="right", padx=20, pady=14)

btn_guardar = tk.Button(
    frm_btn,
    text="  Iniciar sistema",
    font=("Helvetica", 12, "bold"),
    bg=ACCENT_BLUE, fg="white",
    activebackground="#2563eb", activeforeground="white",
    relief="flat", bd=0,
    padx=24, pady=14,
    cursor="hand2",
    command=guardar_cambios
)
btn_guardar.pack()

tk.Label(frm_btn, text="Ingrese la capacidad y presione Iniciar",
         font=("Helvetica", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(4, 0))

# FOOTER

footer = tk.Frame(root, bg=BG_CARD, height=32)
footer.pack(fill="x")
footer.pack_propagate(False)

tk.Label(
    footer,
    text="ℹ  Asegúrase que la cámara tenga una vista clara del área para un conteo preciso.",
    font=("Helvetica", 9), bg=BG_CARD, fg=TEXT_MUTED
).pack(side="left", padx=16, pady=6)

# CLEANUP AL CERRAR

def on_close():
    global running, cap
    running = False

    apagar_actuadores()

    if cap:
        cap.release()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_close)

root.mainloop()