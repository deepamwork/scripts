import os
os.system("sudo apt update")
os.system("sudo apt -y install nginx certbot python3-certbot-nginx nodejs npm")
os.system("sudo npm install -g pm2")
repo_name=input("Enter the name of the repository: ").strip()
os.system(f"git clone {repo_name}")
os.system(f"cd {repo_name}")
os.system("npm install")
ask=input("Is it frontend(f) or backend(b)?")
if ask=="f":
    os.system("npm run build")
elif ask=="b":
    os.system("npm run start")
os.system("sudo systemctl start nginx")
config_default=r"""server {
  listen 8081; # Listen on port 8081 for incoming requests
  server_name localhost; # You can change this to your domain if needed
  location / {
    proxy_pass http://localhost:3001; # Proxy requests to localhost:80
    proxy_set_header Host $host; # Preserve the original host
    proxy_set_header X-Real-IP $remote_addr; # Pass the client's IP address
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; # Forward client IP addresses
    proxy_set_header X-Forwarded-Proto $scheme; # Forward the protocol (http or https)
  }
}"""
with open("/etc/nginx/sites-enabled/default", "w") as f:    
    f.write(config_default)
os.system("sudo systemctl restart nginx")
