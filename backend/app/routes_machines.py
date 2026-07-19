from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_auth
from app.machines import create_machine, delete_machine, list_machines
from app.models import MachineCreate
from app.ssh_keys import list_available_keys

router = APIRouter(prefix="/api/machines", tags=["machines"], dependencies=[Depends(require_auth)])


@router.get("")
def get_machines():
    return {"machines": list_machines()}


@router.get("/available-keys")
def get_available_keys():
    """Keys already mounted from the host -- the add-machine form picks
    from this list rather than accepting a free-text path, per the "use
    what's already there" requirement."""
    return {"keys": list_available_keys()}


@router.post("")
def add_machine(payload: MachineCreate):
    return create_machine(
        payload.name, payload.host, payload.port, payload.ssh_user, payload.ssh_key_path
    )


@router.delete("/{machine_id}")
def remove_machine(machine_id: int):
    if not delete_machine(machine_id):
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"deleted": machine_id}
