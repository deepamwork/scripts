import os
token=input("Enter token: ").strip()
userorg=input("Enter user/org name: ").strip()
repo=input("Enter repo name: ").strip()

os.system(f"git clone https://{token}@github.com/{userorg}/{repo}.git")