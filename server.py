from transformers import pipeline
from flask import Flask, request, jsonify
from flask_cors import CORS
from pdfminer.high_level import extract_text
from googletrans import Translator
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
import os
import tempfile
import language_tool_python

app = Flask(__name__)
CORS(app)

# Inicializar LanguageTool para o idioma desejado
tool = language_tool_python.LanguageToolPublicAPI("en")  # Substituir "en" pelo idioma desejado

def correct_with_languagetool(text, language):
    tool = language_tool_python.LanguageToolPublicAPI(language)
    matches = tool.check(text)
    corrected_text = language_tool_python.utils.correct(text, matches)
    return corrected_text

# Criar pipeline de correção ortográfica com Hugging Face
corrector = pipeline("text2text-generation", model="t5-small")

translator = Translator()

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/', methods=['GET'])
def home():
    return jsonify({'message': 'Servidor funcionando!'})

@app.route('/translate-pdf', methods=['POST'])
def translate_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400

    if 'targetLanguage' not in request.form:
        return jsonify({'error': 'Idioma de destino não especificado'}), 400

    pdf_file = request.files['file']
    target_language = request.form['targetLanguage']
    
    try:
        # Salvar o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(pdf_file.read())
            temp_file_path = temp_file.name

        # Contar o número de páginas do PDF
        reader = PdfReader(temp_file_path)
        num_pages = len(reader.pages)

        # Extrair texto do PDF
        text = extract_text(temp_file_path)

        # Detectar o idioma do texto
        detected_language = translator.detect(text).lang

        # Traduzir o texto para o idioma de destino, se necessário
        if detected_language != target_language:
            translated_text = translator.translate(text, src=detected_language, dest=target_language).text

        else:
            translated_text = text  # Caso o idioma já seja o target_language, não há tradução

        # Retornar os textos original e traduzido, junto com o número de páginas
        return jsonify({
            'originalText': text,
            'translatedText': translated_text,
            'originalLanguage': detected_language,
            'numPages': num_pages
        })
        

    except Exception as e:
        return jsonify({'error': f'Erro interno no servidor: {str(e)}'}), 500

    finally:
        # Remover o arquivo temporário
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)



@app.route('/correct-text', methods=['POST'])
def correct_text():
    if 'file' not in request.files:
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    if 'sourceLanguage' not in request.form:
        return jsonify({'error': 'Idioma de origem não especificado'}), 400

    file = request.files['file']
    source_language = request.form['sourceLanguage']
    
    try:
        # Salvar o arquivo temporariamente
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(file.read())
            temp_file_path = temp_file.name
        
        # Contar o número de páginas do PDF
        reader = PdfReader(temp_file_path)
        num_pages = len(reader.pages)    

        # Extrair texto do PDF
        text = extract_text(temp_file_path)

        # Detectar o idioma do texto
        detected_language = translator.detect(text).lang

        # Corrigir o texto usando Hugging Face
        corrected_text = corrector(text)[0]['generated_text']

        return jsonify({
            'originalText': text,
            'correctedText': corrected_text,
            'originalLanguage': detected_language,
            'numPages': num_pages
        })

    except Exception as e:
        print(f"Erro ao corrigir texto: {str(e)}")
        return jsonify({'error': f'Erro interno no servidor: {str(e)}'}), 500

    finally:
        # Remover o arquivo temporário
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.route('/upload-pdf', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nome do arquivo vazio"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    return jsonify({"fileUrl": file_path})

if __name__ == '__main__':
    app.run(debug=True)


#test API