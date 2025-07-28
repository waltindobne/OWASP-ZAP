# scripts/api_flask.py

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import json
import os
import subprocess
from datetime import datetime

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["http://zap-web-nginx", "http://localhost", "http://localhost:80", "http://localhost:5000"]}})

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

JSON_FILE_PATH = os.path.join(SCRIPT_DIR, 'reports', 'relatory-reports.json')

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
        # Verifica se o script bash existe no caminho esperado
        if not os.path.exists(BASH_SCRIPT_PATH):
            return jsonify({
                "error": "Script bash 'run_full_test.sh' não encontrado.",
                "expected_path": BASH_SCRIPT_PATH,
                "message": "Verifique se 'run_full_test.sh' está no diretório raiz do projeto Zap-Job e montado corretamente em /app/run_full_test.sh no contêiner."
            }), 404

        # REMOVIDO: os.chmod(BASH_SCRIPT_PATH, 0o755)
        # A permissão de execução deve ser definida no Dockerfile (RUN chmod +x)
        # para evitar problemas de permissão em tempo de execução e redundância.

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Disparando testes para URL: {target_url}, Email: {email}")

        # Passa a URL e o E-mail como argumentos para o script bash
        # Eles estarão disponíveis no script bash como $1 e $2
        process = subprocess.run(
            [BASH_SCRIPT_PATH, target_url, email], # Lista de argumentos
            capture_output=True,
            text=True,
            check=True,
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
                "message": "Verifique a lógica do seu 'run_full_test.sh' para garantir que ele cria/atualiza o JSON no diretório esperado."
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
    return "API Zap-Job está rodando. Acesse /reports para os dados, ou /start-configured-tests (POST) para executar os testes."

@app.route('/reports', methods=['GET'])
def get_reports():
    """
    Endpoint para retornar os dados atuais do arquivo relatory-reports.json.
    """
    try:
        if not os.path.exists(JSON_FILE_PATH):
            return jsonify({
                "error": "relatory-reports.json não encontrado.",
                "message": "Por favor, execute o endpoint /start-configured-tests (via POST) para gerar os relatórios."
            }), 404

        with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for report in data:
            if "data_execucao" not in report or not report["data_execucao"]:
                report["data_execucao"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return jsonify(data)
    except json.JSONDecodeError:
        return jsonify({
            "error": "Erro ao decodificar JSON de relatory-reports.json.",
            "message": "Verifique o formato do arquivo JSON. Pode ter sido gerado incorretamente pelo script bash."
        }), 500
    except Exception as e:
        return jsonify({"error": f"Erro interno ao ler relatórios: {str(e)}"}), 500

if __name__ == '__main__':
    if not os.path.exists(JSON_FILE_PATH):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {JSON_FILE_PATH} não encontrado. Criando um arquivo JSON vazio.")
        # Garante que o diretório 'reports' exista antes de tentar criar o arquivo JSON
        os.makedirs(os.path.dirname(JSON_FILE_PATH), exist_ok=True)
        with open(JSON_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Iniciando a API Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000)