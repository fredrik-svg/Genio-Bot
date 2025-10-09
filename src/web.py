import os
import argparse
from flask import Flask, render_template, request, jsonify
from util import load_config, setup_logging
from client import BackendClient

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Global backend client
backend = None
device_name = None

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/ask', methods=['POST'])
def ask():
    """Handle text questions"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'Tom fråga'}), 400
        
        # Send to backend
        reply = backend.ask(device=device_name, text=text)
        
        return jsonify({'reply': reply})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def main(cfg_path: str, host: str = '0.0.0.0', port: int = 5000):
    global backend, device_name
    
    cfg = load_config(cfg_path)
    setup_logging(cfg.get("logging", {}).get("level", "INFO"))
    
    # Init backend client
    be_cfg = cfg.get("backend", {})
    backend = BackendClient(
        url=be_cfg["n8n_url"],
        response_key=be_cfg.get("response_key", "reply"),
        timeout_s=be_cfg.get("timeout_s", 30),
        headers=be_cfg.get("headers", {}),
    )
    
    device_name = os.uname().nodename
    
    print(f"🌐 Web frontend startar på http://{host}:{port}")
    app.run(host=host, port=port, debug=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Web frontend för Genio-Bot')
    parser.add_argument("--config", default="config.yaml", help="Sökväg till konfigurationsfil")
    parser.add_argument("--host", default="0.0.0.0", help="Host att binda till")
    parser.add_argument("--port", type=int, default=5000, help="Port att lyssna på")
    args = parser.parse_args()
    main(args.config, args.host, args.port)
