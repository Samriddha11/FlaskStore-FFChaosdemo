# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install curl, ping, telnet, and necessary dependencies
RUN apt-get update && apt-get install -y \
    curl \
    vim \
    iputils-ping \
    telnet \
    && rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt


# Expose the port the app runs on
EXPOSE 5000

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Define the command to run the app using Flask
CMD ["flask", "run", "--host=0.0.0.0"]