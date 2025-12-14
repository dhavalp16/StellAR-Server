import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class SupabaseService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseService, cls).__new__(cls)
            cls._instance.client = None
            cls._instance.initialized = False
        return cls._instance

    def initialize(self):
        if self.initialized:
            return

        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            logger.warning("⚠️ SUPABASE_URL or SUPABASE_KEY not found in environment variables. tailored features will be disabled.")
            return

        try:
            self.client: Client = create_client(url, key)
            self.initialized = True
            logger.info("✅ Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Supabase client: {e}")

    def get_client(self):
        if not self.initialized:
             # Try lazy init
            self.initialize()
        return self.client

    def upload_file(self, bucket: str, file_path: str, destination_path: str) -> str:
        """
        Uploads a file to Supabase Storage and returns the public URL.
        """
        if not self.initialized:
            raise Exception("Supabase not initialized")

        try:
            with open(file_path, 'rb') as f:
                self.client.storage.from_(bucket).upload(path=destination_path, file=f)
            
            # Get public URL
            BASE_URL = os.environ.get("SUPABASE_URL")
            # Construct URL manually or ask sdk (get_public_url seems standard)
            public_url = self.client.storage.from_(bucket).get_public_url(destination_path)
            return public_url
        except Exception as e:
            logger.error(f"Failed to upload to Supabase: {e}")
            raise e

    def insert_record(self, table: str, data: dict):
        if not self.initialized:
            raise Exception("Supabase not initialized")
        
        try:
            data = self.client.table(table).insert(data).execute()
            return data
        except Exception as e:
            logger.error(f"Failed to insert record into {table}: {e}")
            raise e

    def query_records(self, table: str, select: str = "*", filters: dict = None):
        if not self.initialized:
             # Try lazy init
            self.initialize()
            if not self.initialized:
                return [] # Fail gracefully for now
        
        try:
            query = self.client.table(table).select(select)
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)
            
            response = query.execute()
            return response.data
        except Exception as e:
            logger.error(f"Failed to query {table}: {e}")
            return []

# Global instance
supabase_service = SupabaseService()
