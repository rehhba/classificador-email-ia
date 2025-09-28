from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import PyPDF2
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  

# Configuração Hugging Face
HF_API_KEY = "hf_token" 
HF_CLASSIFY_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
HF_CHAT_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"

headers = {"Authorization": f"Bearer {HF_API_KEY}"}

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/', methods=['GET'])
def home():
    return jsonify({"message": "API de Classificação de Emails Online!"})

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'OK', 'message': 'Servidor funcionando'})

@app.route('/classify', methods=['POST', 'OPTIONS'])
def classify_email():
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        email_text = ""
        
        # Verificar se é upload de arquivo
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                email_text = read_uploaded_file(file)
                print(f"📁 Arquivo processado: {file.filename}")
        
        # Verificar se é JSON com texto
        elif request.is_json and request.json and 'email' in request.json:
            email_text = request.json.get('email', '')
            print("📝 Texto recebido via JSON")
        
        # Verificar se é form-data com texto
        elif request.form and 'email' in request.form:
            email_text = request.form.get('email', '')
            print("📝 Texto recebido via form-data")
        
        if not email_text or not email_text.strip():
            return jsonify({'error': 'Nenhum conteúdo fornecido', 'status': 'error'}), 400
        
        print(f"📧 Conteúdo processado ({len(email_text)} caracteres): {email_text[:100]}...")
        
        # Classificação
        category = classify_with_hf(email_text)
        
        # Geração de resposta
        response_suggestion = generate_response_with_hf(email_text, category)
        
        return jsonify({
            'category': category,
            'response': response_suggestion,
            'status': 'success',
            'content_length': len(email_text)
        })
    
    except Exception as e:
        print(f"Erro: {e}")
        return jsonify({'error': str(e), 'status': 'error'}), 500

def read_uploaded_file(file):
    """Lê o conteúdo de arquivos TXT ou PDF"""
    
    if isinstance(file, str):
        return file
    
    filename = file.filename.lower()
    
    if filename.endswith('.txt'):
        # Ler arquivo TXT
        file_content = file.read().decode('utf-8')
        return file_content
    
    elif filename.endswith('.pdf'):
        # Ler arquivo PDF
        file.seek(0)  # Reset file pointer
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        return text.strip()
    
    else:
        raise ValueError("Formato não suportado. Use .txt ou .pdf")

def classify_with_hf(email_text):
    """Classificação usando Hugging Face API"""
    
    # Fallback para textos muito curtos
    if len(email_text.split()) < 2:
        return classify_simple(email_text)
    
    try:
        payload = {"inputs": email_text}
        response = requests.post(HF_CLASSIFY_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("Resposta HF:", result)
            
            if isinstance(result, list) and len(result) > 0:
                sentiment_data = result[0]
                best_sentiment = max(sentiment_data, key=lambda x: x['score'])
                label = best_sentiment['label'].lower()
                
                if label in ['positive', 'pos', 'lab_1']:
                    return "Improdutivo"
                elif label in ['negative', 'neg', 'neutral', 'lab_0']:
                    return "Produtivo"
        
        return classify_simple(email_text)
        
    except requests.exceptions.Timeout:
        print("Timeout na API HF")
        return classify_simple(email_text)
    except Exception as e:
        print(f"Erro na classificação HF: {e}")
        return classify_simple(email_text)

def generate_response_with_hf(email_text, category):
    """Gera resposta usando Hugging Face"""
    
    try:
        if category == "Produtivo":
            prompt = f"Responda este email profissionalmente: '{email_text}'. Resposta:"
        else:
            prompt = f"Responda este email cordialmente: '{email_text}'. Resposta:"
        
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 100, "temperature": 0.7}
        }
        
        response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0]['generated_text']
                return generated_text.split("Resposta:")[-1].strip()
        
        return generate_fallback_response(category)
        
    except Exception as e:
        print(f"Erro na geração: {e}")
        return generate_fallback_response(category)

def classify_simple(email_text):
    """Classificação simples por palavras-chave"""
    productive_keywords = ['problema', 'ajuda', 'suporte', 'erro', 'urgente', 'ação', 'corrigir', 'quebrado']
    unproductive_keywords = ['obrigado', 'parabéns', 'agradeço', 'feliz', 'bom trabalho', 'excelente']
    
    email_lower = email_text.lower()
    productive_count = sum(1 for word in productive_keywords if word in email_lower)
    unproductive_count = sum(1 for word in unproductive_keywords if word in email_lower)
    
    return "Produtivo" if productive_count >= unproductive_count else "Improdutivo"

def generate_fallback_response(category):
    """Respostas de fallback"""
    if category == "Produtivo":
        return "Agradeço seu email. Analisarei sua solicitação e retornarei em breve com uma solução."
    else:
        return "Obrigado pelo seu email! Agradeço o contato e fico feliz em ajudar."

if __name__ == '__main__':
    print("Servidor iniciando...")
    print("Endpoints:")
    print("   - GET  http://localhost:5000/health")
    print("   - POST http://localhost:5000/classify")
    app.run(debug=True, host='0.0.0.0', port=5000)