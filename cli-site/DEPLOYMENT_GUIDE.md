# Deployment Guide: Hosting Your SSH Portfolio on a VPS

This guide will walk you through deploying your `portfolio-tui` to a typical Linux VPS (like Ubuntu or Debian) using `systemd` so that it runs in the background continuously and restarts automatically.

## Prerequisites
- A VPS (Virtual Private Server) with SSH access.
- Your updated `cli-site` code.

## 1. Prepare and Build the App

First, make sure you compile the application for Linux (assuming your VPS is Linux). On your local machine, run:

```bash
GOOS=linux GOARCH=amd64 go build -o portfolio-tui .
```

*Note: If your VPS runs on ARM (like an AWS Ampere instance or Raspberry Pi), use `GOARCH=arm64`.*

## 2. Transfer Files to the VPS

Use `scp` or `rsync` to copy the necessary files to your server. You only need the compiled binary and the configuration file (`portfolio.yml`):

```bash
scp portfolio-tui portfolio.yml portfolio.service root@<your_vps_ip>:/root/
```

## 3. Server Setup

SSH into your server:

```bash
ssh root@<your_vps_ip>
```

We'll create a dedicated user for security purposes and put the app in `/opt/`.

```bash
# Create a user (without a login shell)
sudo useradd -r -s /bin/false portfolio

# Create the directory
sudo mkdir -p /opt/portfolio-tui

# Move the files into place
sudo cp /root/portfolio-tui /root/portfolio.yml /opt/portfolio-tui/

# Set the correct permissions
sudo chown -R portfolio:portfolio /opt/portfolio-tui
sudo chmod +x /opt/portfolio-tui/portfolio-tui
```

## 4. Install the Systemd Service

We've provided a `portfolio.service` file. Move it to the systemd directory:

```bash
sudo cp /root/portfolio.service /etc/systemd/system/
sudo systemctl daemon-reload
```

## 5. Start the Application

Enable it to start automatically on boot, and start it now:

```bash
sudo systemctl enable portfolio
sudo systemctl start portfolio
```

To check its status:
```bash
sudo systemctl status portfolio
```

## 6. Accessing Your Portfolio

The application should now be live on port `2222`! 

To test it, run this from anywhere:
```bash
ssh -p 2222 anything@<your_vps_ip>
```

*(Note: Anyone can put any username or password, the `gliderlabs/ssh` package we're using skips strict authentication).*

### Wait, how do I use normal port 22? Wait, won't it conflict?
By default, the actual VPS SSH daemon (`sshd`) runs on port 22, allowing YOU to manage the server. Your portfolio app runs silently alongside it on port `2222`. 

If you want people to connect simply by typing `ssh yourdomain.com` without specifying `-p 2222`, you'll need to move your `sshd` to a different port (like 2222 or 443), and reconfigure `main.go` to listen on port `22` (this requires binding as `root` via `setcap cap_net_bind_service=+ep /opt/portfolio-tui/portfolio-tui`). For now, port 2222 is the safest approach and very common for these TUI apps!
