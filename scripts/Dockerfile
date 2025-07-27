# scripts/Dockerfile
FROM python:3.9-slim-buster

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Instala as dependências Flask e Flask-Cors diretamente
# Se você tiver outras dependências além dessas, adicione-as aqui.
RUN pip install --no-cache-dir Flask Flask-Cors

# Copia os arquivos da API e outros scripts
COPY api_flask.py .
COPY generate_html_report.py .
COPY layout.html .
COPY run_full_test.sh .

# Expor a porta que o Flask vai usar
EXPOSE 5000

# Comando para rodar a aplicação Flask
CMD ["flask", "run", "--host=0.0.0.0", "--port=5000"]