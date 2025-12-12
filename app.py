from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import CodeSubmission, ExecutionResult
from executor import CodeExecutor
import threading

app = FastAPI(title="Remote Code Executor")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = CodeExecutor()

@app.post("/execute", response_model=dict)
async def execute_code(submission: CodeSubmission):
    """Submit code for execution"""
    # Run execution in background thread to not block API
    execution_id = executor.execute(submission.code, submission.timeout)
    
    return {
        "execution_id": execution_id,
        "message": "Code submitted for execution"
    }

@app.get("/status/{execution_id}", response_model=ExecutionResult)
async def get_status(execution_id: str):
    """Get execution status"""
    result = executor.get_status(execution_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    return result

@app.get("/")
async def root():
    return {
        "message": "Remote Code Executor API",
        "endpoints": {
            "POST /execute": "Submit code for execution",
            "GET /status/{id}": "Get execution status"
        }
    }