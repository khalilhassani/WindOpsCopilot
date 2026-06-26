import logging
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError
from backend.app.config import settings

logger = logging.getLogger("database")

# In-memory mock database implementation for robust fallback
class MockAsyncCursor:
    def __init__(self, items):
        self.items = list(items)
        
    def sort(self, key, direction=-1):
        # direction: -1 is descending, 1 is ascending
        reverse = direction == -1
        # Simple sorting, try to sort by the specified key if it exists
        self.items.sort(key=lambda x: x.get(key, ""), reverse=reverse)
        return self
        
    def limit(self, n):
        self.items = self.items[:n]
        return self
        
    async def to_list(self, length=None):
        if length is not None:
            return self.items[:length]
        return self.items
        
    def __aiter__(self):
        self._index = 0
        return self
        
    async def __anext__(self):
        if self._index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self._index]
        self._index += 1
        return item

class MockCollection:
    def __init__(self, name):
        self.name = name
        self.docs = []
        
    async def insert_one(self, doc):
        if "_id" not in doc:
            import uuid
            doc["_id"] = str(uuid.uuid4())
        # Copy to avoid external mutations
        self.docs.append(dict(doc))
        class MockInsertResult:
            inserted_id = doc["_id"]
        return MockInsertResult()
        
    async def find_one(self, query):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                return dict(doc)
        return None
        
    def find(self, query=None):
        query = query or {}
        results = []
        for doc in self.docs:
            match = True
            for k, v in query.items():
                if doc.get(k) != v:
                    match = False
                    break
            if match:
                results.append(dict(doc))
        return MockAsyncCursor(results)
        
    async def update_one(self, query, update, upsert=False):
        # Basic update implementation
        set_dict = update.get("$set", {})
        found = False
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in query.items()):
                doc.update(set_dict)
                found = True
                break
        if not found and upsert:
            new_doc = dict(query)
            new_doc.update(set_dict)
            await self.insert_one(new_doc)
        class MockUpdateResult:
            modified_count = 1 if found else 0
        return MockUpdateResult()

class MockDatabase:
    def __init__(self):
        self.collections = {}
        
    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection(name)
        return self.collections[name]

# Global DB client variable
db_client = None
db = None
is_mock_db = False

def get_database():
    global db_client, db, is_mock_db
    
    if db is not None:
        return db
        
    # Attempt connecting to real MongoDB
    try:
        logger.info(f"Connecting to MongoDB at {settings.MONGODB_URL}...")
        # Use a synchronous MongoClient to verify connection is alive
        from pymongo import MongoClient
        check_client = MongoClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        check_client.admin.command('ping')
        check_client.close()
        
        # Connection verified, configure async client
        client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=2000)
        db_client = client
        db = client[settings.DATABASE_NAME]
        is_mock_db = False
        logger.info("Successfully connected to live MongoDB database.")
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB: {e}. Falling back to in-memory MockDatabase.")
        db = MockDatabase()
        is_mock_db = True
        
    return db
