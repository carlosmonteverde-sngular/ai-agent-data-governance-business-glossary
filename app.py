from flask import Flask, render_template, request, jsonify, Response
import sys
import threading
import queue
from modules.glossary_matcher import scan_table, build_proposal, write_proposal
# NOTA: `main` (agente IA) se importa de forma perezosa en /run, para que la pestaña de
# Onboarding funcione aunque no estén instaladas las deps del agente (PyGithub, genai…).

app = Flask(__name__)

# Cola para capturar la salida (logs) del agente de generación por IA.
log_queue = queue.Queue()


class StreamCapture:
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout

    def write(self, text):
        if text.strip():
            log_queue.put(text.strip())
        self.original_stdout.write(text)

    def flush(self):
        self.original_stdout.flush()


sys.stdout = StreamCapture(sys.stdout)


@app.route("/")
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# Pestaña "Onboarding de tabla": buscarV de una tabla nueva contra el glosario
# ---------------------------------------------------------------------------
@app.route("/onboard/scan", methods=["POST"])
def onboard_scan():
    d = request.json or {}
    try:
        res = scan_table(d["project"].strip(), d["dataset"].strip(), d["table"].strip())
        return jsonify({"ok": True, **res})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/onboard/suggest", methods=["POST"])
def onboard_suggest():
    """IA (Gemini/Vertex) recomienda los parámetros de un término nuevo para una columna."""
    d = request.json or {}
    try:
        from modules.glossary_matcher import suggest_term
        s = suggest_term(d["column"], d.get("type", ""), d["asset"], d.get("term_name", ""))
        return jsonify({"ok": True, **s})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/onboard/propose", methods=["POST"])
def onboard_propose():
    d = request.json or {}
    try:
        prop = build_proposal(d["asset"], d.get("rows", []))
        path = write_proposal(d["asset"], prop)
        return jsonify({"ok": True, "path": path, **prop})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# Pestaña "Generar glosario (IA)": el agente original (BigQuery/Drive → Gemini)
# ---------------------------------------------------------------------------
@app.route("/run", methods=["POST"])
def run_agent():
    data = request.json or {}
    project_id = data.get("project_id", "pg-gccoe-carlos-monteverde")
    location = data.get("location", "us")
    target_dataset = data.get("target_dataset", "pharmaceutical_drugs")
    glossary_id = data.get("glossary_id", "business-glossary-v1")
    glossary_display_name = data.get("glossary_display_name", "Business Glossary")
    data_source = data.get("data_source", "bigquery")
    drive_folder_id = data.get("drive_folder_id", "")
    publish_mode = data.get("publish_mode", "pull_request")

    def run_task():
        try:
            from main import main as execute_glossary_agent   # import perezoso
            execute_glossary_agent(
                project_id=project_id, location=location, target_dataset=target_dataset,
                glossary_id=glossary_id, glossary_display_name=glossary_display_name,
                data_source=data_source, drive_folder_id=drive_folder_id, publish_mode=publish_mode,
            )
            log_queue.put("DONE")
        except Exception as e:
            log_queue.put(f"❌ ERROR: {str(e)}")
            log_queue.put("DONE")

    threading.Thread(target=run_task).start()
    return jsonify({"status": "started"})


@app.route("/stream")
def stream():
    def event_stream():
        while True:
            try:
                log = log_queue.get(timeout=30)
                if log == "DONE":
                    yield "data: DONE\n\n"
                    break
                yield f"data: {log}\n\n"
            except queue.Empty:
                yield ": ping\n\n"

    return Response(event_stream(), mimetype="text/event-stream")


if __name__ == "__main__":
    app.run(debug=False, port=5000)
