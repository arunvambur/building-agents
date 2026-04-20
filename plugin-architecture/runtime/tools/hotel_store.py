
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.utilities import SQLDatabase

from runtime.infrastructure.llm_models import get_llm



# -----------------------------------------------------------------------------
# Instantiate the SQLite database
# -----------------------------------------------------------------------------

def get_hotel_info_store():
    llm_model = get_llm()
    hotel_db = SQLDatabase.from_uri("sqlite:///data/hotel_db/cornwall_hotels.db")
    return SQLDatabaseToolkit(db=hotel_db, llm=llm_model)

# hotel_db_toolkit_tools = get_hotel_info_store().get_tools()