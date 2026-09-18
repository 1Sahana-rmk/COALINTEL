from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class KpiResponse(BaseModel):
    total_production_mt: str
    total_obr_mcum: str
    total_documents: int
    active_conflicts: int
    entity_accuracy_rate: str
    citation_coverage_rate: str

    model_config = ConfigDict(from_attributes=True)


class ProductionChartItem(BaseModel):
    subsidiary: str
    actual: float
    target: Optional[float] = None
    obr: float


class DashboardChartsResponse(BaseModel):
    production_data: List[ProductionChartItem]

    model_config = ConfigDict(from_attributes=True)
