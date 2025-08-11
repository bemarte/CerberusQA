import json
import os

OUTPUT_DIR = "output"
LOG_FILE = os.path.join(OUTPUT_DIR, "logs.json")
REPORT_FILE = os.path.join(OUTPUT_DIR, "report.html")
TEMPLATE_FILE = "output/report.html"  # Ajuste se o caminho for diferente

def save_log(network_logs):
    """Salva os logs de rede no arquivo LOG_FILE."""
    # Garante que o diretório de saída existe
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Salva os logs no arquivo
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(network_logs, f, ensure_ascii=False, indent=2)
    
    print(f"[ReportGenerator] Logs salvos em: {LOG_FILE}")
    
    # Gera o relatório automaticamente após salvar os logs
    generate_report()


def format_time_or_size(entry):
    """Retorna string formatada com tempo (ms/s) ou tamanho do request."""
    req = entry.get("request", {})
    res = entry.get("response", {})

    ts_req = entry.get("ts_request")
    ts_res = entry.get("ts_response")

    # Caso tenha tempo
    if ts_req is not None and ts_res is not None:
        elapsed = (ts_res - ts_req) * 1000  # ms
        if elapsed < 1000:
            return f"{elapsed:.0f} ms"
        else:
            return f"{elapsed / 1000:.2f} s"

    # Caso não tenha tempo → calcular tamanho do request
    body = req.get("body", "")
    if isinstance(body, str):
        size = len(body.encode("utf-8"))
    elif isinstance(body, bytes):
        size = len(body)
    else:
        size = 0

    if size < 1024:
        return f"{size} B"
    else:
        return f"{size / 1024:.1f} KB"


def generate_report():
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        logs = json.load(f)

    # Adicionar campo calculado para cada log
    for entry in logs:
        entry["time_or_size"] = format_time_or_size(entry)

    with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
        template_html = f.read()

    # Injeta os logs
    final_html = template_html.replace("{{LOGS_JSON}}", json.dumps(logs, ensure_ascii=False))

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"[ReportGenerator] Relatório gerado: {REPORT_FILE}")


if __name__ == "__main__":
    generate_report()
