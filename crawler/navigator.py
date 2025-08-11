# crawler/navigator.py
import json
import os

# Carrega lista de bloqueio (procura arquivo na raiz do projeto)
BLOCKLIST_FILE = "blocklist.json"
if os.path.exists(BLOCKLIST_FILE):
    with open(BLOCKLIST_FILE, "r", encoding="utf-8") as f:
        try:
            BLOCKLIST = json.load(f)
        except Exception:
            BLOCKLIST = []
else:
    BLOCKLIST = []

def should_block(url):
    return any(url.startswith(b) for b in BLOCKLIST)

def run_crawler(url):
    """
    Execução principal do crawler.
    - configura bloqueio de domínios (context.route)
    - configura logging (setup_logging) e recebe finalize()
    - navega, faz cliques, depois chama finalize() e salva logs
    """
    from playwright.sync_api import sync_playwright
    from .dom_parser import click_elements
    from .report_generator import save_log
    from .network_logger import setup_logging

    print("[Navigator] Iniciando Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()

        def route_handler(route, request):
            if should_block(request.url):
                print(f"[Navigator][Block] abort {request.url}")
                route.abort()
            else:
                route.continue_()

        context.route("**/*", route_handler)

        page = context.new_page()

        # configurando captura de rede e pegando finalize()
        print("[Navigator] Configurando network logger...")
        finalize_network = setup_logging(page)

        try:
            print(f"[Navigator] Acessando: {url}")
            page.goto(url, timeout=60000)
            print("[Navigator] goto: ok")
        except Exception as e:
            print(f"[Navigator] Erro no goto: {e}")

        try:
            page.wait_for_load_state("networkidle", timeout=60000)
            print("[Navigator] networkidle: ok")
        except Exception as e:
            print(f"[Navigator] Aviso: networkidle não atingido / timeout: {e}")

        # executar cliques (dom_parser se encarrega de logs de tentativa)
        try:
            print("[Navigator] Iniciando click_elements...")
            click_elements(page, logs_container=None)  # dom_parser pode aceitar logs interno; alteraremos se precisar
        except Exception as e:
            print(f"[Navigator] Erro durante clicks: {e}")

        # **Muito importante**: agora agregamos os dados de network
        print("[Navigator] Finalizando captura de rede e agregando logs...")
        try:
            network_logs = finalize_network()
            # salvar via report_generator; report_generator espera lista de logs.
            save_log(network_logs)
            print(f"[Navigator] Network logs agregados: {len(network_logs)} entradas")
        except Exception as e:
            print(f"[Navigator] Erro ao finalizar logs de rede: {e}")
            # fallback: salvar um arquivo vazio
            save_log([])

        # fechar navegador
        browser.close()
        print("[Navigator] Navegador fechado. Fim.")
