from flask import Flask, request
import subprocess
import os
import re

app = Flask(__name__)

prioridade_idiomas = ['pt', 'pt-BR', 'pt-orig', 'pt-PT', 'en']


def extrair_video_id(url):
    padroes = [
        r'(?:https?://)?(?:www\.)?youtu\.be/([^?&]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([^&]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([^?&]+)',
        r'(?:https?://)?(?:www\.)?youtube\.com/v/([^?&]+)',
    ]
    for padrao in padroes:
        match = re.search(padrao, url)
        if match:
            return match.group(1)
    return None


def listar_legendas(video_url):
    comando = ['yt-dlp', '--list-subs', video_url]
    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.stdout


def baixar_legenda(video_url, lang_code, video_id):
    comando = [
        'yt-dlp',
        '--write-auto-sub',
        '--sub-lang', lang_code,
        '--skip-download',
        '--output', f'{video_id}.%(ext)s',
        video_url
    ]
    subprocess.run(comando, check=True)
    return os.listdir('.')


def encontrar_arquivo_vtt(video_id):
    for arquivo in os.listdir('.'):
        if arquivo.startswith(video_id) and arquivo.endswith('.vtt'):
            return arquivo
    return None


def limpar_legenda(caminho_arquivo):
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        conteudo = f.read()

    conteudo = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*', '', conteudo)
    conteudo = re.sub(r'^(WEBVTT.*|Kind:.*|Language:.*)$', '', conteudo, flags=re.MULTILINE)
    conteudo = re.sub(r'<.*?>', '', conteudo)
    conteudo = re.sub(r'\[.*?\]', '', conteudo)

    linhas = [linha.strip() for linha in conteudo.splitlines() if linha.strip()]
    resultado = []
    ultimo = ''
    for linha in linhas:
        if linha != ultimo:
            resultado.append(linha)
        ultimo = linha

    return "\n".join(resultado)


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url', '').strip()
        video_id = extrair_video_id(url)

        log = [f"🔗 URL: {url}", f"🎥 ID: {video_id}"]

        if not video_id:
            return "<pre>❌ Erro: ID do vídeo não encontrado.\n" + '\n'.join(log) + "</pre>"

        try:
            lista = listar_legendas(url)
            log.append("\n📄 Lista de legendas encontradas:\n" + lista)
        except Exception as e:
            return f"<pre>❌ Erro ao listar legendas: {e}\n{chr(10).join(log)}</pre>"

        idioma_encontrado = None
        for idioma in prioridade_idiomas:
            if f'\n{idioma}' in lista or f' {idioma} ' in lista:
                idioma_encontrado = idioma
                break

        if not idioma_encontrado:
            match_idiomas = re.findall(r'^\s*([a-zA-Z\-]+)\s', lista, re.MULTILINE)
            if match_idiomas:
                idioma_encontrado = match_idiomas[0]
            else:
                return f"<pre>❌ Nenhuma legenda disponível.\n{chr(10).join(log)}</pre>"

        log.append(f"✅ Idioma escolhido: {idioma_encontrado}")

        try:
            arquivos = baixar_legenda(url, idioma_encontrado, video_id)
            log.append("📦 Arquivos no diretório após download:\n" + '\n'.join(arquivos))
        except subprocess.CalledProcessError as e:
            return f"<pre>❌ Erro ao baixar legenda: {e}\n{chr(10).join(log)}</pre>"

        vtt_path = encontrar_arquivo_vtt(video_id)
        if not vtt_path:
            return f"<pre>❌ Arquivo VTT não encontrado.\n{chr(10).join(log)}</pre>"

        log.append(f"📁 Arquivo VTT encontrado: {vtt_path}")

        legenda_final = limpar_legenda(vtt_path)
        os.remove(vtt_path)

        return f"<pre>{chr(10).join(log)}\n\n📃 LEGENDA:\n{legenda_final}</pre>"

    return '''
        <form method="post">
            <label>URL do vídeo do YouTube:</label><br>
            <input type="text" name="url" size="80"><br><br>
            <input type="submit" value="Gerar Legenda">
        </form>
    '''


if __name__ == '__main__':
    app.run(debug=True)
