# GitHub PR AI Agent
The AI GitHub Code Review Agent is an interactive application that automates and assists with repository management. It leverages Large Language Models (LLMs) like Google's Gemini 
to perform automated code reviews, suggest improvements, and execute changes directly within your GitHub repository through a conversational chat interface.

This agent can be connected to any GitHub repository via webhooks to provide real-time feedback on pull requests or be commanded manually to read files, analyze code, and push updates.

## Table of Contents
- [Features](#Features)
- [Project Structure](#project-structure)
- [Prerequisites & Installation](#prerequisites--installation)
- [Usage](#usage)
- [Technical Details](#technical-details)
- [Agent Commands](#agent-commands)

## Features
- **Automated PR Review:** Automatically reviews new pull requests and posts comments using AI.
- **Interactive Chat Interface:** A web-based chat UI to command the agent.
- **Full Repo Context:** The agent can list and read any file in the repository to understand the full context.
- **AI-Powered Code Suggestions:** Ask the AI to refactor code, fix bugs, or add features to any file.
- **Review & Push:** View a `diff` of the AI's suggested changes and push them to the repository with a single click.
- **History Viewer:** List recent pull requests directly from the chat interface.
- **Multi-Model Support:** Easily switch between different AI models (e.g., Google Gemini, Perplexity) for reviews.

## Project Structure
```bash
github-pr-reviewer/
├── src/
│   ├── models/             # SQLAlchemy models (optional)
│   ├── routes/             # Flask API route definitions
│   │   ├── agent_routes.py # Routes for agent actions (read, suggest, push)
│   │   └── pr_routes.py    # Routes for PR reviews and webhooks
│   ├── static/
│   │   └── agent.html      # The frontend chat interface
│   ├── ai_clients.py       # Clients for interacting with LLMs
│   ├── config.py           # Application configuration management
│   ├── github_client.py    # Client for interacting with the GitHub API
│   ├── main.py             # Main Flask application entry point
│   ├── pr_reviewer.py      # Core logic for the PR review process
│   └── webhook_handler.py  # Logic for handling GitHub webhooks
├── tests/                  # Unit tests for the application
├── .env.example            # Example environment file
├── .gitignore
├── requirements.txt        # Python dependencies
└── README.md
```

## Prerequisites & Installation

### Prerequisites
- Python 3.7+
- `pip` and `venv`
- [ngrok](https://ngrok.com/download) account and CLI (for local webhook development)

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/abhinav-nautiyal/Github-PR-AI-Agent.git
    cd github-pr-reviewer
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```
3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Set up your environment variables:**
    Rename `.env.example` to `.env` and fill in your credentials.
    ```ini
    # .env

    # GitHub Personal Access Token (PAT) with 'repo' scope
    GITHUB_TOKEN="ghp_YourGitHubPersonalAccessToken"

    # The full name of the repository you want the agent to work on
    GITHUB_REPO_NAME="your-github-username/your-repo-name"

    # A secret string for webhook verification
    GITHUB_WEBHOOK_SECRET="a-very-secret-string"

    # Your AI API Keys
    GEMINI_API_KEY="your_gemini_api_key_here"
    PERPLEXITY_API_KEY="your_perplexity_api_key_here"

    # Default model to use (gemini or perplexity)
    DEFAULT_AI_MODEL="gemini"

    # Set to True for more detailed logs during development
    DEBUG=True
    ```

## Usage

### 1. Run the Backend Server
Start the Flask application. This will serve the API and the frontend chat interface.
```bash
python src/main.py
```
The server will start on `http://127.0.0.1:5001`.

### 2. Expose Your Local Server with ngrok
To allow GitHub webhooks to reach your local machine, you need to expose your local server to the internet.

In a **new terminal window**, run the following command:
```bash
ngrok http 5001
```
`ngrok` will provide a public `https://` forwarding URL. **Copy this URL.**

### 3. Configure the GitHub Webhook
1.  Navigate to your target GitHub repository's settings page.
2.  Go to **Settings > Webhooks** and click **Add webhook**.
3.  **Payload URL**: Paste your `ngrok` forwarding URL and add `/api/pr/webhook` to the end.
    *(e.g., `https://random-string.ngrok-free.app/api/pr/webhook`)*
4.  **Content type**: Set to `application/json`.
5.  **Secret**: Enter the same secret string you defined in your `.env` file for `GITHUB_WEBHOOK_SECRET`.
6.  **Which events?**: Select "Send me everything" or choose individual events like "Pull requests".
7.  Click **Add webhook**.

### 4. Use the Chat Interface
You're all set! Open your web browser and navigate to:
**http://127.0.0.1:5001/static/agent.html**

You can now use the chat interface to interact with your AI agent.

## Technical Details
- **Backend**: **Flask** serves a REST API that handles all core logic.
- **Frontend**: A single-page application built with vanilla **JavaScript**, **HTML**, and styled with **Tailwind CSS**.
- **GitHub Integration**: Uses the **PyGithub** library for all GitHub API interactions and relies on **Webhooks** for real-time event notifications (e.g., new PRs).
- **AI Model Integration**: The system is designed with a modular `AIModelManager` that can interact with multiple LLMs. Currently supports:
    - **Google Gemini**
    - **Perplexity**

## Agent Commands
Interact with the agent using these commands in the chat interface:

| Command                                         | Alias     | Description                                                     |
| ----------------------------------------------- | --------- | --------------------------------------------------------------- |
| `list files`                                    | `ls`      | Lists all files and directories in the repository.              |
| `list prs`                                      | `history` | Shows a list of the 10 most recent pull requests.               |
| `read [filepath]`                               | `cat`     | Displays the full content of the specified file.                |
| `review pr [number]`                            |           | Triggers an AI-powered review and posts it as a PR comment.     |
| `suggest changes for [filepath] to [your goal]` |           | Asks the AI to modify a file and shows you the proposed changes.|
