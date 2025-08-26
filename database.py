
"""
Database operations for the Google Maps scraper
"""
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import asyncio
import aiosqlite

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async database manager for storing scraped data"""
    
    def __init__(self, db_path: str = "leads.db"):
        self.db_path = db_path
        self.batch_size = 100
        
    async def initialize(self):
        """Initialize database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS businesses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    website TEXT,
                    email TEXT,
                    query TEXT,
                    page_number INTEGER,
                    position INTEGER,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    data_quality_score REAL DEFAULT 0.0,
                    validation_status TEXT DEFAULT 'pending'
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS scrape_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    total_pages INTEGER,
                    total_businesses INTEGER,
                    successful_scrapes INTEGER,
                    failed_scrapes INTEGER,
                    status TEXT DEFAULT 'running'
                )
            """)
            
            await db.execute("""
                CREATE TABLE IF NOT EXISTS skipped_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    position TEXT,
                    name TEXT,
                    reason TEXT,
                    skipped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES scrape_sessions (id)
                )
            """)
            
            await db.commit()
    
    async def create_session(self, query: str, total_pages: int) -> int:
        """Create a new scrape session"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "INSERT INTO scrape_sessions (query, total_pages) VALUES (?, ?)",
                (query, total_pages)
            )
            await db.commit()
            return cursor.lastrowid
    
    async def update_session(self, session_id: int, **kwargs):
        """Update session statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
            values = list(kwargs.values()) + [session_id]
            await db.execute(
                f"UPDATE scrape_sessions SET {fields} WHERE id = ?",
                values
            )
            await db.commit()
    
    async def insert_business(self, business_data: Dict, session_id: int) -> bool:
        """Insert a business record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO businesses 
                    (name, address, phone, website, email, query, page_number, position, data_quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    business_data.get('Name', ''),
                    business_data.get('Address', ''),
                    business_data.get('Phone', ''),
                    business_data.get('Website', ''),
                    business_data.get('Email', ''),
                    business_data.get('query', ''),
                    business_data.get('page_number', 0),
                    business_data.get('position', 0),
                    self._calculate_quality_score(business_data)
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to insert business: {e}")
            return False
    
    async def insert_skipped_entry(self, skipped_data: Dict, session_id: int) -> bool:
        """Insert a skipped entry record"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO skipped_entries (session_id, position, name, reason)
                    VALUES (?, ?, ?, ?)
                """, (
                    session_id,
                    skipped_data.get('Position', ''),
                    skipped_data.get('Name', ''),
                    skipped_data.get('Reason', '')
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to insert skipped entry: {e}")
            return False
    
    async def get_session_stats(self, session_id: int) -> Dict:
        """Get session statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM scrape_sessions WHERE id = ?", (session_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else {}
    
    async def export_to_csv(self, session_id: int, filename: str) -> bool:
        """Export session data to CSV"""
        try:
            import csv
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT name, address, phone, website, email FROM businesses WHERE query = (SELECT query FROM scrape_sessions WHERE id = ?)",
                    (session_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    
                    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(['Name', 'Address', 'Phone', 'Website', 'Email'])
                        writer.writerows(rows)
                    return True
        except Exception as e:
            logger.error(f"Failed to export to CSV: {e}")
            return False
    
    def _calculate_quality_score(self, business_data: Dict) -> float:
        """Calculate data quality score for a business"""
        score = 0.0
        fields = ['Name', 'Address', 'Phone', 'Website', 'Email']
        
        for field in fields:
            if business_data.get(field) and business_data[field] != 'N/A':
                score += 20.0
        
        # Bonus for valid email format
        email = business_data.get('Email', '')
        if email and email != 'N/A' and '@' in email and '.' in email:
            score += 10.0
        
        return min(score, 100.0)
    
    async def get_businesses_by_query(self, query: str) -> List[Dict]:
        """Get all businesses for a specific query"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM businesses WHERE query = ? ORDER BY scraped_at DESC",
                (query,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
    
    async def cleanup_old_sessions(self, days: int = 30):
        """Clean up old sessions and data"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM scrape_sessions 
                WHERE start_time < datetime('now', '-{} days')
            """.format(days))
            await db.commit()
