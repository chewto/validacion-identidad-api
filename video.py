import ffmpeg
import json

def get_video_metadata(video_file_path):
    """
    Extrae la metadata clave de la stream de video de un archivo, ignorando el audio.

    Args:
        video_file_path (str): La ruta al archivo de video.

    Returns:
        dict: Un diccionario con la metadata de video, o None si hay un error
              o no se encuentra una stream de video.
    """
    try:
        probe = ffmpeg.probe(video_file_path)
        streams = probe['streams']

        video_metadata = None

        for stream in streams:
            if stream['codec_type'] == 'video':
                video_metadata = {
                    'codec_name': stream.get('codec_name'),
                    'codec_long_name': stream.get('codec_long_name'),
                    'width': stream.get('width'),
                    'height': stream.get('height'),
                    'display_aspect_ratio': stream.get('display_aspect_ratio'),
                    'avg_frame_rate': stream.get('avg_frame_rate'),
                    'r_frame_rate': stream.get('r_frame_rate'),
                    'pix_fmt': stream.get('pix_fmt'),
                    'duration_ts': stream.get('duration_ts'),
                    'duration': stream.get('duration'),
                    'bit_rate': stream.get('bit_rate')
                }
                # Una vez que encontramos la stream de video, podemos salir del bucle
                break 
        
        format_info = probe.get('format', {})
        global_duration = format_info.get('duration')
        global_bit_rate = format_info.get('bit_rate')

        return {
            'video': video_metadata,
            'global_duration': global_duration,
            'global_bit_rate': global_bit_rate
        }

    except ffmpeg.Error as e:
        print(f"Error al procesar el archivo '{video_file_path}': {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        print(f"Error: El archivo '{video_file_path}' no fue encontrado.")
        return None
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")
        return None

# --- Ejemplo de uso ---
if __name__ == "__main__":
    test_video_file = "../fotos-prueba/iphone test.webm" # ¡Cambia esto por la ruta a tu video!
    output_video_file = "../fotos-prueba/mi_video_sin_audio_convertido.mp4"

    # Puedes crear un video de prueba pequeño si no tienes uno
    # Por ejemplo, usando ffmpeg en la terminal (si quieres audio en el original):
    # ffmpeg -f lavfi -i testsrc=s=640x480:r=30 -f lavfi -i sine=frequency=1000:duration=5 -t 5 -c:v libx264 -c:a opus mi_video_ejemplo.mp4

    metadata = get_video_metadata(test_video_file)

    if metadata and metadata['video']:
        print("--- Metadata de la Stream de Video ---")
        print(json.dumps(metadata['video'], indent=2))

        print(f"\nResolución: {metadata['video']['width']}x{metadata['video']['height']}")
        print(f"FPS: {metadata['video']['avg_frame_rate']}")
        print(f"Codec de Video: {metadata['video']['codec_name']}")
        print(f"Duración Total del Archivo: {float(metadata['global_duration']):.2f} segundos")

        # --- CONVERSIÓN DEL VIDEO SIN AUDIO ---
        # Aquí es donde realizamos la conversión, ignorando explícitamente el audio.
        # Por ejemplo, vamos a convertirlo a 720p y asegurar el codec h264, sin audio.
        target_width = 1280
        target_height = metadata['video']['height']
        target_width = metadata['video']['width']
        target_codec = 'libx264' # Un codec de video común

        print(f"\n-- Iniciando conversión de '{test_video_file}' a {target_width}x{target_height} ({target_codec}), SIN AUDIO --")
        
        try:
            ffmpeg.input(test_video_file).output(
                output_video_file,
                # 'vf' para filtro de video (escala), 'c:v' para codec de video
                vf=f'scale={target_width}:{target_height}',
                vcodec=target_codec, # Recodifica el video
                an=None, # IMPORTANTE: Esto le dice a FFmpeg que NO incluya la stream de audio
                loglevel='error' # Muestra solo errores
            ).run(overwrite_output=True) # Sobrescribe si el archivo de salida ya existe
            print(f"Video convertido y guardado como '{output_video_file}'")
  
        except ffmpeg.Error as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            print(f"Error durante la conversión: {error_msg}")
        except Exception as e:
            print(f"Ocurrió un error inesperado durante la conversión: {e}")
        print(f"No se encontró una stream de video en '{test_video_file}'.")
    else:
        print(f"No se pudo obtener metadata para '{test_video_file}'.")