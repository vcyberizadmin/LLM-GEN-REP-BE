import aiosqlite
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class DatabaseService:
    """Async SQLite database service for visualization storage"""
    
    def __init__(self, db_path: str = "data/visualizations.db"):
        self.db_path = db_path
        self.ensure_data_directory()
    
    def ensure_data_directory(self):
        """Ensure the data directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    async def init_database(self):
        """Initialize database with required tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Enable JSON1 extension for better JSON support
                await db.execute("PRAGMA foreign_keys = ON")
                
                # Create visualization_sessions table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS visualization_sessions (
                        id TEXT PRIMARY KEY,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        dataset_info TEXT, -- JSON
                        session_metadata TEXT -- JSON
                    )
                """)
                
                # Create visualizations table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS visualizations (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        query TEXT NOT NULL,
                        chart_spec TEXT NOT NULL, -- JSON
                        chart_data TEXT NOT NULL, -- JSON
                        chart_type TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT, -- JSON
                        FOREIGN KEY (session_id) REFERENCES visualization_sessions (id)
                    )
                """)
                
                # Create chat_entries table
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS chat_entries (
                        id TEXT PRIMARY KEY,
                        session_id TEXT NOT NULL,
                        query TEXT NOT NULL,
                        response TEXT NOT NULL,
                        visualization_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES visualization_sessions (id),
                        FOREIGN KEY (visualization_id) REFERENCES visualizations (id)
                    )
                """)
                
                # Create indexes for better performance
                await db.execute("CREATE INDEX IF NOT EXISTS idx_visualizations_session_id ON visualizations(session_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_chat_entries_session_id ON chat_entries(session_id)")
                await db.execute("CREATE INDEX IF NOT EXISTS idx_visualizations_created_at ON visualizations(created_at)")
                
                await db.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    async def create_session(self, session_id: str, dataset_info: Optional[Dict] = None, 
                           session_metadata: Optional[Dict] = None) -> bool:
        """Create a new visualization session"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO visualization_sessions (id, dataset_info, session_metadata)
                    VALUES (?, ?, ?)
                """, (
                    session_id,
                    json.dumps(dataset_info) if dataset_info else None,
                    json.dumps(session_metadata) if session_metadata else None
                ))
                await db.commit()
                logger.info(f"Created session: {session_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def save_visualization(self, viz_id: str, session_id: str, query: str,
                               chart_spec: Dict, chart_data: Dict, chart_type: str,
                               metadata: Optional[Dict] = None) -> bool:
        """Save a visualization to the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO visualizations (id, session_id, query, chart_spec, chart_data, chart_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    viz_id,
                    session_id,
                    query,
                    json.dumps(chart_spec),
                    json.dumps(chart_data),
                    chart_type,
                    json.dumps(metadata) if metadata else None
                ))
                await db.commit()
                logger.info(f"Saved visualization: {viz_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save visualization {viz_id}: {e}")
            return False
    
    async def save_chat_entry(self, entry_id: str, session_id: str, query: str,
                            response: str, visualization_id: Optional[str] = None) -> bool:
        """Save a chat entry to the database"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO chat_entries (id, session_id, query, response, visualization_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (entry_id, session_id, query, response, visualization_id))
                await db.commit()
                logger.info(f"Saved chat entry: {entry_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to save chat entry {entry_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session information"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, created_at, updated_at, dataset_info, session_metadata
                    FROM visualization_sessions WHERE id = ?
                """, (session_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return {
                            "id": row[0],
                            "created_at": row[1],
                            "updated_at": row[2],
                            "dataset_info": json.loads(row[3]) if row[3] else None,
                            "session_metadata": json.loads(row[4]) if row[4] else None
                        }
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
        return None
    
    async def get_session_visualizations(self, session_id: str) -> List[Dict]:
        """Get all visualizations for a session"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, session_id, query, chart_spec, chart_data, chart_type, created_at, metadata
                    FROM visualizations WHERE session_id = ? ORDER BY created_at DESC
                """, (session_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "session_id": row[1],
                            "query": row[2],
                            "chart_spec": json.loads(row[3]),
                            "chart_data": json.loads(row[4]),
                            "chart_type": row[5],
                            "created_at": row[6],
                            "metadata": json.loads(row[7]) if row[7] else None
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Failed to get visualizations for session {session_id}: {e}")
        return []
    
    async def get_visualization(self, viz_id: str) -> Optional[Dict]:
        """Get a specific visualization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, session_id, query, chart_spec, chart_data, chart_type, created_at, metadata
                    FROM visualizations WHERE id = ?
                """, (viz_id,)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return {
                            "id": row[0],
                            "session_id": row[1],
                            "query": row[2],
                            "chart_spec": json.loads(row[3]),
                            "chart_data": json.loads(row[4]),
                            "chart_type": row[5],
                            "created_at": row[6],
                            "metadata": json.loads(row[7]) if row[7] else None
                        }
        except Exception as e:
            logger.error(f"Failed to get visualization {viz_id}: {e}")
        return None
    
    async def get_session_chat_history(self, session_id: str) -> List[Dict]:
        """Get chat history for a session"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, session_id, query, response, visualization_id, created_at
                    FROM chat_entries WHERE session_id = ? ORDER BY created_at ASC
                """, (session_id,)) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "session_id": row[1],
                            "query": row[2],
                            "response": row[3],
                            "visualization_id": row[4],
                            "created_at": row[5]
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Failed to get chat history for session {session_id}: {e}")
        return []
    
    async def list_sessions(self, limit: int = 50) -> List[Dict]:
        """List all sessions with basic info"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, created_at, updated_at, dataset_info
                    FROM visualization_sessions ORDER BY updated_at DESC LIMIT ?
                """, (limit,)) as cursor:
                    rows = await cursor.fetchall()
                    return [
                        {
                            "id": row[0],
                            "created_at": row[1],
                            "updated_at": row[2],
                            "dataset_info": json.loads(row[3]) if row[3] else None
                        }
                        for row in rows
                    ]
        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
        return []
    
    async def delete_visualization(self, viz_id: str) -> bool:
        """Delete a visualization"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM visualizations WHERE id = ?", (viz_id,))
                await db.commit()
                logger.info(f"Deleted visualization: {viz_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete visualization {viz_id}: {e}")
            return False
    
    async def update_session_timestamp(self, session_id: str) -> bool:
        """Update session timestamp"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE visualization_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (session_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Error updating session timestamp: {e}")
            return False

    async def update_session_metadata(self, session_id: str, dataset_info: Optional[Dict] = None, session_metadata: Optional[Dict] = None) -> bool:
        """Update session dataset info and metadata"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Build update query dynamically based on what's provided
                updates = []
                params = []
                
                if dataset_info is not None:
                    updates.append("dataset_info = ?")
                    params.append(json.dumps(dataset_info))
                
                if session_metadata is not None:
                    updates.append("session_metadata = ?")
                    params.append(json.dumps(session_metadata))
                
                # Always update timestamp
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.append(session_id)
                
                if updates:
                    query = f"UPDATE visualization_sessions SET {', '.join(updates)} WHERE id = ?"
                    await db.execute(query, params)
                    await db.commit()
                    logger.info(f"Updated session metadata for session: {session_id}")
                    return True
                
                return False
        except Exception as e:
            logger.error(f"Error updating session metadata: {e}")
            return False 