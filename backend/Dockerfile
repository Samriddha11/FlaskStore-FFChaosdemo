# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install Redis client for communication with Redis
RUN apt-get update && apt-get install -y redis-tools

# Make port 8989 available to the world outside this container
EXPOSE 8989

# Run app.py when the container launches
CMD ["python", "app.py"]
