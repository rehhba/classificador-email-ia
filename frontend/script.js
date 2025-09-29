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

async function classifyEmail() {
    let emailText = '';
    
    try {
        const button = document.querySelector('button');
        const originalText = button.textContent;
        button.textContent = 'Analisando...';
        button.disabled = true;
        
        if (currentOption === 'text') {

            emailText = document.getElementById('emailText').value.trim();
            if (!emailText) {
                alert('Por favor, insira o texto do email');
                button.textContent = originalText;
                button.disabled = false;
                return;
            }
        } else {
            const fileInput = document.getElementById('fileInput');
            if (!fileInput.files.length) {
                alert('Por favor, selecione um arquivo');
                button.textContent = originalText;
                button.disabled = false;
                return;
            }
            
            const file = fileInput.files[0];
            if (!file.name.match(/\.(txt|pdf)$/i)) {
                alert('Por favor, selecione um arquivo .txt ou .pdf');
                button.textContent = originalText;
                button.disabled = false;
                return;
            }
            
            emailText = `Arquivo: ${file.name}`;
        }
        
        const response = await fetch('https://classificador-email-ia.onrender.com/classify', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ email: emailText })
        });
        
        console.log('Status da resposta:', response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erro ${response.status}: ${errorText}`);
        }
        
        const result = await response.json();
        console.log('Resultado:', result);
        
        if (result.status === 'success') {
            document.getElementById('categoryResult').textContent = result.category;
            document.getElementById('responseSuggestion').textContent = result.response;
            document.getElementById('result').classList.remove('hidden');
            
            document.getElementById('result').scrollIntoView({ behavior: 'smooth' });
        } else {
            throw new Error(result.error || 'Erro desconhecido do servidor');
        }
        
    } catch (error) {
        console.error('Erro detalhado:', error);
        
        if (error.message.includes('Failed to fetch')) {
            alert('Não foi possível conectar ao servidor!\n\nVerifique se:\n• O servidor backend está rodando\n• A URL está correta');
        } else if (error.message.includes('NetworkError')) {
            alert('Erro de rede! Verifique sua conexão.');
        } else {
            alert('Erro: ' + error.message);
        }
    } finally {
        const button = document.querySelector('button');
        button.textContent = 'Classificar Email';
        button.disabled = false;
    }
}

function copyResponse() {
    const responseText = document.getElementById('responseSuggestion').textContent;
    navigator.clipboard.writeText(responseText).then(() => {
        alert('Resposta copiada para a área de transferência!');
    }).catch(err => {
        alert('Erro ao copiar: ' + err);
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