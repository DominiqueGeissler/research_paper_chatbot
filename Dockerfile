# Start from a small Linux image with Python 3.12 installed
FROM python:3.12-slim

WORKDIR /app

# Let Python find the src/ package; print logs immediately
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# Install dependencies first, so Docker can reuse this layer
# when only your code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

EXPOSE 8501

CMD ["sh", "-c", "python scripts/prepare.py && streamlit run ui/app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true"]