import os
import sys
import subprocess
import json

# Define log file
LOG_FILE = "/tmp/deployment_script.log"

# Function to check if the script has already been executed
def has_run_before():
    # Check if log file exists and is not empty
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as log:
            last_run = log.read().strip()
            return last_run == "completed"
    return False

# Function to log the status
def log_status(status):
    with open(LOG_FILE, "w") as log:
        log.write(status)

# Function to log the command execution
def log_command(command):
    with open(LOG_FILE, "a") as log:
        log.write(f"Executed: {command}\n")

# Function to execute system commands and check for errors
def run_command(command):
    # Ensure the log file exists before reading
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as log:
            log.write("")  # Create an empty log file if it doesn't exist
    
    # Check if the command was already executed
    with open(LOG_FILE, "r") as log:
        if command in log.read():
            print(f"Command already executed: {command}")
            return

    print(f"Running command: {command}")
    result = os.system(command)
    if result != 0:
        print(f"Error executing command: {command}")
        sys.exit(1)  # Exit the script on failure
    else:
        print(f"Successfully executed: {command}")
        log_command(command)  # Log the executed command

# Function to get the public IP
def get_public_ip():
    try:
        result = subprocess.check_output(["curl", "-s", "ifconfig.me"])
        return result.decode('utf-8').strip()
    except subprocess.CalledProcessError:
        print("Error fetching public IP.")
        sys.exit(1)

# Function to list available scripts in package.json
def get_available_scripts():
    try:
        with open("package.json", "r") as f:
            package_data = json.load(f)
        if "scripts" in package_data:
            return package_data["scripts"]
        else:
            print("No scripts found in package.json.")
            return {}
    except (json.JSONDecodeError, FileNotFoundError):
        print("Error reading package.json.")
        return {}

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

    # Step 4: Automatically Identify Available Scripts from package.json
    scripts = get_available_scripts()
    if scripts:
        print("Available scripts in package.json:")
        for script_name in scripts:
            print(f"- {script_name}")
        
        # Add each script to pm2 without starting it
        for script_name in scripts:
            run_command(f"pm2 start npm --name {script_name} -- run {script_name}")
        
        # Step 5: Ask the user which script to run
        user_input = input(f"Which script would you like to run from the list? (e.g., build, dev, start): ").strip()
        if user_input in scripts:
            run_command(f"pm2 start {user_input}")
        else:
            print(f"Invalid script choice. Skipping script start.")
    
    # Step 6: Start Nginx server
    run_command("sudo systemctl start nginx")

    # Step 7: Ask for the listening port and proxy pass
    listen_port = input("Enter the port for Nginx to listen on (e.g., 8081): ").strip()
    proxy_pass = input("Enter the proxy pass (e.g., http://localhost:3001): ").strip()

    # Step 8: Create Nginx configuration dynamically based on user input
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

    # Step 9: Restart Nginx to apply the new config
    run_command("sudo systemctl restart nginx")

    # Step 10: Get and print the public IP
    public_ip = get_public_ip()
    print(f"Visit your website at {public_ip}")

    # Mark script as completed
    log_status("completed")

    print("Deployment completed successfully!")

except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)
