from flask import Flask, render_template, request, send_file
import yt_dlp
import execjs 
import os

# Obtiene la ruta de la carpeta actual donde corre tu script
base_dir = os.path.dirname(os.path.abspath(__file__))
cookies_path = os.path.join(base_dir, 'cookies.txt')

#Esto carga las cookies desde la variable de entorno que configuraste en render
cookies_content = os.getenv('COOKIES_CONTENT')

cookies_content = os.getenv('COOKIES_CONTENT')
if cookies_content:
    # Reemplaza saltos de línea literales si Render los guardó como texto '\n'
    cookies_content = cookies_content.replace('\\n', '\n')
    with open('cookies.txt', 'w', encoding='utf-8') as f:
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
        'format': 'best',
        'ignoreerrors': True,
        'no_warnings': True
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
        'format': 'best',
        'noplaylist': True,
        'ignoreerrors': True,
        'no_warnings': True
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
