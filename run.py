from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Get the PORT environment variable
    port = int(os.environ.get('PORT', 8080))

    # Run the app on host 0.0.0.0 and on the specified port
    app.run(host='0.0.0.0', port=port)
