from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime
import uuid

class DatasetInfo(BaseModel):
    """Information about the dataset used for visualization"""
    total_rows: int
    total_columns: int
    file_names: List[str]
    columns: List[str]

class ChartSpec(BaseModel):
    """Chart specification from LLM"""
    type: str
    x: Optional[str] = None
    y: Optional[str] = None
    labels: Optional[List[str]] = None
    values: Optional[List[Any]] = None
    colors: Optional[List[str]] = None
    title: Optional[str] = None
    options: Optional[Dict[str, Any]] = None

class ChartData(BaseModel):
    """Processed chart data for frontend rendering"""
    type: str
    labels: Optional[List[str]] = None
    datasets: List[Dict[str, Any]]
    options: Optional[Dict[str, Any]] = None

class VisualizationSession(BaseModel):
    """A visualization session containing multiple charts and chat history"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    dataset_info: Optional[DatasetInfo] = None
    session_metadata: Optional[Dict[str, Any]] = None

class Visualization(BaseModel):
    """Individual visualization within a session"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    query: str
    chart_spec: ChartSpec
    chart_data: ChartData
    chart_type: str
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Optional[Dict[str, Any]] = None

class ChatEntry(BaseModel):
    """Chat entry linked to visualizations"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    query: str
    response: str
    visualization_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)

class VisualizationResponse(BaseModel):
    """Response model for visualization endpoints"""
    visualization: Visualization
    success: bool = True
    message: Optional[str] = None

class SessionResponse(BaseModel):
    """Response model for session endpoints"""
    session: VisualizationSession
    visualizations: List[Visualization] = []
    chat_history: List[ChatEntry] = []
    success: bool = True
    message: Optional[str] = None 