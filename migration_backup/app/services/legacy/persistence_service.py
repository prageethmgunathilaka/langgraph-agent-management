"""
Persistence Service for Task and Workflow Data
Handles data storage, retrieval, and recovery for the hybrid intelligence system
"""

import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import asyncio
import aiofiles
from contextlib import asynccontextmanager

from ..models.schemas import Agent, TaskExecution, WorkflowPlan, TaskStatus, IntelligenceLevel

logger = logging.getLogger(__name__)


@dataclass
class PersistenceConfig:
    """Configuration for persistence service"""
    database_path: str = "data/taskmaster.db"
    backup_interval: int = 300  # 5 minutes
    max_backups: int = 10
    enable_file_backup: bool = True
    backup_directory: str = "data/backups"
    enable_compression: bool = True


class PersistenceService:
    """Service for persisting task and workflow data"""
    
    def __init__(self, config: Optional[PersistenceConfig] = None):
        self.config = config or PersistenceConfig()
        self.db_path = Path(self.config.database_path)
        self.backup_dir = Path(self.config.backup_directory)
        self._ensure_directories()
        self._init_database()
        
    def _ensure_directories(self):
        """Ensure required directories exist"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        if self.config.enable_file_backup:
            self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _init_database(self):
        """Initialize SQLite database with required tables"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Task executions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_executions (
                    task_id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    workflow_id TEXT,
                    status TEXT NOT NULL,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    retries INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    intelligence_level TEXT NOT NULL,
                    llm_interactions TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Workflow plans table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_plans (
                    workflow_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    steps TEXT NOT NULL,
                    success_criteria TEXT,
                    failure_handling TEXT,
                    estimated_duration INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Agent states table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    agent_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    agent_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    capabilities TEXT,
                    config TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    metadata TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_status ON task_executions(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_workflow ON task_executions(workflow_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_workflow ON agent_states(workflow_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_name ON system_metrics(metric_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON system_metrics(timestamp)")
            
            conn.commit()
            logger.info("Database initialized successfully")
    
    async def save_task_execution(self, execution: TaskExecution) -> bool:
        """Save or update task execution"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Convert complex data to JSON
                llm_interactions_json = json.dumps([])
                result_json = json.dumps(execution.result) if execution.result else None
                
                cursor.execute("""
                    INSERT OR REPLACE INTO task_executions 
                    (task_id, agent_id, workflow_id, status, start_time, end_time, 
                     result, error, retries, max_retries, intelligence_level, 
                     llm_interactions, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    execution.task_id,
                    execution.agent_id,
                    execution.workflow_id,
                    execution.status.value,
                    execution.started_at.isoformat() if execution.started_at else None,
                    execution.completed_at.isoformat() if execution.completed_at else None,
                    result_json,
                    execution.error,
                    0,  # retries - not in new model
                    3,  # max_retries - not in new model
                    execution.intelligence_level.value,
                    llm_interactions_json
                ))
                
                conn.commit()
                logger.debug(f"Saved task execution: {execution.task_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save task execution {execution.task_id}: {e}")
            return False
    
    async def load_task_execution(self, task_id: str) -> Optional[TaskExecution]:
        """Load task execution by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, agent_id, status, start_time, end_time, 
                           result, error, retries, max_retries, intelligence_level, 
                           llm_interactions
                    FROM task_executions WHERE task_id = ?
                """, (task_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                # Parse JSON fields
                result = json.loads(row[5]) if row[5] else None
                llm_interactions = json.loads(row[10]) if row[10] else []
                
                # Create TaskExecution with new model structure
                return TaskExecution(
                    task_id=row[0],
                    workflow_id="unknown",  # Legacy data doesn't have workflow_id
                    agent_id=row[1],
                    status=TaskStatus(row[2]),
                    intelligence_level=IntelligenceLevel(row[9]),
                    task_data=result or {},
                    result=result,
                    error=row[6],
                    started_at=datetime.fromisoformat(row[3]),
                    completed_at=datetime.fromisoformat(row[4]) if row[4] else None
                )
                
        except Exception as e:
            logger.error(f"Failed to load task execution {task_id}: {e}")
            return None
    
    async def save_workflow_plan(self, plan: WorkflowPlan) -> bool:
        """Save workflow plan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                steps_json = json.dumps(plan.steps)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO workflow_plans 
                    (workflow_id, title, description, steps, success_criteria, 
                     failure_handling, estimated_duration, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    plan.workflow_id,
                    plan.title,
                    plan.description,
                    steps_json,
                    plan.metadata.get("success_criteria", ""),
                    plan.metadata.get("failure_handling", ""),
                    plan.metadata.get("estimated_duration", 0)
                ))
                
                conn.commit()
                logger.debug(f"Saved workflow plan: {plan.workflow_id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save workflow plan {plan.workflow_id}: {e}")
            return False
    
    async def load_workflow_plan(self, workflow_id: str) -> Optional[WorkflowPlan]:
        """Load workflow plan by ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT workflow_id, title, description, steps, success_criteria, 
                           failure_handling, estimated_duration, created_at
                    FROM workflow_plans WHERE workflow_id = ?
                """, (workflow_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                steps = json.loads(row[3])
                created_at = datetime.fromisoformat(row[7])
                
                return WorkflowPlan(
                    workflow_id=row[0],
                    title=row[1],
                    description=row[2],
                    steps=steps,
                    metadata={
                        "success_criteria": row[4],
                        "failure_handling": row[5],
                        "estimated_duration": row[6]
                    },
                    created_at=created_at
                )
                
        except Exception as e:
            logger.error(f"Failed to load workflow plan {workflow_id}: {e}")
            return None
    
    async def save_agent_state(self, agent: Agent) -> bool:
        """Save agent state"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                capabilities_json = json.dumps(agent.capabilities)
                config_json = json.dumps(agent.config)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO agent_states 
                    (agent_id, workflow_id, name, agent_type, status, 
                     capabilities, config, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    agent.id,
                    agent.workflow_id,
                    agent.name,
                    agent.agent_type,
                    agent.status.value,
                    capabilities_json,
                    config_json
                ))
                
                conn.commit()
                logger.debug(f"Saved agent state: {agent.id}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to save agent state {agent.id}: {e}")
            return False
    
    async def get_tasks_by_status(self, status: TaskStatus) -> List[TaskExecution]:
        """Get all tasks with specific status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, agent_id, status, start_time, end_time, 
                           result, error, retries, max_retries, intelligence_level, 
                           llm_interactions
                    FROM task_executions WHERE status = ?
                    ORDER BY start_time DESC
                """, (status.value,))
                
                tasks = []
                for row in cursor.fetchall():
                    result = json.loads(row[5]) if row[5] else None
                    
                    task = TaskExecution(
                        task_id=row[0],
                        workflow_id="unknown",  # Legacy data doesn't have workflow_id
                        agent_id=row[1],
                        status=TaskStatus(row[2]),
                        intelligence_level=IntelligenceLevel(row[9]),
                        task_data=result or {},
                        result=result,
                        error=row[6],
                        started_at=datetime.fromisoformat(row[3]),
                        completed_at=datetime.fromisoformat(row[4]) if row[4] else None
                    )
                    tasks.append(task)
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to get tasks by status {status}: {e}")
            return []
    
    async def get_workflow_tasks(self, workflow_id: str) -> List[TaskExecution]:
        """Get all tasks for a specific workflow"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT task_id, agent_id, status, start_time, end_time, 
                           result, error, retries, max_retries, intelligence_level, 
                           llm_interactions
                    FROM task_executions WHERE workflow_id = ?
                    ORDER BY start_time ASC
                """, (workflow_id,))
                
                tasks = []
                for row in cursor.fetchall():
                    result = json.loads(row[5]) if row[5] else None
                    
                    task = TaskExecution(
                        task_id=row[0],
                        workflow_id=workflow_id,  # Use the provided workflow_id
                        agent_id=row[1],
                        status=TaskStatus(row[2]),
                        intelligence_level=IntelligenceLevel(row[9]),
                        task_data=result or {},
                        result=result,
                        error=row[6],
                        started_at=datetime.fromisoformat(row[3]),
                        completed_at=datetime.fromisoformat(row[4]) if row[4] else None
                    )
                    tasks.append(task)
                
                return tasks
                
        except Exception as e:
            logger.error(f"Failed to get workflow tasks {workflow_id}: {e}")
            return []
    
    async def record_metric(self, name: str, value: float, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Record a system metric"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                metadata_json = json.dumps(metadata) if metadata else None
                
                cursor.execute("""
                    INSERT INTO system_metrics (metric_name, metric_value, metadata)
                    VALUES (?, ?, ?)
                """, (name, value, metadata_json))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Failed to record metric {name}: {e}")
            return False
    
    async def get_metrics(self, name: str, since: Optional[datetime] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system metrics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if since:
                    cursor.execute("""
                        SELECT metric_name, metric_value, metadata, timestamp
                        FROM system_metrics 
                        WHERE metric_name = ? AND timestamp >= ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (name, since.isoformat(), limit))
                else:
                    cursor.execute("""
                        SELECT metric_name, metric_value, metadata, timestamp
                        FROM system_metrics 
                        WHERE metric_name = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    """, (name, limit))
                
                metrics = []
                for row in cursor.fetchall():
                    metadata = json.loads(row[2]) if row[2] else {}
                    metrics.append({
                        "name": row[0],
                        "value": row[1],
                        "metadata": metadata,
                        "timestamp": datetime.fromisoformat(row[3])
                    })
                
                return metrics
                
        except Exception as e:
            logger.error(f"Failed to get metrics {name}: {e}")
            return []
    
    async def cleanup_old_data(self, days: int = 30) -> bool:
        """Clean up old data older than specified days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up old completed tasks
                cursor.execute("""
                    DELETE FROM task_executions 
                    WHERE status = 'completed' AND updated_at < ?
                """, (cutoff_date.isoformat(),))
                
                # Clean up old metrics
                cursor.execute("""
                    DELETE FROM system_metrics 
                    WHERE timestamp < ?
                """, (cutoff_date.isoformat(),))
                
                conn.commit()
                logger.info(f"Cleaned up data older than {days} days")
                return True
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
            return False
    
    async def create_backup(self) -> Optional[str]:
        """Create a backup of the database"""
        if not self.config.enable_file_backup:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"taskmaster_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Copy database file
            with sqlite3.connect(self.db_path) as source:
                with sqlite3.connect(backup_path) as backup:
                    source.backup(backup)
            
            # Clean up old backups
            await self._cleanup_old_backups()
            
            logger.info(f"Created backup: {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    async def _cleanup_old_backups(self):
        """Remove old backup files"""
        try:
            backup_files = list(self.backup_dir.glob("taskmaster_backup_*.db"))
            backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Keep only the most recent backups
            for backup_file in backup_files[self.config.max_backups:]:
                backup_file.unlink()
                logger.debug(f"Removed old backup: {backup_file}")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old backups: {e}")
    
    async def restore_from_backup(self, backup_path: str) -> bool:
        """Restore database from backup"""
        try:
            backup_file = Path(backup_path)
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Create backup of current database
            await self.create_backup()
            
            # Replace current database with backup
            with sqlite3.connect(backup_file) as backup:
                with sqlite3.connect(self.db_path) as current:
                    backup.backup(current)
            
            logger.info(f"Restored database from backup: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                stats = {}
                
                # Task execution counts
                cursor.execute("SELECT COUNT(*) FROM task_executions")
                stats["total_tasks"] = cursor.fetchone()[0]
                
                cursor.execute("SELECT status, COUNT(*) FROM task_executions GROUP BY status")
                stats["tasks_by_status"] = dict(cursor.fetchall())
                
                # Workflow counts
                cursor.execute("SELECT COUNT(*) FROM workflow_plans")
                stats["total_workflows"] = cursor.fetchone()[0]
                
                # Agent counts
                cursor.execute("SELECT COUNT(*) FROM agent_states")
                stats["total_agents"] = cursor.fetchone()[0]
                
                # Metrics count
                cursor.execute("SELECT COUNT(*) FROM system_metrics")
                stats["total_metrics"] = cursor.fetchone()[0]
                
                # Database size
                stats["database_size"] = self.db_path.stat().st_size
                
                return stats
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on persistence service"""
        try:
            # Test database connection
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                db_healthy = cursor.fetchone()[0] == 1
            
            # Check disk space
            disk_usage = self.db_path.stat().st_size
            
            # Check backup directory
            backup_healthy = self.backup_dir.exists() if self.config.enable_file_backup else True
            
            return {
                "database_healthy": db_healthy,
                "backup_healthy": backup_healthy,
                "disk_usage": disk_usage,
                "last_backup": None,  # Would need to track this
                "status": "healthy" if db_healthy and backup_healthy else "unhealthy"
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "database_healthy": False,
                "backup_healthy": False,
                "disk_usage": 0,
                "last_backup": None,
                "status": "unhealthy",
                "error": str(e)
            } 