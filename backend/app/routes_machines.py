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
    if payload.auth_type == "key" and not payload.ssh_key_path:
        raise HTTPException(status_code=400, detail="ssh_key_path je povinný pre auth_type=key")
    if payload.auth_type == "key" and payload.ssh_key_path not in list_available_keys():
        # The dropdown only ever offers what's actually mounted from the
        # host (see the docstring above) -- reject anything else server
        # side too, don't just trust the client to have used the dropdown.
        raise HTTPException(status_code=400, detail="ssh_key_path nie je medzi kľúčmi namontovanými na hostiteľovi")
    return create_machine(
        payload.name,
        payload.host,
        payload.port,
        payload.ssh_user,
        payload.auth_type,
        payload.ssh_key_path,
    )


@router.delete("/{machine_id}")
def remove_machine(machine_id: int):
    if not delete_machine(machine_id):
        raise HTTPException(status_code=404, detail="Machine not found")
    return {"deleted": machine_id}
