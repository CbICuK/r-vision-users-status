from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    CONTAINERNAME=os.getenv("CONTAINERNAME")