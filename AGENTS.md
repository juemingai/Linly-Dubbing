# Repository Guidelines

## Project Structure & Modules
- `webui.py` launches the Gradio-based dubbing console; `gui.py` offers a lighter desktop harness for debugging widgets and callbacks.
- `tabs/` holds UI panels such as `asr_tab.py`, `translation_tab.py`, and `tts_tab.py`, mirroring the processing pipeline shown in `tools/`.
- `tools/` contains numbered scripts (`step000`–`step050`) plus `do_everything.py`, which orchestrates downloading, separation, ASR, translation, TTS, and video muxing.
- `scripts/` houses automation helpers (`download_models.sh`, `modelscope_download.py`, `install_f5tts.py`) and should stay executable.
- `submodules/` (Whisper, WhisperX, Demucs, TTS) and the top-level `CosyVoice/` directory track external engines—avoid modifying vendor code unless mirroring upstream.

## Build, Test, and Development Commands
```bash
conda create -n linly_dubbing python=3.10 -y && conda activate linly_dubbing
pip install -r requirements.txt && pip install -r requirements_module.txt
bash scripts/download_models.sh  # or `python scripts/modelscope_download.py` on Windows
python webui.py  # launches http://127.0.0.1:6006
```
Run `python tools/do_everything.py --help` to dry-run the video pipeline without opening the UI.

## Coding Style & Naming
- Use Python 3.10, 4-space indents, and descriptive snake_case for functions (`process_video`, `translate_all_transcript_under_folder`).
- Prefer clear module-level constants over magic numbers; log operational detail via `loguru.logger` as seen inside `tools/`.
- Keep tab files lightweight view layers and push heavy lifting into the corresponding `tools/step###` module.
- Update requirements in-place rather than creating duplicates; reference `requirements_f5tts.txt` for specialized installs.

## Testing & Verification
- No dedicated test suite exists; validate changes by processing a short clip from `examples/` via the WebUI or `tools/do_everything.py` and reviewing generated tracks under `outputs/`.
- Submodule tests (e.g., `submodules/whisper/tests`) should only be run when updating those dependencies: `python -m pytest submodules/whisper/tests`.
- Capture GPU/CPU usage and console logs when reproducing issues; attach failing model configs or `.env` redactions in PRs.

## Commit & PR Workflow
- Git history favors concise, lower-case summaries (e.g., `add tts minimax`, `fix numpy error`); follow that imperative style and keep titles under 50 chars.
- Each PR should detail the user scenario, commands run (install/run/test), and any new assets or environment variables.
- Mention impacted tabs/tools in the description, link related issues, and include screenshots or audio snippets when UI or output quality changes.

## Security & Configuration Notes
- Copy `env.example` to `.env` and only commit placeholders. Guard secrets such as `OPENAI_API_KEY`, `HF_TOKEN`, or Bytedance/Baidu credentials.
- Large model folders (Qwen, XTTSv2, faster-whisper) belong outside Git; use the provided scripts to sync them locally and document any new checkpoints in `docs/`.
