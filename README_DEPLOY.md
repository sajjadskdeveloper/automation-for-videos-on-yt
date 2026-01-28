# Deployment Instructions for DigitalOcean

This project is ready for deployment on a DigitalOcean Droplet (Ubuntu).

## Prerequisites
- A DigitalOcean Account
- An Ubuntu Droplet (2GB RAM recommended for video processing)
- SSH Access to the Droplet

## Deployment Steps

1.  **Transfer Files**:
    Upload your project files to the server. You can use direct upload, SCP, or git clone.
    *Note: Do not upload the `venv` directory or `__pycache__`.*

    ```bash
    scp -r  /local/path/to/project root@your_droplet_ip:/var/www/video_app
    ```

2.  **Run Setup Script**:
    SSH into your server and run the setup script.

    ```bash
    ssh root@your_droplet_ip
    cd /var/www/video_app
    chmod +x deploy_setup.sh
    ./deploy_setup.sh
    ```

    *If `deploy_setup.sh` fails due to line endings (windows vs linux), run `sed -i 's/\r$//' deploy_setup.sh` to fix it.*

3.  **Start the Server**:
    For testing, you can run:
    ```bash
    ./venv/bin/gunicorn -c gunicorn_config.py app:app
    ```

4.  **Production Setup (Systemd Service)**:
    To keep the app running in the background, create a systemd service.

    Create file `/etc/systemd/system/video_app.service`:
    ```ini
    [Unit]
    Description=Gunicorn instance to serve video app
    After=network.target

    [Service]
    User=root
    Group=www-data
    WorkingDirectory=/var/www/video_app
    Environment="PATH=/var/www/video_app/venv/bin"
    ExecStart=/var/www/video_app/venv/bin/gunicorn -c gunicorn_config.py app:app

    [Install]
    WantedBy=multi-user.target
    ```

    Enable and start:
    ```bash
    systemctl start video_app
    systemctl enable video_app
    ```

5.  **Nginx Proxy (Optional but Recommended)**:
    Install Nginx and configure it to proxy requests to port 5000.

    ```bash
    sudo apt-get install nginx
    ```
    
    Edit `/etc/nginx/sites-available/default`:
    ```nginx
    server {
        listen 80;
        server_name your_domain_or_ip;

        location / {
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
        }
    }
    ```
    restart nginx: `systemctl restart nginx`

## Notes
- **FFmpeg**: The script installs `ffmpeg`, which is required for `moviepy`.
- **Timeouts**: Video processing can take time. standard timeouts might need increasing in Nginx and Gunicorn (already set to 300s in gunicorn_config).
