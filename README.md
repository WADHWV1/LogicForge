# LogicForge

LogicForge turns rough pseudocode into clean code and beginner-friendly learning notes. It preserves meaningful variable names, checks the core logic, supports multiple target languages, and lets you choose from models available to your signed-in GitHub Copilot account.

## Run locally on Windows

Requirements: Python 3.11 or newer. Choose either the GitHub Copilot provider or the local Ollama setup below. LogicForge does not require an Anthropic API key.

1. For GitHub Copilot mode, install Copilot CLI and sign in:

   ```powershell
   winget install GitHub.Copilot
   copilot login
   ```

2. In the extracted `LogicForge` folder, set up the Python environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m copilot download-runtime  # only needed for Copilot mode
   ```

3. Start the server and open <http://127.0.0.1:5000>:

   ```powershell
   python app.py
   ```

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, then activate again.

### Run with a local AI model (no Copilot API key)

After installing the Python requirements above, run in PowerShell from the extracted project folder:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-local-ai.ps1
```

The script installs Ollama with `winget` if needed, downloads `qwen2.5-coder:3b` and `nomic-embed-text`, then starts LogicForge using Ollama. This 3B coding model is a practical laptop starting point, but still needs several gigabytes of memory and may be slower or less capable than larger models. To use another model, pull it with `ollama pull MODEL_NAME` and run `.\setup-local-ai.ps1 -ChatModel MODEL_NAME`. Model inference and retrieval stay on your computer; downloading Ollama and model weights requires internet once.

## Languages, models, and history

The language menu includes Auto, Python, JavaScript, TypeScript, C, C++, C#, **C# / .NET**, Java, Go, Rust, PHP, Ruby, SQL, HTML/CSS, Bash, Swift, and Kotlin. The dedicated .NET target generates modern C# and defaults to a simple console-app shape unless you request another framework, such as ASP.NET Core or Unity. The model menu loads models from whichever provider you selected (Copilot or Ollama). In Copilot mode, Copilot Free accounts can use Auto when individual model selection is unavailable. Set `$env:COPILOT_MODEL` to choose a default Copilot model, or `$env:OLLAMA_CHAT_MODEL` for Ollama.

The **Updated Patches** timeline contains the project milestones. After conversion, LogicForge retrieves coding guidance, generates code and a beginner walkthrough, asks for a second model review, and runs deterministic checks. It may make one repair pass. Python output gets an AST syntax check; other languages report when a parser was not run. Explicit variable/function names are checked. The **Ask about this code** chat uses the current input and output with the selected model. Python output can be downloaded as a notebook for manual upload to Google Colab. The confusion-matrix evaluator calculates accuracy, macro precision, recall, and F1 locally from actual/predicted labels. It applies to classification models with labeled test data, not general code quality; use tests, assertions, and compiler results for other code. Compile & Run sends code and optional stdin to Judge0 only after explicit confirmation. Commit history reads recent public commits for an `owner/repository` entered in the page.

## Configure online Compile & Run

LogicForge uses Judge0 CE’s public endpoint as a no-key starter and probes it when the page opens. The shared service can be busy, rate-limited, or unavailable; the page reports whether it responds. For steadier use, configure a Judge0 provider/account or self-host an instance. Check current limits before frequent use. Code and stdin are sent only when you explicitly confirm and submit them; never send secrets or private code.

For a Judge0 RapidAPI subscription, set these PowerShell variables in the same terminal where you start LogicForge (keep the key private):

```powershell
$env:JUDGE0_BASE_URL = "https://judge0-ce.p.rapidapi.com"
$env:JUDGE0_API_HOST = "judge0-ce.p.rapidapi.com"
$env:JUDGE0_API_KEY = "YOUR_RAPIDAPI_KEY"
python app.py
```

For a self-hosted or institution-managed Judge0 service, set `JUDGE0_BASE_URL` to its API base URL. If it requires Judge0’s `X-Auth-Token`, set `$env:JUDGE0_AUTH_TOKEN` in the terminal. Do not put credentials in `templates/index.html`, `docs/site-config.js`, or a public repository. The server applies fixed source/input, CPU, memory, and runtime limits. The UI enables the compiler only after it detects an endpoint that responds with active languages.

## AI checks and retrieval

The RAG path uses built-in curated software guidance and a local TF-IDF fallback with no extra packages. With Ollama enabled and `nomic-embed-text` installed, it uses local semantic embeddings. Retrieval does not upload prompts.

Conversion uses multiple model requests: generation, independent review, and sometimes repair plus a final review. This can consume more Copilot or local-model time than the earlier one-call version. A model review is advisory, not proof of correctness.

## Optional local model and LoRA tuning

Run a local model with `setup-local-ai.ps1`, or set `$env:LOGICFORGE_PROVIDER = "ollama"` before `python app.py`. The optional [`training/README.md`](training/README.md) describes LoRA tuning with reviewed examples. The included approved dataset is intentionally empty, so LogicForge has not been fine-tuned yet. Gather at least 20 reviewed examples (100+ varied examples and a separate test set are a better starting point) before training. This path does not modify Copilot’s hosted models; training dependencies are optional.

## Publish the UI on GitHub Pages

GitHub Pages hosts the static interface; it does not run the Flask/Copilot backend. To use conversion from the hosted page, host the Flask app separately.

1. Push this project to the repository's `main` branch. The included `.github/workflows/pages.yml` publishes `docs/` on each push and copies the current editor from `templates/index.html` before deployment.
2. In **Settings → Pages**, select **GitHub Actions** as the deployment source. A private repository needs a GitHub plan that supports Pages for private repositories. Pages sites are public by default, so the deployed interface and any bundled frontend code can be viewed by anyone even when the source repository is private.
3. GitHub Pages hosts only the static interface; it does not run Flask or Copilot. To enable conversion from the hosted UI, set `apiBaseUrl` in `docs/site-config.js` to a separately hosted Flask API origin, and add `https://YOUR-USERNAME.github.io` to `LOGICFORGE_ALLOWED_ORIGINS` on the backend.

Never put a Copilot token in `docs/site-config.js` or browser JavaScript. Protect any public backend with authentication and rate limits. For local use, leave `apiBaseUrl` empty.

## Hosted LogicForge deployment

The hosted UI lives at <https://wadhwv1.github.io/logicforge-pages/> and the Flask API runs as a separate Render web service. `render.yaml` defines the Python 3.12.8 service, Gunicorn start command, health check, CORS origin, and backend access-key generation. The Pages app sends requests only to the API URL configured in its public `site-config.js`. The API requires a random `LOGICFORGE_ACCESS_TOKEN`; enter that key in the page's **Hosted API access** box. The browser holds it in `sessionStorage` for the current tab session only. Requests are limited to 12 conversions or executions per server process.

For a hosted Copilot deployment, use the Copilot CLI sign-in supported by the backend environment and follow the current GitHub Copilot SDK authentication instructions. Keep credentials in the host’s secret variables only. Copilot quotas and billing follow the account plan; the backend does not include a free or unlimited model key. Local Ollama mode needs no Copilot credential.

For local development, leave `LOGICFORGE_ACCESS_TOKEN` unset. Copilot CLI sign-in continues to work as described above. Public `LOGICFORGE_ALLOWED_ORIGINS` defaults to the LogicForge GitHub Pages origin; add any additional exact origins as a comma-separated host variable. Configure Judge0 variables separately if Compile & Run is needed. Render free web services sleep after 15 minutes of inactivity and may take about a minute to wake. Add your GitHub Copilot fine-grained token as the Render `COPILOT_GITHUB_TOKEN` secret; the Blueprint prompts for it without putting it in source control.
