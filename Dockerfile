FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set BASE_URL for baseline endpoint to use internally
ENV BASE_URL=http://localhost:7860

EXPOSE 7860

# Run with single worker (state is not shared across workers)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
