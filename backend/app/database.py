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

# Class wrapper to allow dynamic boolean evaluations for imported references
class MockDbFlag:
    def __init__(self, val=False):
        self.val = val
    def __bool__(self):
        return self.val

# Robust wrappers to catch database exceptions during runtime and fall back on-the-fly
class RobustCursorWrapper:
    def __init__(self, db_wrapper, coll_name, real_cursor, find_args, find_kwargs):
        self._db_wrapper = db_wrapper
        self._coll_name = coll_name
        self._real_cursor = real_cursor
        self._find_args = find_args
        self._find_kwargs = find_kwargs
        self._sort_args = None
        self._limit_n = None

    def sort(self, *args, **kwargs):
        self._sort_args = (args, kwargs)
        if not self._db_wrapper._use_mock:
            try:
                self._real_cursor = self._real_cursor.sort(*args, **kwargs)
            except Exception:
                pass
        return self

    def limit(self, n):
        self._limit_n = n
        if not self._db_wrapper._use_mock:
            try:
                self._real_cursor = self._real_cursor.limit(n)
            except Exception:
                pass
        return self

    async def to_list(self, length=None):
        try:
            if self._db_wrapper._use_mock:
                raise Exception("Forced mock database fallback active.")
            return await self._real_cursor.to_list(length)
        except Exception as e:
            if not self._db_wrapper._use_mock:
                logger.warning(f"Cursor query error on collection '{self._coll_name}': {e}. Switching to MockDatabase.")
                self._db_wrapper._use_mock = True
                global is_mock_db
                is_mock_db.val = True
            mock_coll = self._db_wrapper._mock_db[self._coll_name]
            mock_cursor = mock_coll.find(*self._find_args, **self._find_kwargs)
            if self._sort_args:
                mock_cursor.sort(*self._sort_args[0], **self._sort_args[1])
            if self._limit_n is not None:
                mock_cursor.limit(self._limit_n)
            return await mock_cursor.to_list(length)

class RobustCollectionWrapper:
    def __init__(self, db_wrapper, name):
        self._db_wrapper = db_wrapper
        self._name = name

    @property
    def _current_coll(self):
        if self._db_wrapper._use_mock:
            return self._db_wrapper._mock_db[self._name]
        return self._db_wrapper._real_db[self._name]

    async def insert_one(self, *args, **kwargs):
        try:
            if self._db_wrapper._use_mock:
                return await self._current_coll.insert_one(*args, **kwargs)
            return await self._current_coll.insert_one(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Write failure on collection '{self._name}': {e}. Switching to MockDatabase.")
            self._db_wrapper._use_mock = True
            global is_mock_db
            is_mock_db.val = True
            return await self._current_coll.insert_one(*args, **kwargs)

    async def update_one(self, *args, **kwargs):
        try:
            if self._db_wrapper._use_mock:
                return await self._current_coll.update_one(*args, **kwargs)
            return await self._current_coll.update_one(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Update failure on collection '{self._name}': {e}. Switching to MockDatabase.")
            self._db_wrapper._use_mock = True
            global is_mock_db
            is_mock_db.val = True
            return await self._current_coll.update_one(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        try:
            if self._db_wrapper._use_mock:
                return await self._current_coll.find_one(*args, **kwargs)
            return await self._current_coll.find_one(*args, **kwargs)
        except Exception as e:
            logger.warning(f"Query failure on collection '{self._name}': {e}. Switching to MockDatabase.")
            self._db_wrapper._use_mock = True
            global is_mock_db
            is_mock_db.val = True
            return await self._current_coll.find_one(*args, **kwargs)

    def find(self, *args, **kwargs):
        try:
            if self._db_wrapper._use_mock:
                return self._current_coll.find(*args, **kwargs)
            real_cursor = self._current_coll.find(*args, **kwargs)
            return RobustCursorWrapper(self._db_wrapper, self._name, real_cursor, args, kwargs)
        except Exception as e:
            logger.warning(f"Find failure on collection '{self._name}': {e}. Switching to MockDatabase.")
            self._db_wrapper._use_mock = True
            global is_mock_db
            is_mock_db.val = True
            return self._current_coll.find(*args, **kwargs)

class RobustDatabaseWrapper:
    def __init__(self, real_db, mock_db):
        self._real_db = real_db
        self._mock_db = mock_db
        self._use_mock = isinstance(real_db, MockDatabase)

    def __getitem__(self, name):
        return RobustCollectionWrapper(self, name)

# Global DB client variable
db_client = None
db = None
is_mock_db = MockDbFlag(False)

def get_database():
    global db_client, db, is_mock_db
    
    if db is not None:
        return db
        
    mock_db = MockDatabase()
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
        real_db = client[settings.DATABASE_NAME]
        is_mock_db.val = False
        logger.info("Successfully connected to live MongoDB database.")
        db = RobustDatabaseWrapper(real_db, mock_db)
    except Exception as e:
        logger.warning(f"Could not connect to live MongoDB: {e}. Falling back to in-memory MockDatabase.")
        is_mock_db.val = True
        db = RobustDatabaseWrapper(mock_db, mock_db)
        
    return db
