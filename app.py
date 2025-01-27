import tkinter as tk
from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES
import cv2
from PIL import Image, ImageTk
import threading
import time

def format_time(seconds):
    """Convierte segundos a formato Minutos:Segundos."""
    seconds = int(seconds)  # Convertir a entero para evitar errores de formato
    minutes = seconds // 60
    seconds = seconds % 60
    return f"{minutes}:{seconds:02d}"  # Formato mm:ss

def threaded(func):
    """Decorador para ejecutar una función en un hilo separado."""
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=func, args=args, kwargs=kwargs)
        thread.daemon = True
        thread.start()
        return thread
    return wrapper

class ClipEditorApp:
    def __init__(self, root):
        self.timeline_locked = True  # Bloquear línea de tiempo al inicio
        self.root = root
        self.root.title("Editor de Clips con Arrastrar y Soltar")
        self.root.geometry("900x700")

        # Variables globales
        self.video_path = None
        self.cap = None
        self.running = False
        self.video_thread = None
        self.lock = threading.Lock()
        self.start_pos = 0
        self.end_pos = 100
        self.selected_clip = None
        self.clip_data = {"clip1": {"start": 0, "end": 0}, "clip2": {"start": 0, "end": 0}, "clip3": {"start": 0, "end": 0}}

        # Panel de previsualización
        self.preview_label = tk.Label(self.root, bg="black", width=800, height=400)
        self.preview_label.pack(pady=10)

        # Mensaje inicial
        self.show_placeholder_message()

        # Barra de tiempo estilizada
        self.time_frame = tk.Frame(self.root, bg="white", relief="flat", bd=1)
        self.time_frame.pack(pady=5)

        self.time_scale = tk.Canvas(self.time_frame, width=800, height=20, bg="lightgray", bd=0, highlightthickness=1, highlightbackground="black")
        self.time_scale.pack(pady=5)

        # Dibujar los manejadores estilizados
        self.start_handle = self.time_scale.create_rectangle(0, 2, 15, 18, fill="#007BFF", outline="black", tags="start")  # Azul
        self.end_handle = self.time_scale.create_rectangle(785, 2, 800, 18, fill="#FF4136", outline="black", tags="end")  # Rojo

        # Conectar eventos de los deslizadores
        self.time_scale.tag_bind("start", "<B1-Motion>", self.move_start_handle)
        self.time_scale.tag_bind("start", "<ButtonRelease-1>", self.sync_video_with_start)
        self.time_scale.tag_bind("end", "<B1-Motion>", self.move_end_handle)
        self.time_scale.tag_bind("end", "<ButtonRelease-1>", self.sync_video_with_end)

        self.speed_slider = tk.Scale(
            self.root,
            from_=0.5,  # 50% de velocidad (más lento)
            to=2.0,  # 200% de velocidad (más rápido)
            resolution=0.1,
            orient="horizontal",
            label="Velocidad de Reproducción",
            command=self.on_speed_change  # Conecta el callback
        )
        self.speed_slider.set(2.0)  # Velocidad normal
        self.speed_slider.pack(pady=10)

        self.speed_slider.pack(pady=10)

        # Contenedor para los recuadros de clips
        self.clip_frame = tk.Frame(self.root)
        self.clip_frame.pack(pady=10)

        self.clip_buttons = {}
        for i in range(1, 4):
            self.create_clip_box(f"Clip {i}", f"clip{i}")

        # Botón para cargar video
        self.load_button = tk.Button(self.root, text="Cargar Video", command=self.load_video)
        self.load_button.pack(pady=10)

        # Configuración de arrastrar y soltar
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.on_drop)

    def update_start_handle(self, x):
        """Actualiza la posición del manejador de inicio sin alterar su tamaño."""
        # Obtén las coordenadas actuales del deslizador
        _, y1, _, y2 = self.time_scale.coords(self.start_handle)
        width = 15  # Ancho del deslizador (mantenido constante)

        # Actualiza solo la posición x
        self.time_scale.coords(self.start_handle, x, y1, x + width, y2)
        
        # Calcula la posición en segundos
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.start_pos = (x / 800) * (total_frames / fps)  # Escalar x al rango de frames y convertir a segundos
        
        print(f"Inicio actualizado a: {self.start_pos:.2f} segundos")


    def update_end_handle(self, x):
        """Actualiza la posición del manejador de fin sin alterar su tamaño."""
        # Obtén las coordenadas actuales del deslizador
        _, y1, _, y2 = self.time_scale.coords(self.end_handle)
        width = 15  # Ancho del deslizador (constante)

        # Verifica límites para evitar que el deslizador de fin pase al inicio
        start_x = self.time_scale.coords(self.start_handle)[2]  # Borde derecho del deslizador de inicio
        if x - width <= start_x:
            x = start_x + width  # Ajusta la posición para no sobrepasar el deslizador de inicio

        # Actualiza solo la posición x
        self.time_scale.coords(self.end_handle, x - width, y1, x, y2)

        # Calcula la posición en segundos
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.end_pos = (x / 800) * (total_frames / fps)  # Escalar x al rango de frames y convertir a segundos
        
        print(f"Fin actualizado a: {self.end_pos:.2f} segundos")

    def show_placeholder_message(self):
        """Muestra un mensaje o imagen de bienvenida en la ventana de previsualización."""
        text = "Arrastra un video aquí para comenzar."
        self.preview_label.config(
            text=text,
            fg="white",
            font=("Helvetica", 16),
            justify="center"
        )

    def on_drop(self, event):
        """Maneja el evento de arrastrar y soltar."""
        file_path = event.data.strip()
        if file_path.startswith("{") and file_path.endswith("}"):
            file_path = file_path[1:-1]

        if not file_path.lower().endswith(('.mp4', '.mov', '.avi')):
            messagebox.showerror("Error", "Por favor, arrastra un archivo de video válido (.mp4, .mov, .avi).")
            return

        self.video_path = file_path
        self.load_video()

    @threaded
    def load_video(self):
        """Carga un video desde un archivo."""
        print(f"Cargando video: {self.video_path}")
        self.stop_video_thread()
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(self.video_path)
        if not self.cap.isOpened():
            print("Error: No se pudo abrir el video.")
            messagebox.showerror("Error", "No se pudo abrir el video.")
            return

        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        video_duration = total_frames / fps  # Duración total en segundos

        # Inicializar posiciones
        self.start_pos = 0
        self.end_pos = video_duration

        # Actualizar solo los valores internos, sin redibujar los recuadros
        self.timeline_locked = True
        self.selected_clip = None
        for key, frame in self.clip_buttons.items():
            frame.config(highlightbackground="black", highlightthickness=2)
            frame.start_label.config(text="Inicio: 0:00")
            frame.end_label.config(text=f"Final: {format_time(video_duration)}")

        print("Línea de tiempo bloqueada. Selecciona un clip para desbloquear.")
        self.show_first_frame()


    def show_first_frame(self):
        """Muestra el primer fotograma del video."""
        print("Mostrando primer fotograma.")
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = self.cap.read()
        if ret:
            self.display_frame(frame)

    def display_frame(self, frame):
        """Muestra el fotograma en la ventana."""
        # Rotar el fotograma si está de cabeza
        frame = cv2.rotate(frame, cv2.ROTATE_180)  # Rotar 180 grados si es necesario
        
        frame = cv2.resize(frame, (800, 400))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(image=Image.fromarray(frame))
        self.preview_label.config(image=img)
        self.preview_label.image = img

    def move_start_handle(self, event):
        """Mueve el manejador de inicio."""
        if self.timeline_locked or not self.selected_clip:
            print("Línea de tiempo bloqueada. Selecciona un clip para desbloquear.")
            return

        x = event.x
        end_x = self.time_scale.coords(self.end_handle)[0]  # Posición actual del deslizador de fin
        handle_width = 15  # Ancho del deslizador

        if 0 <= x <= end_x - handle_width:
            self.update_start_handle(x)  # Actualiza la posición del deslizador
            self.update_clip_values()   # Actualiza los valores del clip seleccionado
        else:
            print(f"[START HANDLE] Movimiento inválido: {x} está fuera de rango.")


    def move_end_handle(self, event):
        """Mueve el manejador de fin."""
        if self.timeline_locked or not self.selected_clip:
            print("Línea de tiempo bloqueada. Selecciona un clip para desbloquear.")
            return

        x = event.x
        start_x = self.time_scale.coords(self.start_handle)[2]  # Borde derecho del deslizador de inicio
        handle_width = 15  # Ancho del deslizador

        if start_x + handle_width <= x <= 800:
            self.update_end_handle(x)  # Actualiza la posición del deslizador
            self.update_clip_values()  # Actualiza los valores del clip seleccionado
        else:
            print(f"[END HANDLE] Movimiento inválido: {x} está fuera de rango.")


    def update_start_handle(self, x):
        """Actualiza la posición del manejador de inicio."""
        # Mantén las dimensiones del deslizador constantes
        _, y1, _, y2 = self.time_scale.coords(self.start_handle)
        width = 15  # Ancho del deslizador (mantenido constante)

        print(f"[UPDATE START] Antes de actualizar: {self.time_scale.coords(self.start_handle)}")

        # Actualiza solo la posición x
        self.time_scale.coords(self.start_handle, x, y1, x + width, y2)

        print(f"[UPDATE START] Después de actualizar: {self.time_scale.coords(self.start_handle)}")

        # Calcula la posición en segundos
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.start_pos = (x / 800) * (total_frames / fps)  # Escalar x al rango de frames y convertir a segundos
        
        print(f"[UPDATE START] Nueva posición: {self.start_pos:.2f} segundos")

    def update_end_handle(self, x):
        """Actualiza la posición del manejador de fin."""
        # Mantén las dimensiones del deslizador constantes
        _, y1, _, y2 = self.time_scale.coords(self.end_handle)
        width = 15  # Ancho del deslizador (mantenido constante)

        print(f"[UPDATE END] Antes de actualizar: {self.time_scale.coords(self.end_handle)}")

        # Actualiza solo la posición x
        self.time_scale.coords(self.end_handle, x - width, y1, x, y2)

        print(f"[UPDATE END] Después de actualizar: {self.time_scale.coords(self.end_handle)}")

        # Calcula la posición en segundos
        total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.end_pos = (x / 800) * (total_frames / fps)  # Escalar x al rango de frames y convertir a segundos
        
        print(f"[UPDATE END] Nueva posición: {self.end_pos:.2f} segundos")



    @threaded
    def stop_video_thread(self):
        """Detiene cualquier hilo de reproducción activo."""
        if self.running:
            print("Deteniendo reproducción de video.")
            self.running = False
            if self.video_thread and self.video_thread.is_alive():
                self.video_thread.join()
            print("Hilo de reproducción detenido.")

    @threaded
    def sync_video_with_start(self, event=None):
        """Sincroniza el video con la posición inicial."""
        if self.timeline_locked or not self.selected_clip:
            print("Línea de tiempo bloqueada o ningún clip seleccionado.")
            return

        print(f"Sincronizando inicio del video a {self.start_pos} segundos.")
        self.stop_video_thread()
        self.reopen_video(self.start_pos)

    @threaded
    def sync_video_with_end(self, event):
        """Sincroniza el video con la posición final."""
        print(f"Sincronizando final del video a {self.end_pos:.2f} segundos.")
        self.stop_video_thread()
        self.reopen_video(int(self.end_pos * self.cap.get(cv2.CAP_PROP_FPS)))

    @threaded
    def start_video_thread(self):
        """Inicia la reproducción del video en un hilo separado."""
        print("Iniciando reproducción de video.")
        self.running = True
        self.play_video()  # Llama directamente a play_video en el hilo decorado

    @threaded
    def reopen_video(self, position):
        """Libera el recurso actual y lo reabre en la nueva posición."""
        with self.lock:
            try:
                if self.cap:
                    print("Liberando recurso de video...")
                    self.cap.release()
                    print("Recurso de video liberado.")
                print("Reabriendo recurso de video...")
                self.cap = cv2.VideoCapture(self.video_path)
                if not self.cap.isOpened():
                    raise RuntimeError("Error: No se pudo abrir el recurso del video.")
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, position)
                print(f"Recurso de video reabierto en posición: {position} frames.")
                self.start_video_thread()
            except Exception as e:
                print(f"Error al reabrir el video: {e}")

    @threaded
    def play_video(self):
        """Reproduce el video desde la posición actual."""
        print("Iniciando reproducción del video.")
        try:
            fps = self.cap.get(cv2.CAP_PROP_FPS)  # Obtén los FPS del video
            if fps == 0:  # Si no se pueden obtener los FPS, usar un valor predeterminado
                fps = 30

            speed_factor = self.speed_slider.get()  # Velocidad seleccionada por el slider
            time.sleep(1 / (fps * speed_factor))  # Ajusta el tiempo de espera
            frames_to_skip = max(1, int(round(speed_factor)))  # Saltar frames según la velocidad
            print(f"Velocidad: {speed_factor}, Frames a saltar: {frames_to_skip}")

            with self.lock:
                while self.running and self.cap and self.cap.isOpened():
                    ret, frame = self.cap.read()
                    if not ret:
                        print("Fin del video o error al leer fotograma.")
                        break

                    self.display_frame(frame)

                    # Saltar frames para ajustar la velocidad
                    for _ in range(frames_to_skip - 1):  # Omitir frames
                        self.cap.grab()  # Avanzar al siguiente frame sin decodificar

                    time.sleep(1 / fps)  # Tiempo entre frames basado en FPS
            print("Finalizando reproducción del video.")
        except Exception as e:
            print(f"Error durante la reproducción: {e}")


    def on_speed_change(self, value):
        """Callback para manejar cambios en el slider de velocidad."""
        if self.running:
            print(f"Velocidad ajustada dinámicamente a: {value}")

    def create_clip_box(self, label, clip_key):
        """Crea un recuadro para cada clip."""
        frame = tk.Frame(
            self.clip_frame,
            width=200,
            height=100,
            relief="ridge",
            bd=2,
            bg="white",
            highlightbackground="black",
            highlightthickness=2,
        )
        frame.pack(side=tk.LEFT, padx=10, pady=5)

        # Título del clip
        label_title = tk.Label(frame, text=label, font=("Helvetica", 16), bg="white")
        label_title.pack()

        # Campos de inicio y fin
        label_start = tk.Label(frame, text="Inicio: 0:00", bg="white", font=("Helvetica", 10), width=15, anchor="w")
        label_start.pack()
        label_end = tk.Label(frame, text="Final: 0:00", bg="white", font=("Helvetica", 10), width=15, anchor="w")
        label_end.pack()

        # Vincular el evento de selección al recuadro y sus elementos
        frame.bind("<Button-1>", lambda e, ck=clip_key: self.select_clip(ck))
        label_title.bind("<Button-1>", lambda e, ck=clip_key: self.select_clip(ck))
        label_start.bind("<Button-1>", lambda e, ck=clip_key: self.select_clip(ck))
        label_end.bind("<Button-1>", lambda e, ck=clip_key: self.select_clip(ck))

        # Guardar referencias para actualizaciones
        frame.start_label = label_start
        frame.end_label = label_end
        self.clip_buttons[clip_key] = frame

    def select_clip(self, clip_key):
        """Selecciona un clip y actualiza el borde al color verde."""
        def update_selection():
            for key, frame in self.clip_buttons.items():
                frame.config(highlightbackground="black", highlightthickness=2)

            self.clip_buttons[clip_key].config(highlightbackground="green", highlightthickness=4)
            self.selected_clip = clip_key

            # Desbloquear la línea de tiempo
            self.timeline_locked = False
            print(f"Línea de tiempo desbloqueada para {clip_key}.")

        # Ejecutar la actualización después de un pequeño retraso
        self.root.after(50, update_selection)

    def update_clip_values(self):
        """Actualiza los valores de inicio y final en el recuadro del clip seleccionado."""
        if self.selected_clip:
            # Asegúrate de que start_pos y end_pos estén en segundos y sean enteros
            self.clip_data[self.selected_clip]["start"] = int(self.start_pos)
            self.clip_data[self.selected_clip]["end"] = int(self.end_pos)

            # Convertir los valores a Minutos:Segundos
            start_time = format_time(self.start_pos)
            end_time = format_time(self.end_pos)

            # Actualizar las etiquetas del recuadro seleccionado
            clip_frame = self.clip_buttons[self.selected_clip]
            clip_frame.start_label.config(text=f"Inicio: {start_time}")
            clip_frame.end_label.config(text=f"Final: {end_time}")
            print(f"Clip {self.selected_clip} actualizado: Inicio {start_time}, Final {end_time}")

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = ClipEditorApp(root)
    root.mainloop()