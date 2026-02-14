# Scandy - Inventory Management System

Scandy is a lightweight and flexible inventory management system built with Flask and MongoDB. It is designed to be easily deployed using Docker and managed via Portainer.

## 🚀 Quick Start with Docker Compose

The easiest way to get Scandy up and running locally:

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/scandy.git
    cd scandy
    ```

2.  **Create a `.env` file:**
    ```bash
    cp env.example .env
    ```

3.  **Start the application:**
    ```bash
    docker-compose up -d
    ```

4.  **Access Scandy:**
    Open `http://localhost:5000`.

## ⛴️ Portainer Installation (Recommended)

To install Scandy as a **Stack** in Portainer (failproof method):

1.  Log in to your Portainer instance.
2.  Go to **Stacks** > **Add stack**.
3.  Give the stack a name (e.g., `scandy`).
4.  Select **Web editor** and paste the following YAML configuration:

```yaml
version: "3.9"

services:
  app:
    image: scandy:latest
    # Or build from source:
    # build: https://github.com/woschj/scandy2.git
    container_name: scandy-app
    restart: unless-stopped
    depends_on:
      - mongodb
    environment:
      - FLASK_ENV=production
      - MONGO_URI=mongodb://mongodb:27017/scandy
      - SECRET_KEY=change_me_to_something_random
    ports:
      - "5000:5000"
    volumes:
      - scandy_uploads:/app/app/uploads
      - scandy_backups:/app/app/backups
      - scandy_logs:/app/app/logs
      - scandy_sessions:/app/app/flask_session
    networks:
      - scandy-net

  mongodb:
    image: mongo:7
    container_name: scandy-mongodb
    restart: unless-stopped
    volumes:
      - scandy_db_data:/data/db
    networks:
      - scandy-net
    healthcheck:
      test: ["CMD", "mongosh", "--eval", "db.adminCommand('ping')"]
      interval: 10s
      timeout: 5s
      retries: 5

networks:
  scandy-net:
    driver: bridge

volumes:
  scandy_db_data:
  scandy_uploads:
  scandy_backups:
  scandy_logs:
  scandy_sessions:
```

5.  Click **Deploy the stack**.

## ⚙️ Configuration (Environment Variables)

| Variable | Description | Default |
| :--- | :--- | :--- |
| `APP_PORT` | The port the application will be accessible on. | `5000` |
| `MONGO_URI` | Full MongoDB connection string. | `mongodb://mongodb:27017/scandy` |
| `SECRET_KEY` | Flask secret key for session encryption. | `change_me_secret_key` |
| `FLASK_ENV` | Flask environment (`production` or `development`). | `production` |
| `TIMEZONE` | System timezone. | `Europe/Berlin` |

## 📁 Persistent Data

Scandy uses Docker volumes to ensure your data is persistent. In Portainer, these are automatically created as named volumes.

## 🛠️ Development

*   `make build`: Build the Docker images.
*   `make test`: Run the test suite.
*   `make lint`: Run linting checks.

## 📄 License

This project is licensed under the MIT License.
