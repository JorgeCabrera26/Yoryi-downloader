from flask import Flask, render_template, request, send_file
import yt_dlp
import execjs 
import os

#Esto carga las cookies desde la variable de entorno que configuraste en render
cookies_content = os.getenv('COOKIES_CONTENT')

if cookies_content:
    with open('cookies.txt', 'w') as f:
        f.write(cookies_content)
  

app = Flask(__name__)

CARPETA_DESCARGAS = os.path.join(os.getcwd(), 'descargas_temp')
if not os.path.exists(CARPETA_DESCARGAS):
    os.makedirs(CARPETA_DESCARGAS)

@app.route('/')
def inicio():
    return render_template('index.html', info=None)

@app.route('/analizar', methods=['POST'])
def analizar():
    url = request.form.get('url')
    
    ydl_opts = {
        'outtmpl': os.path.join(CARPETA_DESCARGAS, '%(title)s.%(ext)s'),
        'format': 'best', # <-- Forzar 'best' simple
        'noplaylist': True,
        'quiet': False,
        'no_warnings': False,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'], # <-- Usar clientes móviles que no piden cookies estrictas
                'skip': ['dash', 'hls']
            }
        }
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
            
            formatos_filtrados.sort(key=lambda x: int(x['res'].replace('p','')), reverse=True)

            video_data = {
                'url': url,
                'title': meta.get('title', 'Video de Internet'),
                'thumbnail': meta.get('thumbnail'),
                'formats': formatos_filtrados
            }
            return render_template('index.html', info=video_data)
    except Exception as e:
        return f"Error al analizar el enlace: {str(e)}", 400

@app.route('/descargar', methods=['POST'])
def descargar():
    url = request.form.get('url')
    format_id = request.form.get('format_id')
    
    ydl_opts = {
        'outtmpl': os.path.join(CARPETA_DESCARGAS, '%(title)s.%(ext)s'),
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'cookiefile': 'cookies.txt',
        'format': 'bestvideo+bestaudio/best', # <--- CAMBIA ESTA LÍNEA (Intenta el mejor video y audio combinados, o el mejor que venga solo)
        'noplaylist': True,
        'external_downloader_args': ['--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'],
    }
    
    if format_id == 'bestaudio':
        ydl_opts['format'] = 'bestaudio/best'
    else:
        ydl_opts['format'] = f'{format_id}/bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            archivo_descargado = ydl.prepare_filename(info)
            
            # Creamos una función interna para borrar el archivo de la carpeta temporal 
            # justo después de enviar la respuesta al navegador del usuario
            def borrar_archivo_despues(response):
                try:
                    if os.path.exists(archivo_descargado):
                        os.remove(archivo_descargado)
                except Exception as e:
                    print(f"No se pudo borrar el archivo temporal: {e}")
                return response

            app.after_request(borrar_archivo_despues)
            
            return send_file(archivo_descargado, as_attachment=True)
    except Exception as e:
        return f"Error durante la descarga: {str(e)}", 500

if __name__ == '__main__':
    # Ponemos debug=False para producción y seguridad en internet
    app.run(debug=False)
