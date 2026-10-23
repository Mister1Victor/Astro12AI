FROM python:3.10-slim

WORKDIR /code

# Установка зависимостей
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Копирование проекта (включая knowledge_base, data и т.д.)
COPY . .

# Открываем порт для HF
EXPOSE 7860

# Запуск модифицированного main.py
CMD ["python", "main.py"]
