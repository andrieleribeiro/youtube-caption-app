from flask import Flask, render_template, request
import subprocess, os, re

app = Flask(__name__)

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
        'yt-dlp', '--write-auto-sub', '--sub-lang', lang_code,
        '--skip-download', '--output', f'{video_id}.%(ext)s', video_url
    ]
    subprocess.run(comando, check=True)

def encontrar_arquivo_vtt(video_id, lang_priority):
    for lang in lang_priority:
        nome_arquivo = f"{video_id}.{lang}.vtt"
        if os.path.exists(nome_arquivo):
            return nome_arquivo
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
    resultado, ultimo = [], ''
    for linha in linhas:
        if linha != ultimo:
            resultado.append(linha)
        ultimo = linha
    return "\n".join(resultado)

@app.route('/', methods=['GET', 'POST'])
def index():
    legenda, erro = None, None
    if request.method == 'POST':
        url = request.form['url'].strip()
        video_id = extrair_video_id(url)
        if not video_id:
            erro = "URL inválida."
        else:
            try:
                lista = listar_legendas(url)
                print(lista)  # Adicione esta linha
                prioridade = ['pt', 'pt-BR', 'pt-orig', 'pt-PT', 'en']
                idioma_encontrado = next((lang for lang in prioridade if f'\n{lang}' in lista or f' {lang} ' in lista), None)
                if not idioma_encontrado:
                    match_idiomas = re.findall(r'^\s*([a-zA-Z\-]+)\s', lista, re.MULTILINE)
                    if match_idiomas:
                        idioma_encontrado = match_idiomas[0]
                    else:
                        erro = "Nenhuma legenda disponível para este vídeo."
                if idioma_encontrado:
                    baixar_legenda(url, idioma_encontrado, video_id)
                    caminho_vtt = encontrar_arquivo_vtt(video_id, prioridade)
                    if caminho_vtt:
                        legenda = limpar_legenda(caminho_vtt)
                        os.remove(caminho_vtt)
                    else:
                        erro = "Legenda baixada não encontrada."
            except Exception as e:
                erro = f"Erro: {str(e)}"
    return render_template('index.html', legenda=legenda, erro=erro)

if __name__ == '__main__':
    app.run(debug=True)
