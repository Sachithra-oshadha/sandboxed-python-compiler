const API_URL = 'http://localhost:8000';
let editor;
let currentExecutionId = null;
let statusInterval = null;

// Initialize Monaco Editor
require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }});

require(['vs/editor/editor.main'], function() {
    editor = monaco.editor.create(document.getElementById('editor'), {
        value: `# Welcome to Python Online Compiler!
# Write your Python code here and click "Run Code"

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 fibonacci numbers
for i in range(10):
    print(f"F({i}) = {fibonacci(i)}")

print("\\nExecution completed!")`,
        language: 'python',
        theme: 'vs-dark',
        fontSize: 14,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        automaticLayout: true
    });
});

async function checkStatus() {
    if (!currentExecutionId) return;

    try {
        const response = await fetch(`${API_URL}/status/${currentExecutionId}`);

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const status = await response.json();

        updateStatusBar(status);

        // When execution finishes
        if (
            status.status === "completed" ||
            status.status === "failed" ||
            status.status === "timeout"
        ) {
            clearInterval(statusInterval);

            if (status.output) {
                showOutput("\n📋 --- Output ---", "info");
                showOutput(status.output, "success");
            }

            if (status.error) {
                showOutput("\n⚠️ --- Error ---", "error");
                showOutput(status.error, "error");
            }

            if (status.status === "timeout") {
                showOutput("\n⏱️ Execution timed out!", "error");
            }

            const runBtn = document.getElementById("runBtn");
            runBtn.disabled = false;
            runBtn.innerHTML = "▶ Run Code";
        }
    } catch (error) {
        clearInterval(statusInterval);
        showOutput(`❌ Status check error: ${error.message}`, "error");

        const runBtn = document.getElementById("runBtn");
        runBtn.disabled = false;
        runBtn.innerHTML = "▶ Run Code";
    }
}

function updateSelectedFiles() {
    const input = document.getElementById("fileInput");
    const files = input.files;
    const list = document.getElementById("fileList");
    const entryInput = document.getElementById("entryFile");

    if (!files.length) {
        list.textContent = "No files selected";
        return;
    }

    list.textContent = "Files: " + [...files].map(f => f.name).join(", ");

    // ✅ Auto-pick main.py if exists, else first file
    const mainFile = [...files].find(f => f.name === "main.py");
    entryInput.value = mainFile ? "main.py" : files[0].name;
}


function runCode() {
    const files = document.getElementById("fileInput").files;

    if (files.length > 0) {
        runProject();
    } else {
        runCodeOnly();
    }
}

async function runCodeOnly()  {
    const code = editor.getValue();
    const timeout = parseInt(document.getElementById('timeout').value);
    const runBtn = document.getElementById('runBtn');
    
    if (!code.trim()) {
        alert('Please write some code first!');
        return;
    }

    // Clear previous execution
    if (statusInterval) {
        clearInterval(statusInterval);
    }

    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="loading"></span> Running...';
    
    clearOutput();
    showOutput('🚀 Submitting code for execution...', 'info');

    try {
        // Submit code
        const response = await fetch(`${API_URL}/execute`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, timeout })
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();
        currentExecutionId = result.execution_id;

        showOutput(`✓ Execution started (ID: ${result.execution_id})`, 'success');
        
        // Show status bar
        document.getElementById('statusBar').style.display = 'grid';

        // Poll for status
        statusInterval = setInterval(checkStatus, 500);

    } catch (error) {
        showOutput(`\n❌ Error: ${error.message}`, 'error');
        showOutput('\n💡 Make sure your backend is running on http://localhost:8000', 'info');
        runBtn.disabled = false;
        runBtn.innerHTML = '▶ Run Code';
    }
}

async function runProject() {
    const files = document.getElementById("fileInput").files;
    const entryFile = document.getElementById("entryFile").value;
    const timeout = document.getElementById("timeout").value;
    const runBtn = document.getElementById("runBtn");

    if (!files.length) {
        alert("Please upload Python files");
        return;
    }

    runBtn.disabled = true;
    runBtn.innerHTML = '<span class="loading"></span> Running...';

    clearOutput();
    showOutput("📦 Uploading project files...", "info");

    const formData = new FormData();

    for (const file of files) {
        formData.append("files", file);
    }

    formData.append("entry_file", entryFile);
    formData.append("timeout", timeout);

    try {
        const response = await fetch(`${API_URL}/execute-with-files`, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        currentExecutionId = result.execution_id;

        showOutput(`✓ Project execution started (ID: ${currentExecutionId})`, "success");
        document.getElementById("statusBar").style.display = "grid";

        statusInterval = setInterval(checkStatus, 500);

    } catch (error) {
        showOutput(`❌ Error: ${error.message}`, "error");
        runBtn.disabled = false;
        runBtn.innerHTML = "▶ Run Code";
    }
}

function updateStatusBar(status) {
    const statusValue = document.getElementById('statusValue');
    statusValue.textContent = status.status.toUpperCase();
    statusValue.className = `status-value status-${status.status}`;

    document.getElementById('linesValue').textContent = status.lines_of_code || 0;
    
    const timeRunning = status.execution_time || 
                        (new Date() - new Date(status.start_time)) / 1000;
    document.getElementById('timeValue').textContent = timeRunning.toFixed(2) + 's';
    
    if (status.start_time) {
        const startTime = new Date(status.start_time);
        document.getElementById('startValue').textContent = startTime.toLocaleTimeString();
    }
}

function showOutput(text, type = 'info') {
    const output = document.getElementById('output');
    if (output.querySelector('.output-line') === null && output.textContent.includes('Output will appear here')) {
        output.innerHTML = '';
    }
    
    const line = document.createElement('div');
    line.className = `output-line output-${type}`;
    line.textContent = text;
    output.appendChild(line);
    output.scrollTop = output.scrollHeight;
}

function clearOutput() {
    document.getElementById('output').innerHTML = '<div style="color: #888;">Output will appear here...</div>';
    document.getElementById('statusBar').style.display = 'none';
}

function clearEditor() {
    if (confirm('Are you sure you want to clear the editor?')) {
        editor.setValue('');
        editor.focus();
    }
}