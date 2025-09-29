let currentOption = 'text';

function showOption(option) {
    currentOption = option;
    
    document.querySelectorAll('.option').forEach(opt => {
        opt.classList.remove('active');
    });
    event.target.classList.add('active');
    
    document.getElementById('text-option').classList.toggle('hidden', option !== 'text');
    document.getElementById('file-option').classList.toggle('hidden', option !== 'file');
}

document.getElementById('fileInput').addEventListener('change', function(e) {
    const fileName = document.getElementById('fileName');
    if (this.files.length > 0) {
        fileName.textContent = 'Arquivo selecionado: ' + this.files[0].name;
    } else {
        fileName.textContent = '';
    }
});

async function analyzeEmail() {
    const btn = document.querySelector('.analyze-btn');
    const btnText = document.getElementById('btn-text');
    const resultCard = document.getElementById('result-card');

    try {
        btn.disabled = true;
        btnText.innerHTML = '<div class="loading"></div>Analisando...';

        const activeTab = document.querySelector('.tab-content.active').id;
        let emailText = '';

        if (activeTab === 'text-tab') {
            emailText = document.getElementById('emailText').value.trim();
            if (!emailText) {
                alert('Por favor, insira o texto do email');
                return;
            }
        } else {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) {
                alert('Por favor, selecione um arquivo');
                return;
            }
            const file = fileInput.files[0];
            if (!file.name.match(/\.(txt|pdf|doc|docx)$/i)) {
                alert('Por favor, selecione um arquivo .txt, .pdf, .doc ou .docx');
                return;
            }
            
            emailText = `Arquivo: ${file.name}`;
        }

        const response = await fetch('https://classificador-email-ia.onrender.com/classify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email: emailText })
        });

        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (result.status === 'success') {
            document.getElementById('categoryResult').textContent = result.category;
            document.getElementById('responseSuggestion').textContent = result.response;
            resultCard.classList.remove('hidden');
        } else {
            throw new Error(result.error || 'Erro desconhecido no servidor');
        }

        resultCard.scrollIntoView({ behavior: 'smooth' });

    } catch (error) {
        console.error('Erro completo:', error);
        alert('Erro ao conectar com a IA: ' + error.message);
    } finally {
        btn.disabled = false;
        btnText.textContent = 'Analisar Email';
    }
}

function copyResponse() {
    const responseText = document.getElementById('responseSuggestion').textContent;
    navigator.clipboard.writeText(responseText).then(() => {
        const btn = document.querySelector('.copy-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copiado!';
        btn.style.background = '#2ecc71';
        
        setTimeout(() => {
            btn.textContent = originalText;
            btn.style.background = '';
        }, 2000);
    }).catch(err => {
        console.error('Erro ao copiar:', err);
        const textArea = document.createElement('textarea');
        textArea.value = responseText;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        
        const btn = document.querySelector('.copy-btn');
        const originalText = btn.textContent;
        btn.textContent = '✓ Copiado!';
        setTimeout(() => {
            btn.textContent = originalText;
        }, 2000);
    });
}

async function testConnection() {
    try {
        const response = await fetch('https://classificador-email-ia.onrender.com/classify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: 'test' })
        });
        if (response.ok) {
            const data = await response.json();
            console.log('Backend online:', data);
            return true;
        } else {
            console.error('Backend com erro:', response.status);
            return false;
        }
    } catch (error) {
        console.error('Backend offline:', error);
        return false;
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Página carregada. Iniciando testes...');
    
    showOption('text');
    
    testConnection().then(online => {
        if (online) {
            console.log('Sistema pronto para uso!');
        } else {
            console.warn('Backend offline, algumas funcionalidades podem não funcionar');
        }
    });
    
    document.getElementById('emailText').addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            classifyEmail();
        }
    });
});