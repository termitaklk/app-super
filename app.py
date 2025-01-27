import os
from tkinter import Tk, filedialog, Button, Label, messagebox, ttk, CENTER
from smb.SMBConnection import SMBConnection

class SMBUploaderApp:
    def __init__(self, master):
        self.master = master
        self.master.title("SMB Image Uploader")

        # Centrar ventana
        window_width = 500
        window_height = 300
        screen_width = self.master.winfo_screenwidth()
        screen_height = self.master.winfo_screenheight()
        x_cordinate = int((screen_width/2) - (window_width/2))
        y_cordinate = int((screen_height/2) - (window_height/2))
        self.master.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")

        self.label = Label(master, text="Selecciona imágenes para subir:")
        self.label.pack(pady=10)

        self.select_button = Button(master, text="Seleccionar Imágenes", command=self.select_images)
        self.select_button.pack(pady=10)

        self.upload_button = Button(master, text="Subir Imágenes", command=self.upload_images, state="disabled")
        self.upload_button.pack(pady=10)

        self.progress_label = Label(master, text="Progreso: 0/0 archivos")
        self.progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(master, orient="horizontal", length=300, mode="determinate")
        self.progress_bar.pack(pady=10)

        self.selected_files = []

        # Configuración de conexión SMB
        self.smb_server = "192.168.50.252"  # Cambia esto a la IP o nombre del servidor SMB
        self.smb_share = "fotos"  # Nombre del recurso compartido principal
        self.smb_user = "duanel"  # Cambia esto al usuario SMB
        self.smb_password = "2goP&Lxf"  # Cambia esto a la contraseña SMB

    def select_images(self):
        filetypes = [("Imágenes", "*.png *.jpg *.jpeg *.bmp *.gif")]
        files = filedialog.askopenfilenames(title="Selecciona imágenes", filetypes=filetypes)
        if files:
            self.selected_files = files
            self.upload_button.config(state="normal")
            self.progress_bar["maximum"] = len(files)
            self.progress_label.config(text=f"Progreso: 0/{len(files)} archivos")
            messagebox.showinfo("Archivos seleccionados", f"Se seleccionaron {len(files)} archivos.")

    def upload_images(self):
        try:
            # Establece la conexión SMB
            conn = SMBConnection(
                self.smb_user, self.smb_password, "cliente", "servidor", use_ntlm_v2=True, is_direct_tcp=True
            )
            conn.connect(self.smb_server, 445)

            total_files = len(self.selected_files)
            for idx, file in enumerate(self.selected_files):
                with open(file, "rb") as f:
                    file_name = os.path.basename(file)
                    remote_path = f"CENOTE/{file_name}"
                    conn.storeFile(self.smb_share, remote_path, f)

                # Actualizar barra de progreso
                self.progress_bar["value"] = idx + 1
                self.progress_label.config(text=f"Progreso: {idx + 1}/{total_files} archivos")
                self.master.update_idletasks()

            conn.close()
            messagebox.showinfo("Éxito", "¡Imágenes subidas correctamente!")
            self.selected_files = []
            self.upload_button.config(state="disabled")
            self.progress_bar["value"] = 0
            self.progress_label.config(text="Progreso: 0/0 archivos")
        except Exception as e:
            messagebox.showerror("Error", f"Error al subir imágenes: {str(e)}")

if __name__ == "__main__":
    root = Tk()
    app = SMBUploaderApp(root)
    root.mainloop()

