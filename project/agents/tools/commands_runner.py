"""Runs command in an isolated environments"""

import io
import os
import tarfile
import tempfile
import subprocess
import docker
from docker.errors import ContainerError, ImageNotFound, APIError

class CommandCentre:
    def __init__(self, command, reason):
        self.command = command
        self.reason = reason

    def validate_reason(self):
        # checks the reason it wants to run a command 
        if not self.reason or not isinstance(self.reason, str):
            return False
        return True

    def validate_command(self):
        if not self.command:
            return False
        return True

    def run_command(self):
        pass



def check_docker_daemon() -> bool:
    """Uses subprocess to verify the Docker CLI and daemon are responsive."""
    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _copy_file_to_container(container, local_file_path: str, dest_dir: str = "/workspace") -> None:
    """Packages a local file into an in-memory tar archive and injects it into the container."""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        tar.add(local_file_path, arcname=os.path.basename(local_file_path))
    tar_stream.seek(0)
    container.put_archive(dest_dir, tar_stream)


def run_shell_command(command: str, image: str = "python:3.11-slim", timeout_sec: int = 30) -> str:
    """
    Executes a bash command inside an isolated, ephemeral Docker container.
    Automatically removes the container after execution.
    """
    if not check_docker_daemon():
        return "Error: Docker daemon is not running or Docker CLI is not installed."

    client = docker.from_env()
    try:
        # Ensure image exists locally
        try:
            client.images.get(image)
        except ImageNotFound:
            client.images.pull(image)

        # Run container with strict resource and network limits for safety
        output = client.containers.run(
            image=image,
            command=["/bin/sh", "-c", command],
            remove=True,
            mem_limit="512m",
            network_mode="none",  # Disable internet access inside sandbox (change to 'bridge' if pip install is needed)
            stdout=True,
            stderr=True,
        )
        return output.decode("utf-8").strip() or "Command executed successfully with no output."

    except ContainerError as e:
        return f"Command failed (Exit Code {e.exit_status}):\n{e.stderr.decode('utf-8')}"
    except APIError as e:
        return f"Docker API Error: {str(e)}"
    except Exception as e:
        return f"Execution Error: {str(e)}"


def write_and_execute_python(
    code: str,
    requirements: list[str] | None = None,
    image: str = "python:3.11-slim"
) -> str:
    """
    Writes Python code to a file inside a temporary Docker container,
    installs optional pip packages, executes the script, and returns stdout/stderr.
    """
    if not check_docker_daemon():
        return "Error: Docker daemon is not running or Docker CLI is not installed."

    client = docker.from_env()
    container = None

    try:
        try:
            client.images.get(image)
        except ImageNotFound:
            client.images.pull(image)

        # Enable network only if external packages need to be installed
        net_mode = "bridge" if requirements else "none"

        # Spin up a persistent container for this multi-step task
        container = client.containers.run(
            image=image,
            command="tail -f /dev/null",  # Keep container alive while we copy & run files
            detach=True,
            working_dir="/workspace",
            mem_limit="512m",
            network_mode=net_mode,
        )

        # Create workspace directory inside container
        container.exec_run("mkdir -p /workspace")

        # Write code to a temporary host file and transfer it into the container
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            _copy_file_to_container(container, tmp_path, "/workspace")
            script_name = os.path.basename(tmp_path)
        finally:
            os.remove(tmp_path)

        # Install optional dependencies
        if requirements:
            pkgs = " ".join(requirements)
            pip_res = container.exec_run(f"pip install --quiet {pkgs}")
            if pip_res.exit_code != 0:
                return f"Dependency installation failed:\n{pip_res.output.decode('utf-8')}"

        # Execute the Python script
        exec_res = container.exec_run(f"python /workspace/{script_name}")
        output = exec_res.output.decode("utf-8").strip()

        if exec_res.exit_code != 0:
            return f"Script Error (Exit Code {exec_res.exit_code}):\n{output}"

        return output or "Script executed successfully with no output."

    except Exception as e:
        return f"Sandbox Error: {str(e)}"

    finally:
        # Always clean up the container even if an error occurs
        if container:
            try:
                container.stop(timeout=2)
                container.remove(force=True)
            except Exception:
                pass


# Example usage
if __name__ == "__main__":
    print("--- Testing Shell Command ---")
    print(run_shell_command("uname -a && python --version"))

    print("\n--- Testing Python Code Execution ---")
    sample_code = """
import math
data = [10, 20, 30, 40, 50]
mean = sum(data) / len(data)
print(f"Calculated Mean: {mean}, Sqrt of Mean: {math.sqrt(mean):.2f}")
"""
    print(write_and_execute_python(sample_code))
