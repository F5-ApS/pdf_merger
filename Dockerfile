FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libmupdf-dev \
    && apt-get clean

# Copy requirements and install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the backend application
COPY backend /app


# Expose the Flask port
EXPOSE 8080

# Command to run the backend
CMD ["python", "Pdf_merger.py"]
