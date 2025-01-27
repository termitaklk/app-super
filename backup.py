import os
import subprocess
from imageio_ffmpeg import get_ffmpeg_exe

def generar_clips_y_unir(input_path, output_dir, output_final):
    """
    Genera clips comprimidos directamente con FFmpeg y los une en un único archivo.

    Parámetros:
        input_path (str): Ruta del archivo de video original.
        output_dir (str): Carpeta donde se guardarán los clips.
        output_final (str): Ruta del archivo de video final unificado.

    Retorna:
        None
    """
    try:
        # Obtener la ruta de FFmpeg
        ffmpeg_path = get_ffmpeg_exe()

        # Validar la existencia del archivo de entrada
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"El archivo de entrada no existe: {input_path}")

        # Crear la carpeta de salida si no existe
        os.makedirs(output_dir, exist_ok=True)

        # Normalizar las rutas
        input_path = os.path.normpath(input_path)
        output_dir = os.path.normpath(output_dir)
        output_final = os.path.normpath(output_final)

        # Definir los rangos de tiempo para los clips (en segundos)
        rangos = [
            (60, 20),   # Primer clip: desde el segundo 60 por 20 segundos
            (120, 40),  # Segundo clip: desde el segundo 120 por 40 segundos
            (180, 20),  # Tercer clip: desde el segundo 180 por 20 segundos
        ]

        # Generar cada clip directamente con FFmpeg
        clips_paths = []
        for i, (inicio, duracion) in enumerate(rangos):
            output_clip_path = os.path.join(output_dir, f"clip_{i+1}.mp4")
            output_clip_path = os.path.normpath(output_clip_path)  # Normalizar ruta
            clips_paths.append(output_clip_path)
            cmd = [
                ffmpeg_path,
                "-y",  # Sobrescribir si el archivo existe
                "-ss", str(inicio),  # Búsqueda rápida para evitar acumulación de tiempos
                "-i", input_path,  # Archivo de entrada
                "-t", str(duracion),  # Duración del clip
                "-vf", "scale=854:480",  # Reducir a 480p
                "-c:v", "libx264",  # Códec de video
                "-crf", "30",  # Nivel de compresión
                "-preset", "ultrafast",  # Mayor compresión
                "-c:a", "aac",  # Códec de audio
                "-b:a", "128k",  # Bitrate de audio
                output_clip_path,
            ]
            print(f"Generando clip {i+1}: {output_clip_path}")
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Verificar si FFmpeg falló
            if result.returncode != 0:
                print(f"Error en FFmpeg: {result.stderr}")
                raise RuntimeError(f"Error al generar el clip {i+1}: {result.stderr}")

        # Crear un archivo de lista para FFmpeg
        concat_list_path = os.path.join(output_dir, "concat_list.txt")
        concat_list_path = os.path.normpath(concat_list_path)  # Normalizar ruta
        with open(concat_list_path, "w") as f:
            for clip_path in clips_paths:
                f.write(f"file '{clip_path.replace(os.sep, '/')}'\n")

        # Unir los clips en un único archivo
        cmd_concat = [
            ffmpeg_path,
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_path,
            "-c:v", "libx264",
            "-crf", "30",
            "-preset", "ultrafast",
            "-c:a", "aac",
            "-b:a", "128k",
            output_final,
        ]
        print(f"Uniendo clips en: {output_final}")
        result = subprocess.run(cmd_concat, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Verificar si FFmpeg falló en la concatenación
        if result.returncode != 0:
            print(f"Error en FFmpeg durante la concatenación: {result.stderr}")
            raise RuntimeError(f"Error al unir los clips: {result.stderr}")

        print(f"Archivo unificado generado correctamente: {output_final}")

    except Exception as e:
        print(f"Error al generar los clips y unirlos: {e}")

if __name__ == "__main__":
    # Parámetros de entrada
    input_video_path = r"C:/data/video.mp4"  # Ruta del video original
    output_dir = r"C:/data/clips"  # Carpeta donde se guardarán los clips
    output_final_path = r"C:/data/final/final_video.mp4"  # Ruta del video unificado

    # Generar los clips y unirlos
    generar_clips_y_unir(input_path=input_video_path, output_dir=output_dir, output_final=output_final_path)

