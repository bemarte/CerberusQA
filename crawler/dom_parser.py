# crawler/dom_parser.py
import json
import os
import time
from playwright.sync_api import Page

# carrega blocklist para evitar clicar em redes sociais/apps
BLOCKLIST_FILE = os.path.join(os.path.dirname(__file__), "blocklist.json")
if not os.path.exists(BLOCKLIST_FILE):
    # fallback para raiz
    BLOCKLIST_FILE = os.path.join(os.path.dirname(__file__), "..", "blocklist.json")
if os.path.exists(BLOCKLIST_FILE):
    try:
        with open(BLOCKLIST_FILE, "r", encoding="utf-8") as f:
            BLOCKLIST = json.load(f)
    except Exception:
        BLOCKLIST = []
else:
    BLOCKLIST = []

def is_blocked_url(url):
    if not url:
        return False
    return any(url.startswith(b) for b in BLOCKLIST)

def _get_element_info(page, el):
    """
    Pega href/text/onclick de maneira segura (antes de clicar).
    Usa evaluate para ler atributos no contexto da página, evitando problemas de execution context.
    """
    try:
        info = page.evaluate("""
            (el) => {
                return {
                    href: el.getAttribute ? el.getAttribute('href') : null,
                    onclick: el.getAttribute ? el.getAttribute('onclick') : null,
                    text: (el.innerText || '').trim()
                }
            }
        """, el)
        return info.get("href"), info.get("text"), info.get("onclick")
    except Exception:
        # fallback minimal
        try:
            href = el.get_attribute("href")
        except Exception:
            href = None
        try:
            onclick = el.get_attribute("onclick")
        except Exception:
            onclick = None
        try:
            text = el.inner_text()
        except Exception:
            text = ""
        return href, text, onclick

def click_elements(page: Page, logs_container: list = None, max_clicks: int = 30):
    """
    Tenta clicar em elementos 'a, button, [role=button], input[type=submit]'.
    logs_container: opcional, se passado, append de logs será feito nele; caso contrário, logs são apenas printados.
    """
    logs = logs_container if isinstance(logs_container, list) else []
    try:
        elements = page.query_selector_all("a, button, [role='button'], input[type='submit'], input[type='button']")
    except Exception as e:
        print(f"[DomParser] Erro ao buscar elementos clicáveis: {e}")
        return logs

    print(f"[DomParser] Encontrados {len(elements)} elementos clicáveis (seletores iniciais).")
    clicked = 0

    for el in elements:
        if clicked >= max_clicks:
            print("[DomParser] Limite de cliques atingido.")
            break

        try:
            href, text, onclick = _get_element_info(page, el)

            # normalizar href relativo para exibir, mas para blocklist verificar startswith
            href_display = href or ""
            # filtro blocklist
            if href and is_blocked_url(href):
                print(f"[DomParser][skip] blocklist href: {href}")
                logs.append({"type": "skipped_click", "reason": "blocklist_href", "href": href, "text": text})
                continue

            lowtext = (text or "").lower()
            if any(k in lowtext for k in ["facebook", "instagram", "twitter", "linkedin", "play store", "app store", "aceitar cookies", "whatsapp"]):
                print(f"[DomParser][skip] blocklist text pattern: {text}")
                logs.append({"type": "skipped_click", "reason": "blocklist_text", "text": text, "href": href})
                continue

            print(f"[DomParser] Clicando elemento: text='{(text or '')[:60]}', href='{href_display}'")
            logs.append({"type": "click_attempt", "text": text, "href": href, "onclick": onclick})

            # Estratégia 1: click do Playwright (padrão)
            try:
                el.click(timeout=2000)
                # espera curta para rede reagir
                page.wait_for_timeout(800)
                # opcional: aguardar networkidle por um curto período
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
                clicked += 1
                continue
            except Exception as e_click:
                logs.append({"type": "click_error", "err": str(e_click), "method": "handle.click"})
                print(f"[DomParser] click via handle falhou: {e_click}")

            # Estratégia 2: evaluate click (dispatch event)
            try:
                page.evaluate("(el) => { el.scrollIntoView({block:'center'}); el.dispatchEvent(new MouseEvent('click', {bubbles:true, cancelable:true})); }", el)
                page.wait_for_timeout(800)
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
                clicked += 1
                continue
            except Exception as e_eval:
                logs.append({"type": "click_error", "err": str(e_eval), "method": "evaluate.dispatch"})
                print(f"[DomParser] click via evaluate falhou: {e_eval}")

            # Estratégia 3: mouse click no centro do elemento (fazer coordenadas)
            try:
                box = el.bounding_box()
                if box:
                    x = box["x"] + box["width"] / 2
                    y = box["y"] + box["height"] / 2
                    page.mouse.click(x, y)
                    page.wait_for_timeout(800)
                    try:
                        page.wait_for_load_state("networkidle", timeout=3000)
                    except Exception:
                        pass
                    clicked += 1
                    continue
                else:
                    raise RuntimeError("no bounding box")
            except Exception as e_mouse:
                logs.append({"type": "click_error", "err": str(e_mouse), "method": "mouse.click"})
                print(f"[DomParser] click via mouse falhou: {e_mouse}")

        except Exception as e:
            logs.append({"type": "dom_iter_error", "err": str(e)})
            print(f"[DomParser] Erro iterando elemento: {e}")

    print(f"[DomParser] Total cliques realizados: {clicked}")
    return logs
