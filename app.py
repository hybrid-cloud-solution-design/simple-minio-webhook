from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def main():
    payload = request.get_json()
    print(payload, flush=True)
    return jsonify(payload)

# Get the PORT from environment
port = os.getenv('PORT', '8081')
debug = os.getenv('DEBUG', 'false')

if __name__ == '__main__':
    print("application ready - Debug is " + str(debug))
    app.run(host='0.0.0.0', port=int(port))