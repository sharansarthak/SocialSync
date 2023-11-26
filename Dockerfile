# Use an updated base image
FROM python:3.8-buster

# Copy your application code to the container
COPY . /app

# Set the working directory in the container
WORKDIR /app

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
export FIREBASE_CREDENTIALS="socialsync-35f38-firebase-adminsdk-krv15-f56e160fdb.json"

# Specify the command to run on container start
CMD ["python", "run.py"]
