# Scandy Installation Guide (Portainer)

The easiest and recommended way to install Scandy is using a Portainer Stack.

## ⛴️ Step-by-Step Installation

1.  **Open Portainer** and navigate to your environment (e.g., `local`).
2.  Go to **Stacks** and click **Add stack**.
3.  Give the stack a name: `scandy`.
4.  In the **Web editor**, paste the following configuration:

```yaml
version: "3.9"

services:
  app:
    image: scandy:latest
    container_name: scandy-app
    restart: unless-stopped
    depends_on:
      mongodb:
        condition: service_healthy
    environment:
      - FLASK_ENV=production
      - MONGO_URI=mongodb://mongodb:27017/scandy
      - SECRET_KEY=change_me_to_something_random
      - PORT=5000
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
      start_period: 20s

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

5.  (Optional) If you want to change the external port (e.g., to 5002), change the `ports` mapping to `"5002:5000"`.
6.  Click **Deploy the stack**.

## ⚙️ Important Environment Variables

If you choose to use the "Environment variables" section in Portainer, you can define these:

| Variable | Description | Default |
| :--- | :--- | :--- |
| `PORT` | The internal port the app listens on (default 5000). | `5000` |
| `SECRET_KEY` | A secret string for session security. | `change_me` |
| `MONGO_URI` | Connection string to MongoDB. | `mongodb://mongodb:27017/scandy` |

## 📁 Persistence

All your data (uploads, database, logs, sessions) is stored in named Docker volumes (`scandy_*`). Even if you delete the container, your data will be safe as long as the volumes exist.
