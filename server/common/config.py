import os
from dotenv import load_dotenv

load_dotenv()

AI_PROVIDER = os.getenv("AI_PROVIDER")
MODEL_NAME = os.getenv("MODEL_NAME")