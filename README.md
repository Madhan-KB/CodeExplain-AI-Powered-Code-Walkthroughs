CodeExplain – AI-Powered Code Walkthroughs

CodeExplain helps developers understand any GitHub repository faster.
Point it at a repo URL and get an interactive, AI-generated walkthrough of the entire codebase—functions, classes, and architecture.

✨ Features

🔍 Automatic Code Parsing – Pulls the repo and analyzes files/language automatically.

🤖 AI-Generated Explanations – Step-by-step breakdown of each module, class, and function.

🗂 Interactive Navigation – Click through the code hierarchy or search for specific components.

🧩 Multi-Language Support – Works with Python, JavaScript/TypeScript, Java, and more.

🌐 Web App & CLI – Browse explanations in a browser or generate a markdown summary from the terminal.
🚀 Getting Started
Prerequisites

Python 3.10+ and Node 18+

An OpenAI API key (or compatible LLM endpoint)

Installation
# Clone the repo
git clone https://github.com/<your-username>/codeexplain.git
cd codeexplain

# Backend setup
cd backend
pip install -r requirements.txt
cp .env.example .env   # add your API keys

# Frontend setup
cd ../frontend
npm install

Run Locally
# Backend
uvicorn app.main:app --reload

# Frontend (in another terminal)
npm run dev


Visit: http://localhost:3000

🧪 Usage

Paste a GitHub repo URL in the UI or CLI.

The system fetches and parses the codebase.

Interact with the generated explanation tree or export it to Markdown/PDF.

🗺 Roadmap

 Add authentication & user dashboards

 Improve multi-language coverage

 Add “diff explanations” for pull requests

 VS Code extension

🤝 Contributing

Contributions, issues, and feature requests are welcome!
Fork the repo and create a pull request.

📜 License

MIT License

🙌 Acknowledgements

Thanks to open-source libraries and the developer community for inspiration and support.
