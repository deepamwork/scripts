import os
import sys

# Define log file
LOG_FILE = "/tmp/deployment_script.log"

# Function to check if the script has already been executed
def has_run_before():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log:
            last_run = log.read().strip()
            return last_run == "completed"
    return False

# Function to log the status
def log_status(status):
    with open(LOG_FILE, "w") as log:
        log.write(status)

# Function to execute system commands and check for errors
def run_command(command):
    print(f"Running command: {command}")
    result = os.system(command)
    if result != 0:
        print(f"Error executing command: {command}")
        sys.exit(1)  # Exit the script on failure
    else:
        print(f"Successfully executed: {command}")

# Check if the script has been executed before
if has_run_before():
    print("Script has already been executed. Exiting.")
    sys.exit(0)

# Begin script execution
try:
    # Step 1: Update the system and install dependencies
    run_command("sudo apt update")
    run_command("sudo apt -y install nginx certbot python3-certbot-nginx nodejs npm")
    run_command("sudo npm install -g pm2")

    # Step 2: Clone the repository
    repo_name = input("Enter the name of the repository (e.g., https://github.com/user/repo.git): ")
    name_repo = repo_name.split("/")[-1].replace(".git", "")
    
    if not os.path.exists(name_repo):
        run_command(f"git clone {repo_name}")
    os.chdir(name_repo)
    
    # Step 3: Install Node.js dependencies
    run_command("npm install")

    # Step 4: Ask for the commands to run
    user_input = input("Enter the commands to run (comma-separated, e.g., build, dev, start): ").strip()
    commands = [cmd.strip() for cmd in user_input.split(',')]

    # Execute each command based on user input
    for cmd in commands:
        if cmd == "build":
            run_command("pm2 start npm --name first-backend-build -- run build")
        elif cmd == "dev":
            run_command("pm2 start npm --name first-backend-dev -- run dev")
        elif cmd == "start":
            run_command("pm2 start npm --name first-backend -- run start")
        else:
            print(f"Unknown command: {cmd}. Skipping.")
    
    # Step 5: Start Nginx server
    run_command("sudo systemctl start nginx")

    # Step 6: Ask for the listening port and proxy pass
    listen_port = input("Enter the port for Nginx to listen on (e.g., 8081): ").strip()
    proxy_pass = input("Enter the proxy pass (e.g., http://localhost:3001): ").strip()

    # Step 7: Create Nginx configuration dynamically based on user input
    config_default = f"""server {{
  listen {listen_port}; # Listen on port {listen_port} for incoming requests
  server_name localhost; # You can change this to your domain if needed
  location / {{
    proxy_pass {proxy_pass}; # Proxy requests to {proxy_pass}
    proxy_set_header Host $host; # Preserve the original host
    proxy_set_header X-Real-IP $remote_addr; # Pass the client's IP address
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for; # Forward client IP addresses
    proxy_set_header X-Forwarded-Proto $scheme; # Forward the protocol (http or https)
  }}
}}"""
    
    # Write the configuration to the Nginx default site
    with open("/etc/nginx/sites-enabled/default", "w") as f:
        f.write(config_default)

    # Step 8: Restart Nginx to apply the new config
    run_command("sudo systemctl restart nginx")

    # Mark script as completed
    log_status("completed")

    print("Deployment completed successfully!")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)
