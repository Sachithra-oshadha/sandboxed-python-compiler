# Safe sandboxed execution with real-time status monitoring

## What this project does

It lets a user:
1. Write Python code in a web browser
2. Click “Run Code”
3. Have the code executed safely on the server
4. See the output, errors, and execution status in real time

All of this happens without running the code directly on the server or the user’s machine, which keeps things secure.

## How it works
1. Frontend (index.html)
    * A web page with a code editor (Monaco Editor, like VS Code).
    * The user writes Python code and sets a time limit.
    * When “Run Code” is clicked:
    * The code is sent to the backend using an API request.
    * The page keeps checking the execution status and displays:

    Output
    * Errors
    * Execution time
    * Number of lines of code

2. Backend API (FastAPI)
    * Built using FastAPI (Python).
    * Exposes two main endpoints:
    * POST /execute → accepts Python code and starts execution
    * GET /status/{id} → returns execution status and results
    * The API does not run code directly.
    * Instead, it delegates execution to a sandbox.

3. Secure Sandbox Execution (Docker)
    * Each code submission runs inside a temporary Docker container.
    * The container:
        * Has limited memory and CPU
        * Has no internet access
        * Is destroyed after execution
    * This prevents:
        * System damage
        * Infinite loops
        * Access to server files or network

4. Execution Tracking
    * Every code run gets a unique execution ID.
    * The system tracks:
    * Status (pending, running, completed, failed, timeout)
    * Output and errors
    * Execution time
    * Start time
    * The frontend polls the backend to show real-time updates.

# Future Improvements

* File uploads for better usability