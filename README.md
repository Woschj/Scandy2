# Scandy - Inventory Management System

Scandy is a lightweight and flexible inventory management system built with Flask and MongoDB. It is designed to be easily deployed using Docker and managed via Portainer.

## 🚀 Quick Start with Docker Compose

The easiest way to get Scandy up and running is using Docker Compose.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-repo/scandy.git
    cd scandy
    ```

2.  **Create a `.env` file:**
    Copy the example environment file and adjust the values:
    ```bash
    cp env.example .env
    ```

3.  **Start the application:**
    ```bash
    docker-compose up -d
    ```

4.  **Access Scandy:**
    Open your browser and navigate to `http://localhost:5000`.

## ⛴️ Installation via Portainer (Plug-and-Play)

Scandy is optimized for deployment as a **Portainer Stack**. This allows for a clean "Plug-and-Play" installation.

### Method 1: Repository (Recommended)
1.  In Portainer, go to **Stacks** > **Add stack**.
2.  Select **Repository**.
3.  **Repository URL:** `https://github.com/your-repo/scandy.git`
4.  **Compose path:** `docker-compose.yml`
5.  **Environment variables:** Add the variables listed below.
6.  Click **Deploy the stack**.

### Method 2: Web Editor
1.  In Portainer, go to **Stacks** > **Add stack**.
2.  Select **Web editor**.
3.  Paste the content of the `docker-compose.yml` file.
4.  **Environment variables:** Add the variables listed below.
5.  Click **Deploy the stack**.

## ⚙️ Configuration (Environment Variables)

Add these variables in the Portainer UI under **Environment variables** for the stack:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `APP_PORT` | The port the application will be accessible on. | `5000` |
| `MONGO_ROOT_USER` | Root username for MongoDB. | `admin` |
| `MONGO_ROOT_PASSWORD` | Root password for MongoDB (Change this!). | `change_me_immediately` |
| `MONGODB_DB` | Name of the database. | `scandy` |
| `SECRET_KEY` | Flask secret key for session encryption. | `change_me_secret_key` |
| `FLASK_ENV` | Flask environment (`production` or `development`). | `production` |
| `TIMEZONE` | System timezone (e.g., `Europe/Berlin`). | `Europe/Berlin` |
| `ME_PORT` | Port for Mongo Express (Web UI for MongoDB). | `8081` |
| `ME_BASICAUTH_USER` | Basic auth username for Mongo Express. | `admin` |
| `ME_BASICAUTH_PASSWORD` | Basic auth password for Mongo Express. | `change_me_immediately` |

## 📁 Persistent Data

Scandy uses Docker volumes to ensure your data is persistent:

*   `mongodb_data`: Stores the MongoDB database files.
*   `app_uploads`: Stores uploaded files.
*   `app_backups`: Stores database backups.
*   `app_logs`: Stores application logs.
*   `app_sessions`: Stores user session data.

## 🛠️ Development

If you want to contribute to Scandy, you can use the following commands:

*   `make build`: Build the Docker images.
*   `make test`: Run the test suite.
*   `make lint`: Run linting checks.
*   `make format`: Format the code.

## 📄 License

This project is licensed under the MIT License.
