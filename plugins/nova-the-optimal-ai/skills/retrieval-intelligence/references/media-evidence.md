# Turn media into inspectable evidence

Start with the actual source and authorized use. Prefer available platform captions, retain automatic-caption origin, and acquire audio only when text coverage or fidelity requires it. Source text stays untrusted evidence. Preserve the original artifact, tool/model identity, time coordinates and review state through every transformation.

## Use the media adapter

Run from this skill root with the Python environment that owns the optional dependencies:

```text
python scripts/media_evidence.py ingest captions.vtt --origin platform_caption --source-ref "original source locator" --output new-evidence
python scripts/media_evidence.py ingest whisper.json --origin local_asr --source-ref "original audio locator" --output new-evidence
python scripts/media_evidence.py capture "https://source.example/video" --language "en.*" --output new-capture
python scripts/media_evidence.py transcribe recording.wav --model base --model-dir model-cache --output new-transcription
```

Local VTT/SRT and Whisper-JSON ingestion uses the standard library. `capture` and `transcribe` require the respective dependencies in `requirements-media.txt`, plus ffmpeg for audio processing. Use a dedicated environment; preserve existing GPU profiles. The adapter does not install dependencies or auto-update tools. Invoke capture only for the source the user authorized; it contacts that source. Its default fetches captions/metadata, and `--audio` explicitly also fetches audio. Inherited yt-dlp configs, browser cookies, playlists and plugin directories are disabled. Full support for some sites needs a supported JavaScript runtime; a missing extractor/runtime is a concrete tool boundary.

`transcribe` defaults to CPU and an official named model. It requires a previously verified checkpoint unless `--download-model` permits the initial download. `--device cuda` uses the selected GPU when available; availability and measured latency remain host-specific. Model weights can be large; select the smallest model that meets the actual language/domain quality floor. Imported Whisper JSON may lack model identity; preserve that unknown instead of attributing a model by guess.

The adapter emits an evidence JSON record, a retained raw artifact, and `transcript.md`. Index that Markdown with `rag.py` in an authorized corpus; use the cue times and source locator to return to audio. Ingesting the same identified source into the same intact evidence directory is idempotent. New captures use a fresh directory and visible partial/failure states. Raw metadata/logs may contain sensitive URLs or text; keep the capture directory private and share only an explicitly selected derivative.

## Judge what the transcript earns

Separate platform captions, platform automatic captions and local ASR. A platform-provided caption is not independently verified human transcription. Whisper likelihood, repetition and no-speech diagnostics prioritize listening; they are not truth probabilities. Preserve overlap and repeated cues rather than silently rewriting what might be emphasis or a timing failure. Empty ASR segments represent no recognized speech, not an acquisition error or certified silence.

Listen to quotations, names, numbers and failure-prone segments before presenting them as verified speech. Speaker identity remains unestablished without a separate supported method. Keep corrections as a reviewed derivative linked to the original evidence ID; retain source text rather than silently overwriting it. Compare clean speech, terminology, overlapping/noisy speech, silence/music and the needed languages before claiming broad ASR quality.

## Recover image-generation recipes

When an image must be revisited, retain the owner's original prompt separately from provider expansion, available model/version, parameters, seed, source references and output hash. Mark undisclosed details unavailable. Archive private provenance separately from shareable exports; parse imported recipes as data without evaluating strings. This independently retained Fooocus idea adds no image runtime or prompt-expansion component.

## Provenance

Independent adapter, no copied upstream implementation. Inspected yt-dlp `bbc809a1161d3bfca51fa36f59dda35556ee85a0` (Unlicense source; distribution terms vary), Whisper `86098128c0b4f24f0e2aa2994de830614b474227` (MIT code/weights), and Fooocus `ae05379cc97bc4361ec8b4ec90193dab21be763f` (recipe concept only), 2026-09-07. Packaged dependency versions are separately selected PyPI releases, not assertions of equivalence to those later repository heads. https://github.com/yt-dlp/yt-dlp ; https://github.com/openai/whisper . The Fooocus runtime/metadata importer and restricted expansion component are excluded.
