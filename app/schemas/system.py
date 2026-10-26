from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    model_loaded: bool


class ModelListOut(BaseModel):
    current: str
    model: str
    models: list[str]


class ModelSwitchIn(BaseModel):
    model: str


class StatsOut(BaseModel):
    users: int
    templates: int
    templates_other_model: int
    templates_undecryptable: int
    model: str
    model_loaded: bool
    model_error: str | None
    providers: list[str]
    threshold: float
    threshold_calibrated: bool
    liveness: str
