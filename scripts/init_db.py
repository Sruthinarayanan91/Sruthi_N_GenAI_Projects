from app.config import DB_PATH
from app.database.db import get_connection, initialize_database, seed_default_criteria
conn=get_connection(str(DB_PATH)); initialize_database(conn); seed_default_criteria(conn); conn.close()
print(f"Initialized {DB_PATH}")
