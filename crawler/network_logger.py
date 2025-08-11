# crawler/network_logger.py
import threading
import time

def setup_logging(page):
    """
    Configura listeners de request/response e retorna:
      - logs_store: lista onde serão colocados entradas temporárias (opcional)
      - finalize(): função que agrega request/response no formato final e retorna a lista
    Uso:
      logs_list = []
      finalize = setup_logging(page, logs_list)
      ... navegar ...
      final_logs = finalize()  # retorna a lista final (request+response agrupados)
    """
    request_map = {}  # url -> [ { "request": {...}, "response": None or {...}, "ts_request":..., "ts_response":... } ]
    lock = threading.Lock()

    def on_request(request):
        try:
            entry = {
                "request": {
                    "method": request.method,
                    "url": request.url,
                    "headers": dict(request.headers)
                },
                "response": None,
                "ts_request": time.time()
            }
            with lock:
                request_map.setdefault(request.url, []).append(entry)
        except Exception as e:
            with lock:
                request_map.setdefault("__errors__", []).append({"type": "request_error", "err": str(e)})

    def on_response(response):
        try:
            url = response.url
            resp_obj = {
                "status": response.status,
                "url": response.url,
                "headers": dict(response.headers)
            }
            with lock:
                if url in request_map:
                    # encontrar a primeira entrada sem response e preenchê-la
                    for e in request_map[url]:
                        if e.get("response") is None:
                            e["response"] = resp_obj
                            e["ts_response"] = time.time()
                            break
                    else:
                        # todas as entradas já têm response -> criar nova com request=None
                        request_map.setdefault(url, []).append({
                            "request": None,
                            "response": resp_obj,
                            "ts_response": time.time()
                        })
                else:
                    # response sem request conhecido (cache ou outro caso)
                    request_map[url] = [{
                        "request": None,
                        "response": resp_obj,
                        "ts_response": time.time()
                    }]
        except Exception as e:
            with lock:
                request_map.setdefault("__errors__", []).append({"type": "response_error", "err": str(e)})

    # conectar os listeners
    page.on("request", on_request)
    page.on("response", on_response)

    def finalize():
        """Consolida request_map em uma lista ordenada e retorna essa lista."""
        final_logs = []
        with lock:
            # erros em separado
            if "__errors__" in request_map:
                for err in request_map["__errors__"]:
                    final_logs.append(err)
                # remover para evitar iteração dupla
                del request_map["__errors__"]

            for url, entries in request_map.items():
                for e in entries:
                    final_logs.append({
                        "request": e.get("request"),
                        "response": e.get("response"),
                        "ts_request": e.get("ts_request"),
                        "ts_response": e.get("ts_response")
                    })
        return final_logs

    # Retornar finalize para que o caller invoque no momento certo
    return finalize
