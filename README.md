# SocialSync Backend

SocialSync is a backend service for a social event management platform, enabling users to discover events, interact through real-time chat, and manage their event participation.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Before you begin, ensure you have the following installed:
- Python 3.x
- pip (Python package manager)
- Git (optional, for cloning the repository)

### Setting Up the Development Environment

1. **Clone the Repository** (if using Git):
   ```bash
   git clone https://github.com/sharansarthak/SocialSync.git
   cd SocialSync
   ```

   If you're not using Git, download the project files and navigate to the project directory.

2. **Create a Virtual Environment**:
   ```bash
   python3 -m venv venv
   ```

   This command will create a virtual environment named `venv` in your project directory.

3. **Activate the Virtual Environment**:

   - On Windows:
     ```bash
     .\venv\Scripts\activate
     ```

   - On macOS and Linux:
     ```bash
     source venv/bin/activate
     ```

   Once activated, your command line will indicate the virtual environment, e.g., `(venv)`.

4. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

   This will install all necessary packages for the project.

### Configuration

- Set up your Firebase project and download the service account key if you are running on localhost. 
- Set the environment variable for the Firebase service account:
  - On Windows:
    ```bash
    set FIREBASE_SERVICE_ACCOUNT_BASE64=<Your Base64 Encoded Key>
    ```

  - On macOS and Linux:
    ```bash
    export FIREBASE_SERVICE_ACCOUNT_BASE64=<Your Base64 Encoded Key>
    ```

### Running the Application

1. **Start the Flask Server**:
   ```bash
   flask run
   ```

   This will start the Flask application on `http://127.0.0.1:5000`.

2. **Access the Application**:
   - The application will be accessible on `http://127.0.0.1:5000`.
   - Use Postman or a similar tool to interact with the API endpoints.

## Built With

- Flask - The web framework used.
- Firebase - Backend and Database service.

