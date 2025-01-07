import os
name=input("Enter name of folder: ").strip()
os.system(f"cd {name}")
os.system("git restore .")
os.system("git pull")
os.system("npm install")
os.system(f"pm2 restart {name}")