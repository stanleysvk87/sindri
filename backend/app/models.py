from pydantic import BaseModel


class ScriptOut(BaseModel):
    id: int
    name: str
    host: str
    tags: str
    short_description: str
    long_description: str
    notes: str
    content: str
    run_mode: str
    source_type: str
    source_ref: str
    has_possible_secret: bool
    created_at: str
    updated_at: str


class ScriptListItem(BaseModel):
    id: int
    name: str
    host: str
    tags: str
    short_description: str
    run_mode: str
    has_possible_secret: bool
    updated_at: str


class ScriptUpdate(BaseModel):
    name: str | None = None
    host: str | None = None
    tags: str | None = None
    short_description: str | None = None
    long_description: str | None = None
    notes: str | None = None
    run_mode: str | None = None


class ScriptPasteImport(BaseModel):
    name: str
    content: str
    host: str = ""
    tags: str = ""
    short_description: str = ""
    run_mode: str = ""
    source_ref: str = ""


class PathImportRequest(BaseModel):
    path: str
    host: str = ""


class ScanPathRequest(BaseModel):
    path: str


class ConfirmImportRequest(BaseModel):
    paths: list[str]
    host: str = ""


class LoginRequest(BaseModel):
    password: str


class AIGenerateRequest(BaseModel):
    description: str


class AIReviewRequest(BaseModel):
    name: str
    content: str


class AIChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    text: str


class AIChatRequest(BaseModel):
    name: str
    content: str
    messages: list[AIChatMessage]


class SandboxRunRequest(BaseModel):
    content: str
    script_type: str | None = None


class MachineCreate(BaseModel):
    name: str
    host: str
    port: int = 22
    ssh_user: str
    auth_type: str = "key"  # "key" | "password"
    ssh_key_path: str = ""  # required if auth_type == "key"


class AdHocConnection(BaseModel):
    """A machine's connection details supplied inline at run time,
    instead of picking a saved one -- for the "no machine saved yet,
    just fill in details and run once" flow."""
    host: str
    port: int = 22
    ssh_user: str
    auth_type: str = "key"
    ssh_key_path: str = ""
    save_as_name: str | None = None  # if set, persist the connection (never the password) after running


class RemoteExecRequest(BaseModel):
    machine_id: int | None = None
    connection: AdHocConnection | None = None  # used when machine_id is None
    sudo_password: str | None = None
    ssh_password: str | None = None


class AIConfigUpdate(BaseModel):
    provider_mode: str | None = None  # auto | claude_cli | codex_cli | anthropic_api
    anthropic_api_key: str | None = None  # empty string clears it


class HostStatusRequest(BaseModel):
    machine_id: int
