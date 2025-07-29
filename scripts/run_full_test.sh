#!/bin/bash

#ZAP_TARGET_URL="https://hd-support-bne.vercel.app" 
#ZAP_TARGET_URL="https://testing-hdsupport.bne.com.br"
#ZAP_TARGET_URL="https://testing-campcode.bne.com.br" 
#RECIPIENT_EMAIL="walterbrito@bne.com.br"
echo "$1" 
echo "$2"
ZAP_TARGET_URL="$1"
RECIPIENT_EMAIL="$2"

if [ -z "$ZAP_TARGET_URL" ]; then
    echo "ERRO: URL do alvo não fornecida." >&2
    echo "FIM_DO_SCAN_FALHA" # Sinaliza falha
    exit 1
fi

# Se o email não for fornecido, usa um email padrão ou não envia
if [ -z "$RECIPIENT_EMAIL" ]; then
    echo "AVISO: E-mail para notificação não fornecido. O relatório pode não ser enviado por e-mail."
    # Você pode definir um email padrão aqui se quiser
    RECIPIENT_EMAIL="walterbrito@bne.com.br"
fi

# Extrai o nome da aplicação da URL
# 1. Remove o protocolo (https://, http://)
url_no_protocol="${ZAP_TARGET_URL#*//}"
# 2. Remove a barra final se houver
url_no_slash="${url_no_protocol%/}"
# 3. Pega a parte antes do primeiro ponto (o subdomínio/nome da aplicação)
APP_NAME=$(echo "${url_no_slash}" | cut -d'.' -f1)

ZAP_REPORT_JSON_FILENAME="relatory_${APP_NAME}.json"
ZAP_HTML_TEMPLATE_PATH="layout.html"
ZAP_FINAL_HTML_REPORT_FILENAME="relatory_${APP_NAME}.html"

LOCAL_REPORTS_DIR="/app/reports"

ZAP_DOCKER_IMAGE="ghcr.io/zaproxy/zaproxy:latest"
ZAP_API="http://owasp-zap:8080"

SENDER_EMAIL="walter.222brito@gmail.com"
SENDER_PASSWORD="ucys jzqn auyk geem"


echo "Extraindo dados do relatório JSON para o corpo do e-mail..."

# Verifica se o jq está instalado
# A função check_command precisa ser definida antes de ser chamada.
function check_command {
    command -v "$1" >/dev/null 2>&1 || { echo >&2 "Erro: $1 não está instalado. Abortando."; exit 1; }
}

# Define a função run_command
function run_command {
    echo "Executando: $@"
    "$@"
    if [ $? -ne 0 ]; then
        echo "Erro ao executar: $@" >&2
        exit 1
    fi
}


# Caminho completo para o relatório JSON
FULL_JSON_PATH="${LOCAL_REPORTS_DIR}/${ZAP_REPORT_JSON_FILENAME}"

# --- Validações de Pré-requisitos ---
echo "Verificando pré-requisitos..."
check_command python3
check_command curl
check_command jq # Adiciona a verificação do jq aqui, como é usado mais abaixo

# --- PASSO 0: Preparar diretório de relatórios local ---

echo "Limpando relatórios antigos em ${LOCAL_REPORTS_DIR}..."
rm -f "${LOCAL_REPORTS_DIR}/${ZAP_REPORT_JSON_FILENAME}"
rm -f "${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"


# --- Passo 1
# --- Validações de Pré-requisitos ---
echo "Verificando pré-requisitos..."
check_command python3
check_command curl
check_command jq

# --- PASSO 1: Executar o ZAP Baseline Scan via Docker Compose ---
echo "Aguardando o ZAP inicializar completamente..."
sleep 30

echo "Executando Spider para adicionar URL à árvore..."
SPIDER_ID=$(curl -s "${ZAP_API}/JSON/spider/action/scan/?url=${ZAP_TARGET_URL}" | jq -r '.scan')
if [ -z "$SPIDER_ID" ] || [ "$SPIDER_ID" == "null" ]; then
  echo "Erro ao iniciar o spider."
  exit 1
fi

# Aguardar spider finalizar
while true; do
  STATUS=$(curl -s "${ZAP_API}/JSON/spider/view/status/?scanId=${SPIDER_ID}" | jq -r '.status')
  echo "Spider status: ${STATUS}%"
  [ "$STATUS" -eq 100 ] && break
  sleep 2
done
echo "Spider concluído. Iniciando scan ativo..."

echo "Iniciando scan na URL: ${ZAP_TARGET_URL}"

SCAN_ID=$(curl -s "${ZAP_API}/JSON/ascan/action/scan/?url=${ZAP_TARGET_URL}" | jq -r '.scan')
if [ -z "$SCAN_ID" ] || [ "$SCAN_ID" == "null" ]; then
  echo "Erro ao iniciar o scan ativo no ZAP"
  exit 1
fi

show_progress() {
    local status="$1"
    echo -ne "\rProgresso: $status%"
    sleep 0.1
}

echo "Scan iniciado com ID: $SCAN_ID"
LAST_STATUS=""
while true; do
    STATUS=$(curl -s "${ZAP_API}/JSON/ascan/view/status/?scanId=${SCAN_ID}" | jq -r '.status')
    if [[ "$STATUS" != "$LAST_STATUS" ]]; then
        show_progress $STATUS
        LAST_STATUS=$STATUS
    fi
    [[ "$STATUS" -eq 100 ]] && break
    sleep 5
done

echo -e "\n\nScan completado!"
curl -s "${ZAP_API}/OTHER/core/other/jsonreport/" -o "${FULL_JSON_PATH}"


# --- PASSO 2: Gerar o Relatório HTML Final ---
echo "Gerando relatório HTML a partir do JSON..."
run_command python3 generate_html_report.py \
  "${LOCAL_REPORTS_DIR}/${ZAP_REPORT_JSON_FILENAME}" \
  "${ZAP_HTML_TEMPLATE_PATH}" \
  "${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"

echo "Relatório HTML final gerado em: ${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"
ls -l "${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"

# --- PASSO 3: Enviar o Relatório por E-mail (com curl para SMTP) ---
echo "Enviando relatório por e-mail..."
HIGH_ALERTS=$(jq '.site?.[0]?.alerts | map(select(.riskcode == "3")) | length' "${FULL_JSON_PATH}")
MEDIUM_ALERTS=$(jq '.site?.[0]?.alerts | map(select(.riskcode == "2")) | length' "${FULL_JSON_PATH}")
LOW_ALERTS=$(jq '.site?.[0]?.alerts | map(select(.riskcode == "1")) | length' "${FULL_JSON_PATH}")
INFO_ALERTS=$(jq '.site?.[0]?.alerts | map(select(.riskcode == "0")) | length' "${FULL_JSON_PATH}")
TOTAL_ALERTS=$(jq '.site?.[0]?.alerts | length' "${FULL_JSON_PATH}")

# Verifica se a extração foi bem-sucedida (jq retorna null ou 0 se não encontrar)
if [ -z "$HIGH_ALERTS" ]; then HIGH_ALERTS=0; fi
if [ -z "$MEDIUM_ALERTS" ]; then MEDIUM_ALERTS=0; fi
if [ -z "$LOW_ALERTS" ]; then LOW_ALERTS=0; fi
if [ -z "$INFO_ALERTS" ]; then INFO_ALERTS=0; fi
if [ -z "$TOTAL_ALERTS" ]; then TOTAL_ALERTS=0; fi

EMAIL_SUBJECT="[ZAP Scan Docker] Relatório de Segurança ZAP para ${ZAP_TARGET_URL}"

EMAIL_BODY_HTML="<html><body><div style='font-family: Arial, sans-serif; background-color: #f0f0f0; padding: 20px; border-radius: 8px;'>\
<h2 style='color: #0056b3;'>Relatório de Segurança ZAP - Scan Concluído</h2>\
<p>Prezado(a) time,</p>\
<p>Um scan de segurança do OWASP ZAP foi concluído para a URL: <strong>${ZAP_TARGET_URL}</strong>.</p>\
<p>Segue um resumo dos resultados:</p>\
<ul>\
    <li>Total de Alertas: <strong>${TOTAL_ALERTS}</strong></li>\
    <li>Alertas de Alto Risco: <strong style='color: #ef233c;'>${HIGH_ALERTS}</strong></li>\
    <li>Alertas de Médio Risco: <strong style='color: #f4a261;'>${MEDIUM_ALERTS}</strong></li>\
    <li>Alertas de Baixo Risco: <strong style='color: #4cc9f0;'>${LOW_ALERTS}</strong></li>\
    <li>Alertas Informativos: <strong style='color: #6c757d;'>${INFO_ALERTS}</strong></li>\
</ul>\
<p>O relatório completo em formato HTML e JSON está anexado a este e-mail para análise detalhada.</p>\
<p>Atenciosamente,<br>Seu Script de Teste de Segurança</p>\
<div style='font-size: 0.8em; color: #555; margin-top: 20px;'>Este é um e-mail gerado automaticamente.</div>\
</div></body></html>"

REPORTS_SUMMARY_FILE="relatory-reports.json"
# Preparar corpo do e-mail com anexo MIME
BOUNDARY="----=_Part_$(date +%s%N)"

(
    echo "From: ${SENDER_EMAIL}"
    echo "To: ${RECIPIENT_EMAIL}"
    echo "Subject: ${EMAIL_SUBJECT}"
    echo "MIME-Version: 1.0"
    echo "Content-Type: multipart/mixed; boundary=\"${BOUNDARY}\""
    echo ""
    echo "--${BOUNDARY}"
    echo "Content-Type: text/html; charset=UTF-8"
    echo "Content-Transfer-Encoding: quoted-printable"
    echo ""
    echo "${EMAIL_BODY_HTML}"
    echo ""
    echo "--${BOUNDARY}"
    echo "Content-Type: application/json; name=\"${ZAP_REPORT_JSON_FILENAME}\""
    echo "Content-Transfer-Encoding: base64"
    echo "Content-Disposition: attachment; filename=\"${ZAP_REPORT_JSON_FILENAME}\""
    echo ""
    base64 "${LOCAL_REPORTS_DIR}/${ZAP_REPORT_JSON_FILENAME}"
    echo ""
    echo "--${BOUNDARY}"
    echo "Content-Type: text/html; name=\"${ZAP_FINAL_HTML_REPORT_FILENAME}\""
    echo "Content-Transfer-Encoding: base64"
    echo "Content-Disposition: attachment; filename=\"${ZAP_FINAL_HTML_REPORT_FILENAME}\""
    echo ""
    base64 "${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"
    echo ""
    echo "--${BOUNDARY}--"
) | curl --url "smtp://smtp.gmail.com:587" \
          --ssl-reqd \
          --mail-from "${SENDER_EMAIL}" \
          --mail-rcpt "${RECIPIENT_EMAIL}" \
          --user "${SENDER_EMAIL}:${SENDER_PASSWORD}" \
          --upload-file "-"

if [ $? -ne 0 ]; then
    echo "Erro ao enviar o e-mail via cURL. Verifique as credenciais e configurações SMTP." >&2
    exit 1
fi
echo "E-mail enviado com sucesso!"

REPORTS_SUMMARY_FILE="${LOCAL_REPORTS_DIR}/relatory-reports.json"
DATA_EXECUCAO=$(date "+%Y-%m-%d %H:%M:%S")
HTML_FILENAME_PATH="reports/${ZAP_FINAL_HTML_REPORT_FILENAME}"


# Cria o novo objeto JSON com as informações do relatório
NEW_ENTRY=$(jq -n \
  --arg url "$ZAP_TARGET_URL" \
  --arg date "$DATA_EXECUCAO" \
  --arg high "$HIGH_ALERTS" \
  --arg medium "$MEDIUM_ALERTS" \
  --arg low "$LOW_ALERTS" \
  --arg info "$INFO_ALERTS" \
  --arg total "$TOTAL_ALERTS" \
  --arg summary "$SUMMARY_TEXT" \
  --arg html_path "$HTML_FILENAME_PATH" \
  '{
    "url_executado": $url,
    "data_execucao": $date,
    "quantidade_riscos": {
      "alto": ($high | tonumber),
      "medio": ($medium | tonumber),
      "baixo": ($low | tonumber),
      "informativo": ($info | tonumber),
      "total": ($total | tonumber)
    },
    "resumo": $summary,
    "caminho_html": $html_path
  }')

echo "Novo conteúdo a adicionar:"
echo "$NEW_ENTRY" | jq .

# Se o arquivo já existir, lê o array atual e adiciona a nova entrada.
# Se não existir, cria um novo array com a nova entrada.
if [ -s "$REPORTS_SUMMARY_FILE" ]; then
    jq --arg url "$ZAP_TARGET_URL" --argjson new "$NEW_ENTRY" '
        map(if .url_executado == $url then $new else . end)
        + (if map(.url_executado == $url) | any then [] else [$new] end)
    ' "$REPORTS_SUMMARY_FILE" > "${REPORTS_SUMMARY_FILE}.tmp" \
    && mv "${REPORTS_SUMMARY_FILE}.tmp" "$REPORTS_SUMMARY_FILE"
else
    echo "[$NEW_ENTRY]" > "$REPORTS_SUMMARY_FILE"
fi


if [ $? -ne 0 ]; then
    echo "Erro ao salvar o arquivo de resumo '${REPORTS_SUMMARY_FILE}'." >&2
    exit 1
fi
echo "Arquivo de resumo '${REPORTS_SUMMARY_FILE}' salvo com sucesso."

# --- PASSO 4: Limpeza dos Recursos ---
echo "Limpando arquivos gerados localmente em ${LOCAL_REPORTS_DIR}..."
rm -f "${LOCAL_REPORTS_DIR}/${ZAP_REPORT_JSON_FILENAME}"
#rm -f "${LOCAL_REPORTS_DIR}/${ZAP_FINAL_HTML_REPORT_FILENAME}"
echo "Limpeza concluída. Processo finalizado com sucesso."