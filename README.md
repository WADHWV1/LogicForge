# LogicForge

LogicForge turns rough pseudocode into clean code and beginner-friendly learning notes. It preserves meaningful variable names, checks the core logic, supports multiple target languages, and lets you choose from models available to your signed-in GitHub Copilot account.

## Run locally on Windows

Requirements: Python 3.11 or newer and an active GitHub Copilot plan. LogicForge uses Copilot CLI sign-in through the GitHub Copilot SDK; it does not require an Anthropic API key.

1. Install Copilot CLI and sign in:

   ```powershell
   winget install GitHub.Copilot
   copilot login
   ```

2. In the extracted `LogicForge` folder, set up the Python environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m copilot download-runtime
   ```

3. Start the server and open <http://127.0.0.1:5000>:

   ```powershell
   python app.py
   ```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.

## Languages, models, and history

The language menu includes Auto, Python, JavaScript, TypeScript, C, C++, C#, **C# / .NET**, Java, Go, Rust, PHP, Ruby, SQL, HTML/CSS, Bash, Swift, and Kotlin. The dedicated .NET target generates modern C# and defaults to a simple console-app shape unless you request another framework, such as ASP.NET Core or Unity. The model menu loads options available to your signed-in Copilot account and always includes **Auto**. Copilot Free accounts can use Auto when individual model selection is unavailable. Set `$env:COPILOT_MODEL` before starting the server to choose a default model available on your plan.

The **Updated Patches** timeline includes V1–V7 project milestones. After conversion, LogicForge retrieves relevant coding guidance, generates code and a beginner walkthrough, asks for a second model review, and runs deterministic checks. It may make one repair pass and check the repaired result. Python output gets a Python AST syntax check; other languages report when a parser was not run. It checks that detected user variable/function names appear in the code. Code is not executed automatically. The optional **Compile & Run** action sends the selected code and optional stdin to your configured Judge0 service only after you tick the confirmation box and press the button. Each answer reports retrieval method, review result, and checks. The commit history panel reads recent public commits for an `owner/repository` entered in the page and remembers that choice in the browser.

## Configure online Compile & Run

LogicForge integrates with Judge0, an online sandboxed code execution service. The old public Piston API is no longer freely available, so compiler access requires a Judge0 provider/account or your own Judge0 instance. Judge0 documents a RapidAPI Basic plan and self-hosting as options. Check the provider’s current limits before frequent use. Code and stdin are sent to the configured Judge0 endpoint only when you explicitly confirm and submit them; never send secrets or private code.

For a Judge0 RapidAPI subscription, set these PowerShell variables in the same terminal where you start LogicForge (keep the key private):

```powershell
$env:JUDGE0_BASE_URL = "https://judge0-ce.p.rapidapi.com"
$env:JUDGE0_API_HOST = "judge0-ce.p.rapidapi.com"
$env:JUDGE0_API_KEY = "YOUR_RAPIDAPI_KEY"
python app.py
```

For a self-hosted or institution-managed Judge0 service, set `JUDGE0_BASE_URL` to its API base URL. If it requires Judge0’s `X-Auth-Token`, set `$env:JUDGE0_AUTH_TOKEN` in the terminal. Do not put credentials in `templates/index.html`, `docs/site-config.js`, or a public repository. The server applies fixed source/input, CPU, memory, and runtime limits. The UI enables the compiler only after it detects a configured endpoint.

## AI checks and retrieval

The default RAG path uses built-in curated software guidance and a local TF-IDF fallback with no extra packages. To use semantic embeddings locally, install and start [Ollama](https://ollama.com), then run `ollama pull nomic-embed-text`; LogicForge will use Ollama's local embedding endpoint when available. It does not upload prompts for retrieval.

Conversion uses multiple model requests: generation, independent review, and sometimes repair plus a final review. This can consume more Copilot or local-model time than the earlier one-call version. A model review is advisory, not proof of correctness.

## Optional local model and LoRA tuning

You can run a local model through Ollama by setting `$env:LOGICFORGE_PROVIDER = "ollama"` before `python app.py`. LogicForge reads available local models from Ollama. The optional [`training/README.md`](training/README.md) explains how to train a LoRA adapter on reviewed examples and serve it through Ollama. This is separate from Copilot; it does not fine-tune Copilot's hosted models. Training dependencies are optional and are not installed by the normal setup.

## Publish the UI on GitHub Pages

GitHub Pages hosts the static interface; it does not run the Flask/Copilot backend. To use conversion from the hosted page, host the Flask app separately.

1. Push this project to the repository's `main` branch. The included `.github/workflows/pages.yml` publishes `docs/` on each push and copies the current editor from `templates/index.html` before deployment.
2. In **Settings → Pages**, select **GitHub Actions** as the deployment source. A private repository needs a GitHub plan that supports Pages for private repositories. Pages sites are public by default, so the deployed interface and any bundled frontend code can be viewed by anyone even when the source repository is private.
3. GitHub Pages hosts only the static interface; it does not run Flask or Copilot. To enable conversion from the hosted UI, set `apiBaseUrl` in `docs/site-config.js` to a separately hosted Flask API origin, and add `https://YOUR-USERNAME.github.io` to `LOGICFORGE_ALLOWED_ORIGINS` on the backend.

Never put a Copilot token in `docs/site-config.js` or browser JavaScript. Protect any public backend with authentication and rate limits. For local use, leave `apiBaseUrl` empty.
