# scripts/api_flask.py

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS # Importe a extensão CORS
import json
import os
import subprocess
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- Configuração de Caminhos ---
# Obtém o caminho absoluto para o diretório que contém este script (scripts/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Constrói o caminho para o arquivo relatory-reports.json (um nível acima de 'scripts/')
# Ex: Zap-Job/relatory-reports.json
JSON_FILE_PATH = os.path.join(SCRIPT_DIR, '../', 'reports/relatory-reports.json')

# Constrói o caminho para o script bash run_full_test.sh (um nível acima de 'scripts/')
# Ex: Zap-Job/run_full_test.sh
BASH_SCRIPT_PATH = os.path.join(SCRIPT_DIR, 'run_full_test.sh')

# --- Endpoints da API ---
@app.route('/start-configured-tests', methods=['POST'])
def start_configured_tests():
    """
    Endpoint para receber URL e E-mail, e disparar o script run_full_test.sh com esses parâmetros.
    """
    if not request.is_json:
        return jsonify({"error": "Requisição deve ser JSON"}), 400

    data = request.get_json()
    target_url = data.get('url')
    email = data.get('email')

    if not target_url or not email:
        return jsonify({"error": "URL e E-mail são obrigatórios."}), 400

    try:
        if not os.path.exists(BASH_SCRIPT_PATH):
            return jsonify({
                "error": "Script bash 'run_full_test.sh' não encontrado.",
                "expected_path": BASH_SCRIPT_PATH,
                "message": "Certifique-se de que 'run_full_test.sh' está no diretório raiz do projeto Zap-Job."
            }), 404

        os.chmod(BASH_SCRIPT_PATH, 0o755)

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Disparando testes para URL: {target_url}, Email: {email}")

        # Passa a URL e o E-mail como argumentos para o script bash
        # Eles estarão disponíveis no script bash como $1 e $2
        process = subprocess.run(
            [BASH_SCRIPT_PATH, target_url, email], # Lista de argumentos
            capture_output=True,
            text=True,
            check=True,
            cwd=os.path.join(SCRIPT_DIR, '..')
        )

        # Após a execução, tenta ler os novos dados do JSON
        if os.path.exists(JSON_FILE_PATH):
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            return jsonify({
                "message": f"Testes iniciados com sucesso para {target_url}. Relatórios atualizados!",
                "target_url": target_url,
                "email": email,
                "bash_stdout": process.stdout,
                "bash_stderr": process.stderr,
                "reports": updated_data
            }), 200
        else:
            return jsonify({
                "error": "Script executado, mas 'relatory-reports.json' não foi encontrado ou gerado.",
                "expected_json_path": JSON_FILE_PATH,
                "bash_stdout": process.stdout,
                "bash_stderr": process.stderr,
                "message": "Verifique a lógica do seu 'run_full_test.sh' para garantir que ele cria/atualiza o JSON."
            }), 500

    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": f"Erro ao executar script bash (código de saída {e.returncode}).",
            "message": "O script 'run_full_test.sh' encontrou um problema. Verifique a saída de erro.",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        return jsonify({"error": f"Erro interno ao disparar testes: {str(e)}"}), 500

@app.route('/')
def home():
    """
    Página inicial da API.
    """
    return "API Zap-Job está rodando. Acesse /reports para os dados, /dashboard para o dashboard, ou /run-tests para executar os testes."

@app.route('/reports', methods=['GET'])
def get_reports():
    """
    Endpoint para retornar os dados atuais do arquivo relatory-reports.json.
    """
    try:
        # Verifica se o arquivo JSON existe. Se não, informa que precisa rodar os testes.
        if not os.path.exists(JSON_FILE_PATH):
            return jsonify({
                "error": "relatory-reports.json não encontrado.",
                "message": "Por favor, execute o endpoint /run-tests (via POST) para gerar os relatórios."
            }), 404

        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Opcional: Adicionar ou garantir a data de execução atual no JSON.
        # Isso é útil caso o script bash não preencha essa informação ou para garantir que ela seja a mais recente.
        for report in data:
            if "data_execucao" not in report or not report["data_execucao"]:
                report["data_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(data)
    except json.JSONDecodeError:
        # Erro se o JSON estiver mal formatado
        return jsonify({
            "error": "Erro ao decodificar JSON de relatory-reports.json.",
            "message": "Verifique o formato do arquivo JSON. Pode ter sido gerado incorretamente pelo script bash."
        }), 500
    except Exception as e:
        # Captura outros erros inesperados
        return jsonify({"error": f"Erro interno ao ler relatórios: {str(e)}"}), 500

@app.route('/run-tests', methods=['POST'])
def run_tests():
    """
    Endpoint para disparar a execução do script run_full_test.sh.
    Após a execução, tenta ler e retornar os novos dados do relatory-reports.json.
    """
    try:
        # 1. Verifica se o script bash existe
        if not os.path.exists(BASH_SCRIPT_PATH):
            return jsonify({
                "error": "Script bash 'run_full_test.sh' não encontrado.",
                "expected_path": BASH_SCRIPT_PATH,
                "message": "Certifique-se de que 'run_full_test.sh' está no diretório raiz do projeto Zap-Job."
            }), 404
        
        # 2. Garante que o script bash é executável
        # Define permissões de leitura, escrita e execução para o proprietário,
        # e leitura e execução para grupo e outros (0o755).
        os.chmod(BASH_SCRIPT_PATH, 0o755)

        # 3. Executa o script bash
        # O 'cwd' (current working directory) é crucial aqui.
        # Ele define o diretório de trabalho para onde o comando subprocess será executado.
        # Ao definir para o diretório pai (Zap-Job/), o script bash pode usar caminhos relativos
        # como 'reports/...' ou 'relatory-reports.json' sem problemas.
        process = subprocess.run(
            BASH_SCRIPT_PATH,
            capture_output=True, # Captura a saída padrão e de erro
            text=True,           # Decodifica a saída como texto (UTF-8 por padrão)
            check=True,          # Se o script bash retornar um código de erro (!= 0), lança uma exceção CalledProcessError
            cwd=os.path.join(SCRIPT_DIR, '..') # Define o diretório de trabalho para Zap-Job/
        )

        # 4. Se a execução foi bem-sucedida, tenta ler os novos dados do JSON
        if os.path.exists(JSON_FILE_PATH):
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                updated_data = json.load(f)
            
            return jsonify({
                "message": "Testes executados com sucesso e relatórios atualizados!",
                "bash_stdout": process.stdout, # Saída padrão do script bash
                "bash_stderr": process.stderr, # Saída de erro do script bash
                "reports": updated_data
            }), 200
        else:
            # Caso o script tenha rodado, mas não gerou o JSON no local esperado
            return jsonify({
                "error": "Script executado, mas 'relatory-reports.json' não foi encontrado ou gerado no local esperado.",
                "expected_json_path": JSON_FILE_PATH,
                "bash_stdout": process.stdout,
                "bash_stderr": process.stderr,
                "message": "Verifique a lógica do seu 'run_full_test.sh' para garantir que ele cria/atualiza o JSON no diretório raiz do projeto."
            }), 500

    except subprocess.CalledProcessError as e:
        # Captura erros onde o script bash retornou um código de erro
        return jsonify({
            "error": f"Erro ao executar script bash (código de saída {e.returncode}).",
            "message": "O script 'run_full_test.sh' encontrou um problema.",
            "stdout": e.stdout,
            "stderr": e.stderr
        }), 500
    except Exception as e:
        # Captura quaisquer outros erros inesperados
        return jsonify({"error": f"Erro interno ao disparar testes: {str(e)}"}), 500

@app.route('/dashboard')
def serve_dashboard():
    """
    Endpoint para servir o arquivo dashboard.html.
    """
    # O dashboard.html está no diretório pai de 'scripts'
    return send_from_directory(os.path.join(SCRIPT_DIR, '..'), 'dashboard.html')

# --- Execução da Aplicação Flask ---

if __name__ == '__main__':
    # Bloco executado apenas se o script for rodado diretamente (python api_flask.py)

    # Verifica se o arquivo JSON existe ao iniciar a API.
    # Se não existir, cria um arquivo JSON vazio (uma lista vazia) para evitar erros
    # de FileNotFoundError quando a API tentar lê-lo pela primeira vez.
    if not os.path.exists(JSON_FILE_PATH):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {JSON_FILE_PATH} não encontrado. Criando um arquivo JSON vazio.")
        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2) # Salva uma lista vazia com indentação para legibilidade

    # Inicia o servidor Flask
    # debug=True: Permite recarregamento automático e fornece informações de depuração.
    # host='0.0.0.0': Torna o servidor acessível de outras máquinas na rede (útil para testes).
    # port=5000: Define a porta em que a API será executada.
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando a API Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)