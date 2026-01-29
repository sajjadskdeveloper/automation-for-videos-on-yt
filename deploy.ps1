# deploy.ps1 - Use this on your LOCAL Windows machine

$zipName = "deploy_package.zip"
$exclude = @("venv", "__pycache__", ".git", "downloads", "uploads", "outputs", "*.mp4", "*.zip", ".env")

echo "Creating deployment package..."

# Remove old zip if exists
if (Test-Path $zipName) {
    Remove-Item $zipName
}

# Get list of files to include
$files = Get-ChildItem -Path . -Exclude $exclude

# Create the zip file
Compress-Archive -Path $files -DestinationPath $zipName -Force

echo "Package created: $zipName"
echo "--------------------------------------------------------"
echo "Run the following command to upload to your DigitalOcean server:"
echo "scp $zipName root@<YOUR_SERVER_IP>:/root/app/"
echo "--------------------------------------------------------"
echo "Then allow SSH into your server, unzip, and run ./deploy_setup.sh"
