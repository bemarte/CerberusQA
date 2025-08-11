from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import sys
import os


app = Flask(__name__)

CORS(app)

@app.route("/run-test", methods=["POST"])
def run_test():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL não fornecida"}), 400

    try:
        # Executa o main.py como subprocesso para manter compatibilidade com execução via terminal
        process = subprocess.Popen(
            [sys.executable, "main.py", url],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__)) + "/..",
            text=True
        )
        stdout, stderr = process.communicate()

        return jsonify({
            "success": True,
            "output": stdout,
            "errors": stderr
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
