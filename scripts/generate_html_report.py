# scripts/generate_html_report.py
import json
import os
import sys
from datetime import datetime

def calcular_stats(alertas):
    stats = {"high": 0, "medium": 0, "low": 0, "info": 0, "total": len(alertas)}
    for alerta in alertas:
        # Garante que riskcode é uma string para o lookup no risk_map
        risk = str(alerta.get("riskcode", "0"))
        if risk == "3":
            stats["high"] += 1
        elif risk == "2":
            stats["medium"] += 1
        elif risk == "1":
            stats["low"] += 1
        else: # riskcode "0" ou qualquer outro não mapeado
            stats["info"] += 1
    return stats

def render_html_report(json_file_path, html_template_path, output_html_path):
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            zap_report_data = json.load(f)

        with open(html_template_path, 'r', encoding='utf-8') as f:
            html_template_content = f.read()

        site_data = zap_report_data.get("site", [{}])[0]
        alertas = site_data.get("alerts", [])
        
        # Calcula as estatísticas
        stats = calcular_stats(alertas)
        
        # Obtém a data do scan do próprio JSON do ZAP, se disponível, ou usa a data atual
        scan_date_from_report = zap_report_data.get('@generated')
        if scan_date_from_report:
            try:
                # Exemplo de formato ZAP: 'Mon, 21 Jul 2025 15:43:23 -0300'
                dt_obj = datetime.strptime(scan_date_from_report, '%a, %d %b %Y %H:%M:%S %z')
                scan_date_formatted = dt_obj.strftime('%d/%m/%Y %H:%M:%S') # Formato DD/MM/YYYY HH:MM:SS
            except ValueError:
                scan_date_formatted = scan_date_from_report # Fallback se o formato for diferente
        else:
            scan_date_formatted = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        # --- Geração dos blocos HTML ---

        # 1. HTML para os cartões de estatísticas (summary-cards-container)
        summary_cards_html = f"""
            <div class="stat-card">
                <h3>Total de Alertas</h3>
                <p>{stats['total']}</p>
            </div>
            <div class="stat-card">
                <h3>Alto Risco</h3>
                <p class="high">{stats['high']}</p>
            </div>
            <div class="stat-card">
                <h3>Médio Risco</h3>
                <p class="medium">{stats['medium']}</p>
            </div>
            <div class="stat-card">
                <h3>Baixo Risco</h3>
                <p class="low">{stats['low']}</p>
            </div>
            <div class="stat-card">
                <h3>Informativo</h3>
                <p class="info">{stats['info']}</p>
            </div>
        """

        # 2. HTML para a lista de alertas (alert-container)
        alerts_list_html = ''
        if not alertas:
            alerts_list_html = """
                <div class="empty-state" id="empty-message-no-alerts">
                    <img src="https://cdn-icons-png.flaticon.com/512/4076/4076478.png" alt="Nenhum alerta">
                    <h3>Nenhuma vulnerabilidade encontrada</h3>
                    <p>O scan não identificou problemas de segurança.</p>
                </div>
            """
        else:
            # Mapeamento de riscos para classes CSS e rótulos para uso no HTML
            risk_map_html = {
                '3': {'class': 'high', 'label': 'Alto', 'filter': 'high'},
                '2': {'class': 'medium', 'label': 'Médio', 'filter': 'medium'},
                '1': {'class': 'low', 'label': 'Baixo', 'filter': 'low'},
                '0': {'class': 'info', 'label': 'Informativo', 'filter': 'info'},
                'High': {'class': 'high', 'label': 'Alto', 'filter': 'high'},
                'Medium': {'class': 'medium', 'label': 'Médio', 'filter': 'medium'},
                'Low': {'class': 'low', 'label': 'Baixo', 'filter': 'low'},
                'Informational': {'class': 'info', 'label': 'Informativo', 'filter': 'info'}
            }
            for alerta in alertas:
                # Tenta usar riskcode numérico primeiro, depois o texto de riskdesc
                risk_level_key = str(alerta.get('riskcode', '0'))
                risk_info = risk_map_html.get(risk_level_key)
                if not risk_info:
                    risk_info = risk_map_html.get(alerta.get('riskdesc', '').split(' ')[0], {'class': 'info', 'label': 'Desconhecido', 'filter': 'info'})

                instances_html = ''
                for instance in alerta.get('instances', []):
                    # Garante que a URI é um link válido
                    uri = instance.get('uri', '#')
                    method = instance.get('method', 'GET')
                    instances_html += f"""
                        <li><strong>URI:</strong> <a href="{uri}" target="_blank">{uri}</a> ({method})</li>
                    """
                if not instances_html:
                    instances_html = '<li>Nenhuma URL específica encontrada</li>'

                # Use .get() com um valor padrão para evitar KeyError se o campo estiver faltando
                alert_name = alerta.get('name', 'Alerta sem nome')
                alert_desc = alerta.get('desc', 'Sem descrição disponível.')
                alert_solution = alerta.get('solution', 'Sem solução recomendada disponível.')
                alert_reference = alerta.get('reference')
                alert_cweid = alerta.get('cweid', 'N/A')
                alert_wascid = alerta.get('wascid', 'N/A')

                ref_html = f"""
                    <div class="alert-section">
                        <h4>Referência</h4>
                        <p><a href="{alert_reference}" target="_blank">{alert_reference}</a></p>
                    </div>
                """ if alert_reference else ''

                alerts_list_html += f"""
                    <div class="alert alert-{risk_info['class']}" data-riskcode="{risk_info['filter']}">
                        <div class="alert-header">
                            <h3 class="alert-title">{alert_name}</h3>
                            <span class="alert-risk risk-{risk_info['class']}">{risk_info['label']}</span>
                        </div>
                        <div class="alert-body">
                            <div class="alert-section">
                                <h4>Descrição</h4>
                                <p>{alert_desc}</p>
                            </div>
                            <div class="alert-extra" style="display:none">
                                <div class="alert-section">
                                    <h4>Solução</h4>
                                    <p>{alert_solution}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>CWE ID:</h4>
                                    <p>{alert_cweid}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>WASC ID:</h4>
                                    <p>{alert_wascid}</p>
                                </div>
                                <div class="alert-section">
                                    <h4>URLs Afetadas ({len(alerta.get('instances', []))})</h4>
                                    <ul class="url-list">
                                        {instances_html}
                                    </ul>
                                </div>
                                {ref_html}
                            </div>
                            <button class="ver-mais-btn">Ver mais ▼</button>
                        </div>
                    </div>
                """
        
        # --- Realiza as substituições no template HTML ---
        
        # Substitui a data do scan
        html_template_content = html_template_content.replace(
            "<!-- ZAP_SCAN_DATE_PLACEHOLDER -->", scan_date_formatted
        )

        # Substitui os cartões de estatísticas
        html_template_content = html_template_content.replace(
            "<!-- ZAP_STATS_PLACEHOLDER -->", summary_cards_html
        )

        # Substitui a lista de alertas
        html_template_content = html_template_content.replace(
            "<!-- ZAP_ALERTS_LIST_PLACEHOLDER -->", alerts_list_html
        )

        with open(output_html_path, 'w', encoding='utf-8') as f:
            f.write(html_template_content)

        print(f"Relatório HTML final gerado em: {output_html_path}")
        return True

    except FileNotFoundError:
        print(f"Erro: Arquivo não encontrado. Verifique os caminhos: JSON '{json_file_path}', HTML Template '{html_template_path}'")
        return False
    except json.JSONDecodeError:
        print(f"Erro: O arquivo JSON '{json_file_path}' não é um JSON válido.")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Uso: python generate_html_report.py <caminho_json> <caminho_template_html> <caminho_saida_html>")
        sys.exit(1)

    json_path = sys.argv[1]
    template_path = sys.argv[2]
    output_path = sys.argv[3]

    if not render_html_report(json_path, template_path, output_path):
        sys.exit(1) 