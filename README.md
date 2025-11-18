# rest-latex

Small FastAPI service that compiles uploaded LaTeX sources into PDFs inside a compact Alpine container. Ship LaTeX builds without needing a full TeX distribution on the host.

## Overview
- One POST endpoint that turns uploaded `.tex` sources (plus optional assets) into a PDF.
- Ships with Tectonic by default; swap engines with an environment variable.
- Alpine-based image sized for CI/CD pipelines and short-lived jobs.

## Requirements
- Docker 20.10 or newer.
- curl (or any HTTP client) for testing the API.

## Quick start
1. Build the container: `docker build -t rest-latex .`
2. Run the API on port 8080: `docker run --rm -p 8080:8080 rest-latex`
3. Optional: prefer LuaLaTeX builds by setting `LATEX_ENGINE=lualatex` in the `docker run` command.

## API

### POST `/compile`

**Form fields**
- `tex_file` *(required)*: the LaTeX source file to compile.
- `assets_archive` *(optional)*: ZIP file containing figures/fonts referenced by the source.

**Examples**

Compile a standalone `.tex`:

```bash
curl \
  -X POST \
  -F "tex_file=@examples/sample.tex" \
  http://localhost:8080/compile \
  -o output.pdf
```

Compile with external assets:

```bash
curl \
  -X POST \
  -F "tex_file=@examples/sample_with_images.tex" \
  -F "assets_archive=@examples/assets.zip" \
  http://localhost:8080/compile \
  -o output.pdf
```

The service responds with a PDF attachment on success or JSON containing `stdout`/`stderr` when compilation fails.

### GET `/health`

```bash
curl http://localhost:8080/health
```

Returns HTTP 200 and `{"status":"ok"}` when the API is ready to accept work.

## Environment

All settings have defaults so the container works out-of-the-box:

| Variable | Default | Purpose |
| --- | --- | --- |
| `LATEX_ENGINE` | `tectonic` | Binary used to compile LaTeX (`tectonic`, `lualatex`, etc.). |
| `LATEX_TIMEOUT_SECONDS` | `60` | Maximum seconds allowed for a compilation run. |
| `LATEX_MAIN_FILENAME` | `main.tex` | Target filename used when saving the uploaded LaTeX source. |
| `TECTONIC_CACHE_DIR` | `/tmp/tectonic-cache` | Storage for cached LaTeX packages fetched by Tectonic. |

## Troubleshooting
- Inspect the JSON error response for the captured compiler logs when a build fails.
- Ensure uploaded ZIP files do not contain paths that escape the working directory; such entries are rejected for safety.
- Switch to `LATEX_ENGINE=lualatex` when your document depends on LuaTeX-only packages (e.g., `luacode`).
