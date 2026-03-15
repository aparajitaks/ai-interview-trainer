Why Whisper is handled separately

The `openai-whisper` package is a source distribution that may require build-time tooling and a packaging environment that provides `pkg_resources` (part of setuptools). On macOS (especially arm64) this can fail inside pip's isolated build environment.

Recommended installation options

1) Quick: install from the GitHub repo (may still build from source):

```bash
source .venv/bin/activate
pip install --upgrade pip setuptools wheel setuptools_scm
pip install git+https://github.com/openai/whisper.git
```

2) Use Conda (recommended on macOS for complex audio/C extensions)

```bash
conda create -n ai-interview-trainer python=3.10
conda activate ai-interview-trainer
pip install -r requirements.txt  # with openai-whisper commented out
pip install git+https://github.com/openai/whisper.git
```

3) If pip build still fails
- Ensure Xcode command line tools are installed: `xcode-select --install`
- Ensure `pip`, `setuptools`, `wheel`, and `setuptools_scm` are upgraded in the environment before installing Whisper.
- As a last resort, install Whisper in a separate environment (conda) or on an x86 mac where prebuilt wheels may be available.

Notes
- If you need Whisper features (transcription, etc.) in this repo, follow the steps above after finishing the other dependencies.
- If you want, I can try installing Whisper in your environment and debug further — say "debug whisper" and I'll run a verbose install and attempt fixes.
