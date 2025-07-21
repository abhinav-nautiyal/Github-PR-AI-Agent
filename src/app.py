from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/pr/logs', methods=['GET'])
def get_logs():
    try:
        with open('pr_reviewer.log', 'r') as f:
            lines = f.readlines()[-100:]
        return jsonify({'logs': lines})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 