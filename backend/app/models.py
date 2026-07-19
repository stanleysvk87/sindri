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


class SandboxRunRequest(BaseModel):
    content: str
    script_type: str | None = None
