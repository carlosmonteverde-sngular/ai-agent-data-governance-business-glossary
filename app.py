from flask import Flask, render_template, request, jsonify, Response
import sys
import threading
import queue
import time
from main import main as execute_glossary_agent

app = Flask(__name__)

# Queue for capturing print output
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

# Replace stdout globally
sys.stdout = StreamCapture(sys.stdout)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/run", methods=["POST"])
def run_agent():
    data = request.json
    project_id = data.get("project_id", "pg-gccoe-carlos-monteverde")
    location = data.get("location", "us")
    target_dataset = data.get("target_dataset", "pharmaceutical_drugs")
    glossary_id = data.get("glossary_id", "business-glossary-v1")
    glossary_display_name = data.get("glossary_display_name", "Business Glossary")
    
    def run_task():
        try:
            execute_glossary_agent(
                project_id=project_id,
                location=location,
                target_dataset=target_dataset,
                glossary_id=glossary_id,
                glossary_display_name=glossary_display_name
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
            # wait for log entry
            try:
                # Prevent keeping connection open forever by putting a small timeout
                log = log_queue.get(timeout=30)
                if log == "DONE":
                    yield f"data: DONE\n\n"
                    break
                # Server sent events data payload
                yield f"data: {log}\n\n"
            except queue.Empty:
                # Send a ping to keep connection alive
                yield ": ping\n\n"
                
    return Response(event_stream(), mimetype="text/event-stream")

if __name__ == "__main__":
    app.run(debug=False, port=5000)
