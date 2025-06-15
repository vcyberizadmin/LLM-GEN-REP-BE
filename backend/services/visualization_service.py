import uuid
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from .database_service import DatabaseService
from models.visualization_models import (
    VisualizationSession, Visualization, ChatEntry, DatasetInfo,
    ChartSpec, ChartData, VisualizationResponse, SessionResponse
)

logger = logging.getLogger(__name__)

class VisualizationService:
    """Service layer for visualization management"""
    
    def __init__(self, db_path: str = "data/visualizations.db"):
        self.db = DatabaseService(db_path)
        self._initialized = False
    
    async def initialize(self):
        """Initialize the service and database"""
        if not self._initialized:
            await self.db.init_database()
            self._initialized = True
            logger.info("VisualizationService initialized")
    
    async def create_session(self, dataset_info: Optional[Dict] = None, 
                           session_metadata: Optional[Dict] = None) -> str:
        """Create a new visualization session and return session ID"""
        try:
            await self.initialize()
            session_id = str(uuid.uuid4())
            
            success = await self.db.create_session(
                session_id=session_id,
                dataset_info=dataset_info,
                session_metadata=session_metadata
            )
            
            if success:
                logger.info(f"Created new session: {session_id}")
                return session_id
            else:
                raise Exception("Failed to create session in database")
                
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            # Return a temporary session ID for graceful degradation
            return str(uuid.uuid4())
    
    async def save_visualization(self, session_id: str, query: str, 
                               chart_spec: Dict, chart_data: Dict,
                               metadata: Optional[Dict] = None) -> Optional[str]:
        """Save a visualization and return visualization ID"""
        try:
            await self.initialize()
            viz_id = str(uuid.uuid4())
            chart_type = chart_spec.get('type', 'unknown') if chart_spec else 'unknown'
            
            success = await self.db.save_visualization(
                viz_id=viz_id,
                session_id=session_id,
                query=query,
                chart_spec=chart_spec or {},
                chart_data=chart_data or {},
                chart_type=chart_type,
                metadata=metadata
            )
            
            if success:
                # Update session timestamp
                await self.db.update_session_timestamp(session_id)
                logger.info(f"Saved visualization: {viz_id}")
                return viz_id
            else:
                logger.warning(f"Failed to save visualization for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving visualization: {e}")
            return None
    
    async def save_chat_entry(self, session_id: str, query: str, response: str,
                            visualization_id: Optional[str] = None) -> Optional[str]:
        """Save a chat entry and return entry ID"""
        try:
            await self.initialize()
            entry_id = str(uuid.uuid4())
            
            success = await self.db.save_chat_entry(
                entry_id=entry_id,
                session_id=session_id,
                query=query,
                response=response,
                visualization_id=visualization_id
            )
            
            if success:
                # Update session timestamp
                await self.db.update_session_timestamp(session_id)
                logger.info(f"Saved chat entry: {entry_id}")
                return entry_id
            else:
                logger.warning(f"Failed to save chat entry for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error saving chat entry: {e}")
            return None
    
    async def get_session_data(self, session_id: str) -> SessionResponse:
        """Get complete session data including visualizations and chat history"""
        try:
            await self.initialize()
            
            # Get session info
            session_data = await self.db.get_session(session_id)
            if not session_data:
                return SessionResponse(
                    session=VisualizationSession(id=session_id),
                    success=False,
                    message="Session not found"
                )
            
            # Get visualizations
            viz_data = await self.db.get_session_visualizations(session_id)
            visualizations = []
            for viz in viz_data:
                try:
                    visualization = Visualization(
                        id=viz['id'],
                        session_id=viz['session_id'],
                        query=viz['query'],
                        chart_spec=ChartSpec(**viz['chart_spec']),
                        chart_data=ChartData(**viz['chart_data']),
                        chart_type=viz['chart_type'],
                        created_at=datetime.fromisoformat(viz['created_at']),
                        metadata=viz['metadata']
                    )
                    visualizations.append(visualization)
                except Exception as e:
                    logger.warning(f"Failed to parse visualization {viz['id']}: {e}")
            
            # Get chat history
            chat_data = await self.db.get_session_chat_history(session_id)
            chat_history = []
            for chat in chat_data:
                try:
                    chat_entry = ChatEntry(
                        id=chat['id'],
                        session_id=chat['session_id'],
                        query=chat['query'],
                        response=chat['response'],
                        visualization_id=chat['visualization_id'],
                        created_at=datetime.fromisoformat(chat['created_at'])
                    )
                    chat_history.append(chat_entry)
                except Exception as e:
                    logger.warning(f"Failed to parse chat entry {chat['id']}: {e}")
            
            # Create session object
            session = VisualizationSession(
                id=session_data['id'],
                created_at=datetime.fromisoformat(session_data['created_at']),
                updated_at=datetime.fromisoformat(session_data['updated_at']),
                dataset_info=DatasetInfo(**session_data['dataset_info']) if session_data['dataset_info'] else None,
                session_metadata=session_data['session_metadata']
            )
            
            return SessionResponse(
                session=session,
                visualizations=visualizations,
                chat_history=chat_history,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error getting session data for {session_id}: {e}")
            return SessionResponse(
                session=VisualizationSession(id=session_id),
                success=False,
                message=f"Error retrieving session: {str(e)}"
            )
    
    async def get_visualization(self, viz_id: str) -> VisualizationResponse:
        """Get a specific visualization"""
        try:
            await self.initialize()
            
            viz_data = await self.db.get_visualization(viz_id)
            if not viz_data:
                return VisualizationResponse(
                    visualization=Visualization(
                        id=viz_id,
                        session_id="",
                        query="",
                        chart_spec=ChartSpec(type="unknown"),
                        chart_data=ChartData(type="unknown", datasets=[]),
                        chart_type="unknown"
                    ),
                    success=False,
                    message="Visualization not found"
                )
            
            visualization = Visualization(
                id=viz_data['id'],
                session_id=viz_data['session_id'],
                query=viz_data['query'],
                chart_spec=ChartSpec(**viz_data['chart_spec']),
                chart_data=ChartData(**viz_data['chart_data']),
                chart_type=viz_data['chart_type'],
                created_at=datetime.fromisoformat(viz_data['created_at']),
                metadata=viz_data['metadata']
            )
            
            return VisualizationResponse(
                visualization=visualization,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error getting visualization {viz_id}: {e}")
            return VisualizationResponse(
                visualization=Visualization(
                    id=viz_id,
                    session_id="",
                    query="",
                    chart_spec=ChartSpec(type="unknown"),
                    chart_data=ChartData(type="unknown", datasets=[]),
                    chart_type="unknown"
                ),
                success=False,
                message=f"Error retrieving visualization: {str(e)}"
            )
    
    async def list_sessions(self, limit: int = 50) -> List[Dict]:
        """List all sessions with basic information"""
        try:
            await self.initialize()
            return await self.db.list_sessions(limit)
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            return []
    
    async def delete_visualization(self, viz_id: str) -> bool:
        """Delete a visualization"""
        try:
            await self.initialize()
            return await self.db.delete_visualization(viz_id)
        except Exception as e:
            logger.error(f"Error deleting visualization {viz_id}: {e}")
            return False
    
    async def get_session_visualizations(self, session_id: str) -> List[Dict]:
        """Get all visualizations for a session (raw format)"""
        try:
            await self.initialize()
            return await self.db.get_session_visualizations(session_id)
        except Exception as e:
            logger.error(f"Error getting visualizations for session {session_id}: {e}")
            return [] 