from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import zipfile
from typing import Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response


@dataclass
class ServiceSettings:
    latex_engine: str
    latex_timeout_seconds: int
    latex_main_filename: str
    tectonic_cache_dir: Path


def load_settings() -> ServiceSettings:
    """This function loads environment configuration by reading variables with sane defaults."""
    latex_engine = os.getenv("LATEX_ENGINE", "tectonic")
    latex_timeout_seconds = int(os.getenv("LATEX_TIMEOUT_SECONDS", "60"))
    latex_main_filename = os.getenv("LATEX_MAIN_FILENAME", "main.tex")
    tectonic_cache_dir = Path(os.getenv("TECTONIC_CACHE_DIR", "/tmp/tectonic-cache"))
    return ServiceSettings(
        latex_engine=latex_engine,
        latex_timeout_seconds=latex_timeout_seconds,
        latex_main_filename=latex_main_filename,
        tectonic_cache_dir=tectonic_cache_dir,
    )


settings = load_settings()
settings.tectonic_cache_dir.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="rest-latex", version="1.0.0")


def create_work_dir() -> Path:
    """This function creates an isolated working directory by delegating to tempfile.mkdtemp."""
    return Path(tempfile.mkdtemp(prefix="latexwork_"))


async def save_upload_file(upload: UploadFile, destination: Path) -> None:
    """This function saves an uploaded file to disk by reading its body and writing bytes."""
    contents = await upload.read()
    destination.write_bytes(contents)


def ensure_tex_extension(filename: Optional[str]) -> None:
    """This function validates the LaTeX filename by confirming it ends with a .tex suffix."""
    if not filename or not filename.lower().endswith(".tex"):
        raise HTTPException(status_code=400, detail="Uploaded file must have a .tex extension.")


def ensure_zip_is_valid(zip_path: Path) -> None:
    """This function validates the archive by checking it is a readable ZIP file."""
    if not zipfile.is_zipfile(zip_path):
        raise HTTPException(status_code=400, detail="Provided assets archive is not a valid ZIP file.")


def extract_zip_safely(zip_path: Path, target_dir: Path) -> None:
    """This function extracts asset archives safely by preventing path traversal entries."""
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.infolist():
            resolved_target = (target_dir / member.filename).resolve()
            if not str(resolved_target).startswith(str(target_dir.resolve())):
                raise HTTPException(status_code=400, detail="Archive contains unsafe paths.")
        archive.extractall(target_dir)


def build_engine_command(work_dir: Path, tex_filename: str, current_settings: ServiceSettings) -> list[str]:
    """This function builds the LaTeX command by tailoring flags to the configured engine."""
    engine_name = current_settings.latex_engine.lower()
    if engine_name == "tectonic":
        return [
            current_settings.latex_engine,
            "--synctex=0",
            "--keep-intermediates",
            "--keep-logs",
            "--outdir",
            str(work_dir),
            tex_filename,
        ]
    return [
        current_settings.latex_engine,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(work_dir),
        tex_filename,
    ]


def run_latex_engine(work_dir: Path, tex_filename: str, current_settings: ServiceSettings) -> None:
    """This function compiles the LaTeX input by invoking the configured engine via subprocess."""
    command = build_engine_command(work_dir, tex_filename, current_settings)
    environment = os.environ.copy()
    environment.setdefault("TECTONIC_CACHE_DIR", str(current_settings.tectonic_cache_dir))
    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=current_settings.latex_timeout_seconds,
            env=environment,
            check=False,
        )
    except FileNotFoundError as error:
        raise HTTPException(status_code=500, detail="LaTeX engine executable not found.") from error
    except subprocess.TimeoutExpired as error:
        raise HTTPException(status_code=504, detail="LaTeX compilation timed out.") from error

    if completed.returncode != 0:
        detail = {
            "message": "LaTeX compilation failed.",
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        raise HTTPException(status_code=400, detail=detail)


def build_pdf_response(pdf_path: Path) -> Response:
    """This function prepares the successful PDF response by reading bytes and setting headers."""
    pdf_bytes = pdf_path.read_bytes()
    headers = {
        "Content-Disposition": f'attachment; filename="{pdf_path.name}"',
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@app.post("/compile")
async def compile_latex(tex_file: UploadFile = File(...), assets_archive: Optional[UploadFile] = File(None)) -> Response:
    """This function handles compilation requests by saving inputs, invoking the engine, and returning PDFs."""
    ensure_tex_extension(tex_file.filename)
    work_dir = create_work_dir()
    tex_path = work_dir / settings.latex_main_filename

    try:
        await save_upload_file(tex_file, tex_path)

        if assets_archive and assets_archive.filename:
            archive_path = work_dir / "assets.zip"
            await save_upload_file(assets_archive, archive_path)
            ensure_zip_is_valid(archive_path)
            extract_zip_safely(archive_path, work_dir)
            archive_path.unlink(missing_ok=True)

        run_latex_engine(work_dir, tex_path.name, settings)
        pdf_path = tex_path.with_suffix(".pdf")
        if not pdf_path.exists():
            raise HTTPException(status_code=500, detail="PDF output missing after compilation.")
        return build_pdf_response(pdf_path)
    except HTTPException:
        raise
    except Exception as unexpected_error:
        raise HTTPException(status_code=500, detail="Unexpected error during compilation.") from unexpected_error
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


@app.get("/health")
def health() -> Response:
    """This function exposes a health check by returning a simple JSON payload."""
    return Response(content='{"status":"ok"}', media_type="application/json")
