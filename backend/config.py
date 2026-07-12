import os

from dotenv import load_dotenv

load_dotenv()


class Settings:

    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    SELF_URL = os.getenv("SELF_URL")

    PORT = int(os.getenv("PORT", "8080"))

    ENV = os.getenv("ENV", "production").lower()

    MODEL_NAME = os.getenv(
        "MODEL_NAME",
        "llama-3.3-70b-versatile"
    )

    TEMPERATURE = float(
        os.getenv("TEMPERATURE", "0.2")
    )

    @property
    def IS_DEVELOPMENT(self):
        return self.ENV == "development"


settings = Settings()