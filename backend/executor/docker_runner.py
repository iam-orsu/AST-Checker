"""
Docker Code Execution Engine
Runs user code in isolated Docker sibling containers via the Docker SDK.
Each container is created with strict security constraints:
  --network none  --memory=256m  --cap-drop=ALL  --pids-limit=50
Hard timeout of 5 seconds. Containers are removed after execution.

IMPORTANT: Because the backend runs INSIDE a Docker container, we cannot
volume-mount temp directories (the path exists in the backend container,
not on the host). Instead, we copy files into the container via put_archive.
"""

import io
import os
import re
import tarfile
import time
from typing import Any


# Lazy Docker client — don't crash on import if Docker isn't available
_client = None


def _get_client():
    global _client
    if _client is None:
        import docker
        _client = docker.from_env()
    return _client


LANGUAGE_CONFIG = {
    "python": {
        "image": "python:3.11-slim",
        "filename": "solution.py",
        "run_stdin": "python /code/solution.py < /code/input.txt",
        "run_no_stdin": "python /code/solution.py",
    },
    "java": {
        "image": "openjdk:17-slim",
        "filename": "Solution.java",
        "run_stdin": "cd /code && javac {filename} && java {classname} < /code/input.txt",
        "run_no_stdin": "cd /code && javac {filename} && java {classname}",
    },
    "c": {
        "image": "gcc:latest",
        "filename": "solution.c",
        "run_stdin": "cd /code && gcc -o solution solution.c -lm && ./solution < /code/input.txt",
        "run_no_stdin": "cd /code && gcc -o solution solution.c -lm && ./solution",
    },
    "cpp": {
        "image": "gcc:latest",
        "filename": "solution.cpp",
        "run_stdin": "cd /code && g++ -o solution solution.cpp -std=c++17 -lm && ./solution < /code/input.txt",
        "run_no_stdin": "cd /code && g++ -o solution solution.cpp -std=c++17 -lm && ./solution",
    },
    "c++": {
        "image": "gcc:latest",
        "filename": "solution.cpp",
        "run_stdin": "cd /code && g++ -o solution solution.cpp -std=c++17 -lm && ./solution < /code/input.txt",
        "run_no_stdin": "cd /code && g++ -o solution solution.cpp -std=c++17 -lm && ./solution",
    },
    "javascript": {
        "image": "node:20-slim",
        "filename": "solution.js",
        "run_stdin": "node /code/solution.js < /code/input.txt",
        "run_no_stdin": "node /code/solution.js",
    },
    "js": {
        "image": "node:20-slim",
        "filename": "solution.js",
        "run_stdin": "node /code/solution.js < /code/input.txt",
        "run_no_stdin": "node /code/solution.js",
    },
}

TIMEOUT_SECONDS = 5
MEMORY_LIMIT = "256m"
PIDS_LIMIT = 50


def _make_tar(files: dict[str, str]) -> bytes:
    """Create an in-memory tar archive from a dict of {filename: content}.
    Files are placed under code/ directory prefix."""
    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        # Create the /code directory entry
        dir_info = tarfile.TarInfo(name="code")
        dir_info.type = tarfile.DIRTYPE
        dir_info.mode = 0o755
        tar.addfile(dir_info)

        for name, content in files.items():
            data = content.encode("utf-8")
            info = tarfile.TarInfo(name=f"code/{name}")
            info.size = len(data)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(data))
    tar_stream.seek(0)
    return tar_stream.read()


def execute_code(code: str, language: str, input_data: str = "") -> dict:
    """
    Execute user code in an isolated Docker container.

    Args:
        code: The full source code to execute
        language: Programming language (python, java, c, cpp, javascript)
        input_data: Input to pipe to stdin

    Returns:
        dict with keys: status ("success"|"error"|"timeout"), stdout, stderr
    """
    import docker

    lang_key = language.lower().strip()
    config = LANGUAGE_CONFIG.get(lang_key)

    if not config:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Unsupported language: {language}",
        }

    container = None

    try:
        client = _get_client()

        # Determine filename
        filename = config["filename"]

        # For Java, extract the public class name
        if lang_key == "java":
            filename = _get_java_filename(code)

        # Build the files to copy into the container
        files_to_copy = {filename: code}

        has_input = bool((input_data or "").strip())
        if has_input:
            # Ensure input ends with newline
            input_content = input_data if input_data.endswith("\n") else input_data + "\n"
            files_to_copy["input.txt"] = input_content

        # Build the command
        if lang_key == "java":
            class_name = filename.replace(".java", "")
            if has_input:
                cmd_str = config["run_stdin"].format(filename=filename, classname=class_name)
            else:
                cmd_str = config["run_no_stdin"].format(filename=filename, classname=class_name)
        elif has_input:
            cmd_str = config["run_stdin"]
        else:
            cmd_str = config["run_no_stdin"]

        # Create the container (don't start yet — we need to copy files first)
        container = client.containers.create(
            image=config["image"],
            command=["sh", "-c", cmd_str],
            network_mode="none",
            mem_limit=MEMORY_LIMIT,
            cap_drop=["ALL"],
            pids_limit=PIDS_LIMIT,
            environment={"PYTHONUNBUFFERED": "1"},
            working_dir="/code",
        )

        # Copy code files into the container via tar archive (extract to /)
        tar_data = _make_tar(files_to_copy)
        container.put_archive("/", tar_data)

        # Start the container
        container.start()

        # Wait for completion with timeout
        try:
            result = container.wait(timeout=TIMEOUT_SECONDS)
            exit_code = result.get("StatusCode", -1)
        except Exception:
            # Timeout or connection error — kill the container
            try:
                container.kill()
            except Exception:
                pass
            return {
                "status": "timeout",
                "stdout": "",
                "stderr": f"Execution timed out after {TIMEOUT_SECONDS} seconds",
            }

        # Get stdout and stderr
        stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
        stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")

        if exit_code != 0:
            return {
                "status": "error",
                "stdout": stdout.strip(),
                "stderr": stderr.strip() or f"Process exited with code {exit_code}",
            }

        return {
            "status": "success",
            "stdout": stdout.strip(),
            "stderr": stderr.strip(),
        }

    except docker.errors.ImageNotFound:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Docker image '{config['image']}' not found. Run: docker pull {config['image']}",
        }
    except docker.errors.APIError as e:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Docker API error: {str(e)}",
        }
    except Exception as e:
        return {
            "status": "error",
            "stdout": "",
            "stderr": f"Execution error: {str(e)}",
        }
    finally:
        # Clean up container — no leaks
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass


def _get_java_filename(code: str) -> str:
    """
    Extract the public class name from Java code to use as filename.
    Java requires the filename to match the public class name.
    Falls back to 'Solution.java' if not found.
    """
    match = re.search(r'public\s+class\s+(\w+)', code)
    if match:
        return f"{match.group(1)}.java"
    return "Solution.java"


def pull_required_images():
    """Pre-pull all required Docker images for faster first execution."""
    try:
        client = _get_client()
    except Exception as e:
        print(f"Docker not available for image pre-pull: {e}")
        return

    images = set()
    for config in LANGUAGE_CONFIG.values():
        images.add(config["image"])

    for image in images:
        try:
            client.images.get(image)
            print(f"  ✓ {image} already available")
        except Exception:
            try:
                print(f"  ↓ Pulling {image}...")
                client.images.pull(image)
                print(f"  ✓ {image} ready")
            except Exception as e:
                print(f"  ✗ Failed to pull {image}: {e}")
