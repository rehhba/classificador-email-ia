from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import PyPDF2
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)  

HF_API_KEY = os.environ.get('HUGGINGFACE_TOKEN')
HF_CLASSIFY_URL = "https://api-inference.huggingface.co/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
HF_CHAT_URL = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"

headers = {"Authorization": f"Bearer {HF_API_KEY}"} if HF_API_KEY else {}

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
        
        if 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                email_text = read_uploaded_file(file)
        
        elif request.is_json and request.json and 'email' in request.json:
            email_text = request.json.get('email', '')
        
        elif request.form and 'email' in request.form:
            email_text = request.form.get('email', '')
        
        if not email_text or not email_text.strip():
            return jsonify({'error': 'Nenhum conteúdo fornecido', 'status': 'error'}), 400
        
        category = classify_with_hf(email_text)
        
        response_suggestion = generate_response_with_hf(email_text, category)
        
        return jsonify({
            'category': category,
            'response': response_suggestion,
            'status': 'success',
            'content_length': len(email_text)
        })
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

def read_uploaded_file(file):
    if isinstance(file, str):
        return file
    
    filename = file.filename.lower()
    
    if filename.endswith('.txt'):
        file_content = file.read().decode('utf-8')
        return file_content
    
    elif filename.endswith('.pdf'):
        file.seek(0)
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
    if len(email_text.split()) < 2:
        return classify_simple(email_text)
    
    try:
        payload = {"inputs": email_text}
        response = requests.post(HF_CLASSIFY_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                sentiment_data = result[0]
                best_sentiment = max(sentiment_data, key=lambda x: x['score'])
                label = best_sentiment['label'].lower()
                
                if label in ['negative', 'neg', 'lab_0']:
                    return "Importante"
                elif label in ['positive', 'pos', 'neutral', 'lab_1']:
                    return "Não Importante"
        
        return classify_simple(email_text)
        
    except Exception:
        return classify_simple(email_text)

def generate_response_with_hf(email_text, category):
    try:
        if category == "Importante":
            prompt = f"Responda este email importante de forma profissional e direta: '{email_text}'. Resposta:"
        else:
            prompt = f"Responda este email não importante de forma breve e cordial: '{email_text}'. Resposta:"
        
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
        
    except Exception:
        return generate_fallback_response(category)

def classify_simple(email_text):
    important_keywords = ['problema', 'erro', 'urgente', 'quebrado', 'suporte', 'ajuda', 'contrato', 'pagamento', 'bug', 'reclamação']
    unimportant_keywords = ['obrigado', 'parabéns', 'agradeço', 'feliz', 'bom trabalho', 'excelente', 'demo', 'promoção', 'newsletter']
    
    email_lower = email_text.lower()
    important_count = sum(1 for word in important_keywords if word in email_lower)
    unimportant_count = sum(1 for word in unimportant_keywords if word in email_lower)
    
    return "Importante" if important_count > unimportant_count else "Não Importante"

def generate_fallback_response(category):
    if category == "Importante":
        return "Prezado(a) cliente,\n\nAgradecemos seu contato. Esta é uma questão importante e nossa equipe dará prioridade ao seu atendimento. Retornaremos em até 24 horas.\n\nAtenciosamente,\nEquipe de Suporte"
    else:
        return "Prezado(a) cliente,\n\nObrigado pelo seu email! Agradecemos o contato.\n\nAtenciosamente,\nEquipe de Atendimento"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)