import docker
from .settings import SETTINGS

# Use explicit unix socket base_url to avoid relying on "http+docker" scheme support.
# SETTINGS.DOCKER_HOST should be like: unix:///var/run/docker.sock
cli = docker.DockerClient(base_url=SETTINGS.DOCKER_HOST)

def trader_container_name(trader_id: str) -> str:
    return f"trader-{trader_id}"

def ensure_trader_container(trader_id: str, env: dict[str, str], recreate: bool = False):
    name = trader_container_name(trader_id)

    try:
        c = cli.containers.get(name)
        if recreate:
            try:
                c.stop(timeout=5)
            except Exception:
                pass
            try:
                c.remove(force=True)
            except Exception:
                pass
        else:
            return c
    except docker.errors.NotFound:
        pass

    return cli.containers.run(
        image=SETTINGS.TRADER_IMAGE,
        name=name,
        detach=True,
        network=SETTINGS.TRADER_NETWORK,
        environment=env,
        restart_policy={"Name": "unless-stopped"},
        labels={"app": "upbit-trader", "trader_id": trader_id},
    )

def get_trader_container(trader_id: str):
    name = trader_container_name(trader_id)
    try:
        return cli.containers.get(name)
    except docker.errors.NotFound:
        return None

def stop_remove_trader_container_if_exists(trader_id: str) -> bool:
    c = get_trader_container(trader_id)
    if not c:
        return False
    try:
        try:
            c.stop(timeout=5)
        except Exception:
            pass
        c.remove(force=True)
    except Exception:
        pass
    return True
