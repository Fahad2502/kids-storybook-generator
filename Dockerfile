# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
# This is an optimization step
COPY ./requirements.txt /app/requirements.txt

# Install any dependencies specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . /app

# The port that FastAPI runs on (must match your frontend fetch calls)
EXPOSE 8000

# Command to run the application using Uvicorn
# Note: We use 0.0.0.0 to make the server accessible externally
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]