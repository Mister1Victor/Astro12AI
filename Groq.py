import os
import requests
from dotenv import load_dotenv

# Загружаем переменные из вашего .env файла
load_dotenv()

# Берем ключ из .env или просим ввести вручную, если его там нет
api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    api_key = input("Введите ваш GROQ_API_KEY: ")

url = "https://api.groq.com/openai/v1/models"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

try:
    response = requests.get(url, headers=headers)
    response.raise_for_status()  # Проверка на ошибки (например, неверный ключ)

    data = response.json()
    models = data.get("data", [])

    print(f"\n✅ Найдено моделей: {len(models)}\n")
    print("📋 Полный список доступных моделей Groq:")
    print("-" * 40)

    # Сортируем модели по имени для удобства
    for model in sorted(models, key=lambda x: x["id"]):
        model_id = model["id"]
        # Добавляем пометку для самых популярных моделей
        note = ""
        if "llama3-70b" in model_id or "llama-3.3-70b" in model_id:
            note = " ⭐ (Рекомендуется: баланс скорости и ума)"
        elif "llama3-8b" in model_id:
            note = " ⚡ (Самая быстрая, но проще)"
        elif "qwen" in model_id:
            note = " 🧠 (Отлично рассуждает)"

        print(f"• {model_id}{note}")

    print("-" * 40)
    print("💡 Скопируйте любое название выше и вставьте в ваш .env файл в переменную MODEL_NAME")

except requests.exceptions.HTTPError as e:
    print(f"❌ Ошибка HTTP: {e}")
    print("Проверьте, правильно ли указан GROQ_API_KEY в файле .env")
except Exception as e:
    print(f"❌ Произошла ошибка: {e}")
