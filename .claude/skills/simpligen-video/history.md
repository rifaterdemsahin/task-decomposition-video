# simpligen: start to end

How the proof of concept was built, version by version, 23 Nov 2026 on an Apple M1 Max (64 GB).
Each row is a git tag on https://github.com/rifaterdemsahin/simpligen.

| Version | Commit | Added | Measured |
|---|---|---|---|
| (PoC) | `52982ca` | JSON → MP4 renderer (Pillow + macOS `say` + ffmpeg), first demo video, cost doc, HyperFrames comparison, Fly.io app `simpligen-poc` | 42.7 s video in 11.6 s |
| v0.2.0 | `32316e6` | Kokoro-82M TTS in local Docker (`:8880`) with fallback to say/espeak, SVG diagram per scene, version on slides | 63.7 s video in ~31 s (78 s with Kokoro cold) |
| v0.2.1 | `7bbd862` | Emoji menu on all pages, `site/images.html` (which local image model to use, what to load) with 4 SVG diagrams | n/a |
| v0.3.0 | `0105231` | mflux + FLUX.2 Klein 4B installed; `tools/gen_images.py` (Ollama gemma3:12b prompts → mflux PNGs); per-scene `image` + `emoji`; `site/gallery.html` | 34 s/image avg, 9.3 GB peak; 75.7 s video in 44 s |
| v0.4.0 | `3cad366` | `simpligen/animate.py` animated intro; same intro as a HyperFrames composition (not rendered); "Same intro, two ways" scene; `site/architecture.html` | ~50 ms per 1080p frame; 2:03 video in 95–160 s |

## Decisions and why

- **Pillow + ffmpeg, not a headless browser:** small footprint, so it can run next to a 9 GB image model and Kokoro. HyperFrames is the richer alternative for motion design.
- **JSON, not YAML:** PyYAML wasn't installed, and JSON needs no dependency.
- **Images as a separate step:** they're the slowest part (~34 s each), so they're generated once and committed. Re-rendering after a narration change only takes step 3.
- **Ollama for prompts, not LM Studio:** the LM Studio server on this Mac requires an API token, and Ollama on localhost doesn't.
- **mflux, not Ollama, for images:** Ollama 0.40.16 rejects image models.
- **Fly.io serves static files only:** no model or key runs in the cloud. One shared-cpu-1x 256 MB machine with auto-stop costs $0–2.19 a month.

## Installed along the way

| Tool | How | Size |
|---|---|---|
| mflux | `uv tool install mflux` | CLI |
| FLUX.2 Klein 4B | first `mflux-generate-flux2 --model flux2-klein-4b` run | ~15 GB (`~/.cache/huggingface`) |
| Ollama `x/z-image-turbo` | `ollama pull x/z-image-turbo` | 12 GB, unusable on Ollama 0.40.16 (`ollama rm x/z-image-turbo` to free it) |
| Kokoro | already running: `ghcr.io/remsky/kokoro-fastapi-cpu` (see `docker-compose.yml`) | 5.6 GB image |
