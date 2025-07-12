### Core Integration: `FunASRModel`

The integration of FunASR is primarily implemented in the `FunASRModel` class within `nextalk_server/funasr_model.py`. This class handles:

- **Model Loading & Management**: Dynamically loads and initializes ASR, VAD and punctuation models based on server configuration
- **Configuration-Driven**: Supports specifying model name, device (CPU/CUDA), model version (`model_revision`) via config files
- **Async Processing**: Uses `ThreadPoolExecutor` to offload compute-intensive operations to worker threads, preventing blocking of server's async event loop
- **Model Warmup & Preloading**:
  - **Warmup**: After initialization, tests all model components with short test data to reduce first-request latency
  - **Preloading**: `scripts/run_server.py` supports fully initializing `FunASRModel` instance before uvicorn server starts via `set_preloaded_model`, significantly reducing model loading time after server startup
- **Streaming Recognition**: Provides `process_audio_chunk` method for real-time audio streams
- **Offline Recognition**: Provides `process_audio_offline` method for complete audio clips
- **Resource Management**: Provides `release` method to free model resources during server shutdown

### Model Caching & Download

FunASR models are automatically downloaded from default ModelScope source (or other configured sources like HuggingFace) to local cache directory upon first use. Default cache path is typically `~/.cache/modelscope/hub` or similar. Cache behavior can be modified via FunASR environment variables (e.g. `MODELSCOPE_CACHE`). The `scripts/run_server.py` script may specify model search path via `--model-path` argument, or set model source via `MODEL_HUB` environment variable (e.g. `modelscope` or `hf`).

### Testing FunASR Features

When testing FunASR-related features, note:
- Ensure FunASR and its dependencies are properly installed in dev environment
- Server config files (`config/default_config.ini` or `~/.config/nextalk/config.ini`) point to correct, accessible model names
- If using GPU (`device=cuda`), ensure CUDA environment is properly configured and compatible with FunASR's PyTorch version

## Troubleshooting

### Common Development Issues

1. **Test Timeout Issues**
   - For WebSocket tests, may need to increase timeout
   - Use `@pytest.mark.asyncio(timeout=10)` to set longer timeout

2. **GPU Memory Issues**
   - If encountering GPU OOM during development, set `device=cpu` in config
   - Or use smaller models (e.g. `tiny.en` or `SenseVoiceSmall`) for development

3. **Audio Device Permission Issues**
   - Ensure user is in `audio` group
   - Verify device access with `aplay -l` and `arecord -l`

4. **FunASR Related Issues**
   - For ImportError, ensure funasr is installed: `pip install funasr`
   - For model download issues, manually download models to `~/.cache/NexTalk/funasr_models`
   - FunASR models may auto-download on first use - ensure stable network connection
   - When using `ASRRecognizer` class, check imports to avoid forcing FunASR dependency

### Debugging Tips

- Use standard `logging` module for detailed logging
- Set `LOG_LEVEL=DEBUG` on server side
- Launch client with `--debug` flag for verbose logging
- For WebSocket issues, use browser dev tools network panel
- For FunASR issues, set `FUNASR_LOG_LEVEL=DEBUG` for detailed model logs

## Packaging & Distribution

NexTalk provides PyInstaller scripts to package client and server as standalone executables.

### Prerequisites

- Ensure `PyInstaller` is installed. If not, run in your virtual environment:
```bash
pip install pyinstaller
```

### Packaging Script

The `scripts/build_package.sh` script in project root handles packaging.

### Packaging Client Only

To package just the client:

```bash
cd /path/to/nextalk  # Navigate to project root
bash scripts/build_package.sh
```

This will:
1. Create `nextalk_client` executable in `dist/` directory
2. Package client as single-file, windowed application
3. Include resources from `src/nextalk_client/ui/assets`
4. Copy default config `config/default_config.ini` to `dist/config/`
5. Generate basic `README.txt` in `dist/`

### Packaging Client & Server

To package both client and server:

```bash
cd /path/to/nextalk  # Navigate to project root
bash scripts/build_package.sh --with-server
```

This will additionally create `nextalk_server` executable in `dist/`.

### Output

All generated files are located in `dist/` directory after packaging.

**Note**: Packaging depends on current Python environment and installed libraries. Ensure running script in correct virtual environment with all runtime dependencies.