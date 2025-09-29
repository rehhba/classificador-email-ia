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
        
        # USAR APENAS CLASSIFICAÇÃO SIMPLES - MAIS EFETIVA
        category = classify_simple_improved(email_text)
        
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

def classify_simple_improved(email_text):
    """
    SISTEMA DE CLASSIFICAÇÃO MELHORADO
    Foca em palavras-chave específicas para importância de emails
    """
    email_lower = email_text.lower()
    
    # PALAVRAS-CHAVE FORTES para IMPORTANTE (com pesos)
    important_keywords = {
        # Urgência e problemas críticos
        'urgente': 3, 'emergência': 3, 'crítico': 3, 'crítica': 3, 
        'problema grave': 3, 'não funciona': 3, 'sistema down': 3,
        'fora do ar': 3, 'erro crítico': 3, 'parado': 2, 'travado': 2,
        'quebrado': 2, 'defeito': 2, 'falha': 2, 'bug': 2,
        
        # Impacto financeiro
        'perda de vendas': 3, 'cliente reclamando': 2, 'chargeback': 3,
        'prejuízo': 3, 'perda financeira': 3, 'pagamento': 2,
        'fatura': 2, 'boleto': 2, 'vencimento': 2, 'atrasado': 2,
        
        # Problemas operacionais
        'suporte': 2, 'ajuda técnica': 2, 'conserto': 2, 'reparo': 2,
        'contrato': 2, 'legal': 2, 'jurídico': 2, 'processo': 2,
        
        # Reclamações sérias
        'reclamação': 2, 'insatisfeito': 2, 'devolução': 2, 'cancelar': 2,
        'revogar': 2, 'rescisão': 2,
        
        # Segurança
        'hackeado': 3, 'segurança': 2, 'senha': 2, 'conta': 2,
        'acesso': 2, 'bloqueado': 2,
        
        # Prazos
        'prazo curto': 2, 'hoje': 2, 'amanhã': 2, 'data limite': 2,
        'imediatamente': 2, 'agora': 2
    }
    
    # PALAVRAS-CHAVE para NÃO IMPORTANTE
    unimportant_keywords = {
        # Agradecimentos
        'obrigado': 2, 'obrigada': 2, 'grato': 2, 'gratidão': 2,
        'agradeço': 2, 'valeu': 2, 'parabéns': 2, 'felicitações': 2,
        
        # Marketing/Newsletter
        'newsletter': 2, 'promoção': 1, 'oferta': 1, 'desconto': 1,
        'marketing': 1, 'divulgação': 1, 'novidade': 1, 'lançamento': 1,
        
        # Social
        'convite': 1, 'evento': 1, 'festa': 1, 'encontro': 1,
        'social': 1, 'comemoração': 1,
        
        # Informações gerais
        'curiosidade': 1, 'interessante': 1, 'compartilhar': 1,
        'informação': 1, 'consulta': 1,
        
        # Follow-up não urgente
        'lembrete suave': 1, 'quando possível': 1, 'sem pressa': 1,
        'sem urgência': 1
    }
    
    # Calcular pontuação
    important_score = 0
    unimportant_score = 0
    
    # Verificar palavras importantes
    for keyword, weight in important_keywords.items():
        if keyword in email_lower:
            important_score += weight
    
    # Verificar palavras não importantes
    for keyword, weight in unimportant_keywords.items():
        if keyword in email_lower:
            unimportant_score += weight
    
    # Classificar baseado na pontuação
    if important_score > unimportant_score:
        return "Importante"
    elif important_score == 0 and unimportant_score == 0:
        # Se não encontrou palavras-chave, classificar como importante por padrão
        return "Importante"
    else:
        return "Não Importante"

def generate_response_with_hf(email_text, category):
    try:
        if category == "Importante":
            prompt = f"Como assistente profissional, responda este email importante de forma direta e solucionadora: '{email_text}'. Ofereça ajuda imediata e prazos curtos. Resposta profissional:"
        else:
            prompt = f"Como assistente profissional, responda este email de rotina de forma cordial e breve: '{email_text}'. Agradeça e ofereça ajuda futura se necessário. Resposta cordial:"
        
        payload = {
            "inputs": prompt,
            "parameters": {"max_length": 150, "temperature": 0.7, "do_sample": True}
        }
        
        response = requests.post(HF_CHAT_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                generated_text = result[0]['generated_text']
                # Extrair apenas a parte da resposta
                if "Resposta:" in generated_text:
                    return generated_text.split("Resposta:")[-1].strip()
                return generated_text.strip()
        
        return generate_fallback_response(category)
        
    except Exception:
        return generate_fallback_response(category)

def generate_fallback_response(category):
    if category == "Importante":
        return "Prezado(a),\n\nIdentificamos que seu requerimento é de alta prioridade. Nossa equipe técnica foi acionada e entrará em contato dentro de 2 horas úteis para resolver esta questão.\n\nAtenciosamente,\nEquipe de Suporte Técnico"
    else:
        return "Prezado(a),\n\nAgradecemos seu contato! Sua mensagem foi recebida e será respondida em até 48 horas úteis, conforme nossa fila de atendimento.\n\nAtenciosamente,\nEquipe de Atendimento"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)