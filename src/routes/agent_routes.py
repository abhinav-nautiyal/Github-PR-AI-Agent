from flask import Blueprint, request, jsonify
from github import Github
import os
import difflib

# This blueprint will be registered with the '/api' prefix in main.py
agent_bp = Blueprint('agent', __name__)

# In-memory store for pending edits (for demo purposes)
# In a production app, you might use a database or a cache like Redis.
pending_edits = {}

# GitHub setup (This relies on GITHUB_TOKEN and GITHUB_REPO_NAME being in your .env file)
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
REPO_NAME = os.getenv('GITHUB_REPO_NAME')
g = Github(GITHUB_TOKEN)
repo = g.get_repo(REPO_NAME) if GITHUB_TOKEN and REPO_NAME else None

# The route path is now just '/agent/files'. 
# Flask will combine it with the blueprint's '/api' prefix to make the full URL '/api/agent/files'.
@agent_bp.route('/agent/files', methods=['GET'])
def list_files():
    if not repo:
        return jsonify({'error': 'GitHub repo not configured. Ensure GITHUB_TOKEN and GITHUB_REPO_NAME are in your .env file.'}), 400
    try:
        # Get repository contents at the root level
        contents = repo.get_contents("")
        files = []
        # Recursively list all files in the repository
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            else:
                files.append(file_content.path)
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': f'Could not list files: {str(e)}'}), 500

# Corrected route path
@agent_bp.route('/agent/diff', methods=['POST'])
def get_diff():
    if not repo:
        return jsonify({'error': 'GitHub repo not configured'}), 400
    data = request.json
    path = data.get('path')
    if not path:
        return jsonify({'error': 'File path required'}), 400
    try:
        file_content_obj = repo.get_contents(path)
        file_content = file_content_obj.decoded_content.decode()
        new_content = data.get('new_content', '')
        diff = list(difflib.unified_diff(file_content.splitlines(keepends=True), new_content.splitlines(keepends=True), fromfile=path, tofile=path))
        return jsonify({'diff': ''.join(diff)})
    except Exception as e:
        return jsonify({'error': f'Could not get diff for {path}: {str(e)}'}), 500

# Corrected route path
@agent_bp.route('/agent/edit', methods=['POST'])
def accept_edit():
    data = request.json
    path = data.get('path')
    new_content = data.get('new_content')
    if not path or new_content is None:
        return jsonify({'error': 'path and new_content required'}), 400
    pending_edits[path] = new_content
    return jsonify({'message': 'Edit is staged and ready to be pushed.', 'path': path})

# Corrected route path
@agent_bp.route('/agent/push', methods=['POST'])
def push_edits():
    if not repo:
        return jsonify({'error': 'GitHub repo not configured'}), 400
    commit_message = request.json.get('commit_message', 'AI agent code update')
    if not pending_edits:
        return jsonify({'error': 'No pending edits to push.'}), 400
        
    results = []
    try:
        for path, new_content in pending_edits.items():
            # Get the latest sha of the file to avoid conflicts
            file = repo.get_contents(path)
            repo.update_file(path, commit_message, new_content, file.sha)
            results.append({'path': path, 'status': 'pushed'})
        pending_edits.clear() # Clear edits after successful push
        return jsonify({'message': 'All staged edits have been successfully pushed to the repository.', 'results': results})
    except Exception as e:
        return jsonify({'error': f'Failed to push changes: {str(e)}'}), 500
