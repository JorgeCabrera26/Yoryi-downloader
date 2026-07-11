from flask import Flask, render_template, request, send_file
import yt_dlp
import os

# Ruta del proyecto
base_dir = os.path.dirname(os.path.abspath(__file__))
cookies_path = os.path.join(base_dir, 'cookies.txt')

# Verificar cookies.txt
if os.path.exists(cookies_path):
    print("cookies encontradas:", True)
    print("Tamaño:", os.path.getsize(cookies_path))
else:
    print("No se encontró cookies.txt")

app = Flask(__name__)

CARPETA_DESCARGAS = os.path.join(os.getcwd(), 'descargas_temp')
os.makedirs(CARPETA_DESCARGAS, exist_ok=True)


@app.route('/')
def inicio():
    return render_template('index.html', info=None)


@app.route('/analizar', methods=['POST'])
def analizar():
    url = request.form.get('url')

    ydl_opts = {
        'format': 'best',
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'extractor_args': {
            'youtube': {
                'player_client': ['web'],
            }
        },
        'check_formats': False,
        'dynamic_mpd': False
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            meta = ydl.extract_info(url, download=False)

            formatos_filtrados = []
            formatos_vistos = set()

            for f in meta.get('formats', []):
                if f.get('height'):
                    res_label = f"{f['height']}p"

                    if res_label not in formatos_vistos:
                        formatos_vistos.add(res_label)

                        filesize = f.get('filesize') or f.get('filesize_approx')
                        filesize_mb = round(filesize / (1024 * 1024), 1) if filesize else None

                        formatos_filtrados.append({
                            'id': f['format_id'],
                            'res': res_label,
                            'ext': f.get('ext', 'mp4').upper(),
                            'filesize': filesize_mb
                        })

            formatos_filtrados.sort(
                key=lambda x: int(x['res'].replace('p', '')),
                reverse=True
            )

            video_data = {
                'url': url,
                'title': meta.get('title', 'Video'),
                'thumbnail': meta.get('thumbnail'),
                'formats': formatos_filtrados
            }

            return render_template('index.html', info=video_data)

    except Exception as e:
        return f"Error al analizar el enlace:<br><br>{str(e)}", 400


@app.route('/descargar', methods=['POST'])
def descargar():
    url = request.form.get('url')
    format_id = request.form.get('format_id')

    ydl_opts = {
        'outtmpl': os.path.join(CARPETA_DESCARGAS, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookies_path,
        'extractor_args': {
            'youtube': {
                'player_client': ['android'],
                'skip': ['webpage', 'configs']
            }
        },
        'check_formats': False,
        'dynamic_mpd': False
    }

    if format_id == 'bestaudio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = f'{format_id}+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

            archivo_descargado = ydl.prepare_filename(info)

            if not os.path.exists(archivo_descargado):
                for archivo in os.listdir(CARPETA_DESCARGAS):
                    ruta = os.path.join(CARPETA_DESCARGAS, archivo)
                    if os.path.isfile(ruta):
                        archivo_descargado = ruta
                        break

            respuesta = send_file(
                archivo_descargado,
                as_attachment=True
            )

            @respuesta.call_on_close
            def borrar_archivo():
                try:
                    if os.path.exists(archivo_descargado):
                        os.remove(archivo_descargado)
                except Exception as e:
                    print("No se pudo borrar:", e)

            return respuesta

    except Exception as e:
        return f"Error durante la descarga:<br><br>{str(e)}", 500


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False
    )
