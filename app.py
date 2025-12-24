from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from models import CodeSubmission, ExecutionResult
from executor import CodeExecutor
import tempfile
import os
import shutil
from pathlib import Path

app = FastAPI(title="Remote Code Executor")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = CodeExecutor()


@app.post("/execute", response_model=dict)
async def execute_code(submission: CodeSubmission):
    """
    Execute single Python code snippet
    """
    execution_id = executor.execute(
        code=submission.code,
        timeout=submission.timeout
    )

    return {
        "execution_id": execution_id,
        "message": "Code submitted for execution"
    }


@app.post("/execute-with-files", response_model=dict)
async def execute_with_files(
    files: List[UploadFile] = File(...),
    entry_file: str = Form(...),
    timeout: int = Form(30),
):
    """
    Execute uploaded Python project (mounted as /workspace in Docker)
    """

    # 1️⃣ Create temp directory on HOST
    project_path = Path(tempfile.mkdtemp(prefix="exec_"))

    try:
        # 2️⃣ Save uploaded files into project directory
        for file in files:
            # Normalize filename (prevents ../ attacks)
            safe_name = Path(file.filename).name
            file_path = project_path / safe_name

            with open(file_path, "wb") as f:
                f.write(await file.read())

        # 3️⃣ Validate entry file exists
        uploaded_files = [Path(f.filename).name for f in files]

        if entry_file not in uploaded_files:
            raise HTTPException(
                status_code=400,
                detail=f"Entry file '{entry_file}' not among uploaded files: {uploaded_files}"
            )

        # 4️⃣ Execute project
        execution_id = executor.execute_project(
            project_path=str(project_path),   # mounted as /workspace
            entry_file=entry_file,
            timeout=timeout
        )

        return {
            "execution_id": execution_id,
            "message": "Project submitted for execution"
        }

    except HTTPException:
        shutil.rmtree(project_path, ignore_errors=True)
        raise

    except Exception as e:
        shutil.rmtree(project_path, ignore_errors=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/{execution_id}", response_model=ExecutionResult)
async def get_status(execution_id: str):
    """
    Get execution status
    """
    result = executor.get_status(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result


@app.get("/")
async def root():
    return {
        "message": "Remote Code Executor API",
        "endpoints": {
            "POST /execute": "Submit single-file code",
            "POST /execute-with-files": "Submit multi-file project",
            "GET /status/{id}": "Get execution status",
        },
    }
