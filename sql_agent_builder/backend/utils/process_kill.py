import subprocess

def kill_process_on_port(port: int):
    try:
        output = subprocess.check_output(f"lsof -t -i:{port}", shell=True).decode().strip()
        for pid in output.splitlines():
            subprocess.call(["kill", "-9", pid])
    except subprocess.CalledProcessError:
        pass
