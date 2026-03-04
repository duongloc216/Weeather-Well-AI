import os
import pyodbc
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Load biến môi trường từ file .env
load_dotenv()

# Đọc thông tin SQL Server từ env
SQL_SERVER_HOST = os.getenv("SQL_SERVER_HOST", "localhost\\MSSQLSERVER02")
SQL_SERVER_PORT = os.getenv("SQL_SERVER_PORT", "1433")
SQL_SERVER_DATABASE = os.getenv("SQL_SERVER_DATABASE", "health_twin")
SQL_SERVER_USER = os.getenv("SQL_SERVER_USER", "locdt")
SQL_SERVER_PASSWORD = os.getenv("SQL_SERVER_PASSWORD", "locdt")
SQL_SERVER_DRIVER = os.getenv("SQL_SERVER_DRIVER", "ODBC Driver 17 for SQL Server")

# Thread pool executor cho async operations
executor = ThreadPoolExecutor(max_workers=10)

class SQLServerPool:
    """
    SQL Server connection pool wrapper để tương thích với asyncpg interface
    """
    def __init__(self):
        self.connection_string = (
            f"DRIVER={{{SQL_SERVER_DRIVER}}};"
            f"SERVER={SQL_SERVER_HOST},{SQL_SERVER_PORT};"
            f"DATABASE={SQL_SERVER_DATABASE};"
            f"UID={SQL_SERVER_USER};"
            f"PWD={SQL_SERVER_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
        print(f"[SQL Server] Connection string configured for {SQL_SERVER_HOST}")
    
    class Connection:
        """Wrapper class để mô phỏng asyncpg connection"""
        def __init__(self, connection_string):
            self.connection_string = connection_string
            self._conn = None
        
        async def __aenter__(self):
            loop = asyncio.get_event_loop()
            self._conn = await loop.run_in_executor(
                executor, 
                lambda: pyodbc.connect(self.connection_string, timeout=30)
            )
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if self._conn:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(executor, self._conn.close)
        
        async def execute(self, query, *args):
            """Execute query without returning results"""
            loop = asyncio.get_event_loop()
            def _execute():
                cursor = self._conn.cursor()
                try:
                    cursor.execute(query, args)
                    self._conn.commit()
                    return f"UPDATE {cursor.rowcount}"
                finally:
                    cursor.close()
            return await loop.run_in_executor(executor, _execute)
        
        async def fetch(self, query, *args):
            """Fetch multiple rows"""
            loop = asyncio.get_event_loop()
            def _fetch():
                cursor = self._conn.cursor()
                try:
                    cursor.execute(query, args)
                    columns = [column[0] for column in cursor.description]
                    results = []
                    for row in cursor.fetchall():
                        results.append(dict(zip(columns, row)))
                    return results
                finally:
                    cursor.close()
            return await loop.run_in_executor(executor, _fetch)
        
        async def fetchrow(self, query, *args):
            """Fetch single row"""
            loop = asyncio.get_event_loop()
            def _fetchrow():
                cursor = self._conn.cursor()
                try:
                    cursor.execute(query, args)
                    row = cursor.fetchone()
                    if row:
                        columns = [column[0] for column in cursor.description]
                        return dict(zip(columns, row))
                    return None
                finally:
                    cursor.close()
            return await loop.run_in_executor(executor, _fetchrow)
        
        async def fetchval(self, query, *args):
            """Fetch single value"""
            loop = asyncio.get_event_loop()
            def _fetchval():
                cursor = self._conn.cursor()
                try:
                    cursor.execute(query, args)
                    row = cursor.fetchone()
                    return row[0] if row else None
                finally:
                    cursor.close()
            return await loop.run_in_executor(executor, _fetchval)
        
        async def executemany(self, query, records):
            """Execute query for multiple records (bulk insert)"""
            loop = asyncio.get_event_loop()
            def _executemany():
                cursor = self._conn.cursor()
                try:
                    cursor.executemany(query, records)
                    self._conn.commit()
                    return f"INSERT {cursor.rowcount}"
                finally:
                    cursor.close()
            return await loop.run_in_executor(executor, _executemany)
    
    def acquire(self):
        """Return a connection context manager"""
        return self.Connection(self.connection_string)


# Biến toàn cục giữ connection pool
db_pool = None


async def init_db():
    """
    Khởi tạo connection pool đến SQL Server.
    Gọi 1 lần khi start app/worker.
    """
    global db_pool
    if db_pool is None:
        db_pool = SQLServerPool()
        print("[SQL Server] Connection pool created")
    return db_pool


async def get_db():
    """
    Lấy connection pool.
    Sử dụng trong async context:
        async with (await get_db()).acquire() as conn:
            ...
    """
    global db_pool
    if db_pool is None:
        await init_db()
    return db_pool
