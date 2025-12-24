import os
import shutil
import docker
import time
import uuid
import tarfile
import io
from datetime import datetime
from models import ExecutionStatus, ExecutionResult


class CodeExecutor:
    def __init__(self):
        self.client = docker.from_env()
        self.executions = {}  # In-memory storage

    def _escape_code(self, code: str) -> str:
        """Safely escape code for python -c."""
        return code.replace("'", "'\"'\"'")

    def _count_lines(self, path):
        total = 0
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".py"):
                    with open(os.path.join(root, f)) as file:
                        total += sum(1 for _ in file)
        return total

    def execute(self, code: str, timeout: int = 10):
        execution_id = str(uuid.uuid4())
        escaped_code = self._escape_code(code)
        lines_of_code = len([l for l in code.split("\n") if l.strip()])

        # Initialize execution record
        self.executions[execution_id] = {
            "status": ExecutionStatus.PENDING,
            "start_time": datetime.now(),
            "lines_of_code": lines_of_code,
            "output": "",
            "error": "",
            "execution_time": None,
        }

        container = None

        try:
            # Mark as running
            self.executions[execution_id]["status"] = ExecutionStatus.RUNNING

            # Start sandbox container (do not auto-remove)
            container = self.client.containers.run(
                "python-sandbox:latest",                   # custom sandbox
                f"python -c '{escaped_code}'",
                detach=True,
                mem_limit="50m",
                cpu_period=100000,
                cpu_quota=50000,
                network_disabled=True,
                remove=False
            )

            # Wait with timeout
            start = time.time()
            result = container.wait(timeout=timeout)
            exec_time = time.time() - start

            # Read logs BEFORE removal
            try:
                logs = container.logs(stdout=True, stderr=True).decode("utf-8")
            except Exception:
                logs = "[logs unavailable]"

            # Save success result
            self.executions[execution_id].update({
                "status": ExecutionStatus.COMPLETED,
                "output": logs,
                "execution_time": exec_time
            })

        except docker.errors.ContainerError as e:
            self.executions[execution_id].update({
                "status": ExecutionStatus.FAILED,
                "error": str(e)
            })

        except docker.errors.APIError as e:
            # Timeout or Docker-level error
            is_timeout = "timeout" in str(e).lower()
            self.executions[execution_id].update({
                "status": ExecutionStatus.TIMEOUT if is_timeout else ExecutionStatus.FAILED,
                "error": str(e)
            })

        except Exception as e:
            # Any other error
            is_timeout = "timeout" in str(e).lower()
            self.executions[execution_id].update({
                "status": ExecutionStatus.TIMEOUT if is_timeout else ExecutionStatus.FAILED,
                "error": str(e)
            })

        finally:
            # ALWAYS clean up the container if it exists
            if container:
                try:
                    container.remove(force=True)
                except Exception:
                    pass

        return execution_id

    

    def execute_project(self, project_path: str, entry_file: str, timeout: int):
        execution_id = str(uuid.uuid4())

        self.executions[execution_id] = {
            "status": ExecutionStatus.PENDING,
            "start_time": datetime.now(),
            "lines_of_code": self._count_lines(project_path),
            "output": "",
            "error": "",
            "execution_time": None,
        }

        container = None

        try:
            self.executions[execution_id]["status"] = ExecutionStatus.RUNNING

            # 1️⃣ Create container (do NOT start yet)
            container = self.client.containers.create(
                image="python-sandbox:latest",
                command=["python", entry_file],
                working_dir="/workspace",
                mem_limit="100m",
                network_disabled=True,
                detach=True
            )

            # 2️⃣ Tar project directory
            tar_stream = io.BytesIO()
            with tarfile.open(fileobj=tar_stream, mode="w") as tar:
                tar.add(project_path, arcname=".")

            tar_stream.seek(0)

            # 3️⃣ Copy files into container
            container.put_archive("/workspace", tar_stream)

            # 4️⃣ Start container
            start = time.time()
            container.start()
            container.wait(timeout=timeout)
            exec_time = time.time() - start

            logs = container.logs(stdout=True, stderr=True).decode()

            self.executions[execution_id].update({
                "status": ExecutionStatus.COMPLETED,
                "output": logs,
                "execution_time": exec_time
            })

        except Exception as e:
            self.executions[execution_id].update({
                "status": ExecutionStatus.FAILED,
                "error": str(e)
            })

        finally:
            if container:
                container.remove(force=True)
            shutil.rmtree(project_path, ignore_errors=True)

        return execution_id

    def get_status(self, execution_id: str):
        if execution_id not in self.executions:
            return None

        exec_data = self.executions[execution_id]
        time_running = (datetime.now() - exec_data["start_time"]).total_seconds()

        return ExecutionResult(
            execution_id=execution_id,
            status=exec_data["status"],
            output=exec_data.get("output", ""),
            error=exec_data.get("error", ""),
            start_time=exec_data["start_time"],
            execution_time=exec_data.get("execution_time", time_running),
            lines_of_code=exec_data["lines_of_code"],
        )
