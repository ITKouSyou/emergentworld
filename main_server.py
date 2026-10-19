import sys
import os
import traceback

if getattr(sys, 'frozen', False):
    base_dir = os.path.dirname(sys.executable)
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, base_dir)

log_file = open(os.path.join(base_dir, "server_error.log"), "w", encoding="utf-8")
sys.stderr = log_file

try:
    import uvicorn
    from server.main import app
    if __name__ == "__main__":
        uvicorn.run(app, host="127.0.0.1", port=8000, log_config=None)
except Exception as e:
    traceback.print_exc(file=log_file)
    log_file.flush()
