FROM python:3.11-slim

# Set working directory
WORKDIR /workspace

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the default port (typically 8000, though Railway/Render override this)
EXPOSE 8000

# Start FastAPI server using the PORT environment variable if provided, or default to 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
