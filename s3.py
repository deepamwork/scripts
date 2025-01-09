import os
import json
import typer
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from typing import Optional

# Create a Typer app instance
app = typer.Typer()

# Path to store the credentials (in the same directory as the script)
CONFIG_FILE = "aws_credentials.json"

# Create an S3 client with AWS Access Key and Secret Key from the config
def create_s3_client(access_key: str, secret_key: str):
    """Create an S3 client with given AWS credentials"""
    return boto3.client('s3', aws_access_key_id=access_key, aws_secret_access_key=secret_key)

# Store AWS credentials securely in a JSON file
def store_credentials(access_key: str, secret_key: str):
    """Store AWS credentials in a JSON file"""
    credentials = {
        'access_key': access_key,
        'secret_key': secret_key
    }

    with open(CONFIG_FILE, 'w') as configfile:
        json.dump(credentials, configfile, indent=4)
    print(f"Credentials stored in {CONFIG_FILE}")

# Load AWS credentials from the JSON file
def load_credentials() -> Optional[dict]:
    """Load AWS credentials from the JSON file"""
    if not os.path.exists(CONFIG_FILE):
        print(f"{CONFIG_FILE} not found! Please provide your credentials.")
        return None

    with open(CONFIG_FILE, 'r') as configfile:
        credentials = json.load(configfile)

    if 'access_key' not in credentials or 'secret_key' not in credentials:
        print("AWS Access Key or Secret Key is missing in the config file.")
        return None

    return credentials

# AWS Configuration group
@app.command(name="configure-aws")
def configure_aws():
    """Prompt user for AWS credentials and store them in the JSON file"""
    access_key = typer.prompt("Enter your AWS Access Key")
    secret_key = typer.prompt("Enter your AWS Secret Key", hide_input=True)

    store_credentials(access_key, secret_key)

# S3 Operations group
@app.command(name="lsb")
def list_buckets():
    """List all S3 buckets in the AWS account"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        response = s3_client.list_buckets()
        if 'Buckets' in response:
            print("Buckets:")
            for bucket in response['Buckets']:
                print(f" - {bucket['Name']}")
        else:
            print("No buckets found.")
    except ClientError as e:
        print(f"Error listing buckets: {e}")


@app.command(name="lsf")
def list_files(bucket: str):
    """List files in the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])
    try:
        response = s3_client.list_objects_v2(Bucket=bucket)
        if 'Contents' not in response:
            print(f"No objects found in bucket {bucket}.")
        else:
            for obj in response['Contents']:
                print(f" - {obj['Key']}")
    except ClientError as e:
        print(f"Error listing files in bucket {bucket}: {e}")


@app.command(name="rdf")
def read_file(bucket: str, filename: str):
    """Read a file from the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        response = s3_client.get_object(Bucket=bucket, Key=filename)
        file_content = response['Body'].read().decode('utf-8')
        print(f"Contents of {filename} from S3:")
        print(file_content)
    except ClientError as e:
        print(f"Error reading file {filename} from S3: {e}")
        print("Possible errors could include:")
        print("  - Invalid S3 bucket or key.")
        print("  - Missing or incorrect AWS credentials.")


@app.command(name="rmf")
def remove_file(bucket: str, key: str):
    """Remove a file from the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])
    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        print(f"Successfully deleted {key} from bucket {bucket}.")
    except ClientError as e:
        print(f"Error deleting {key} from bucket {bucket}: {e}")


@app.command(name="upf")
def upload_file(bucket: str, file_path: str, key: Optional[str] = None):
    """Upload a file to the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    if not os.path.isfile(file_path):
        print(f"The file {file_path} does not exist.")
        return
    
    if key is None:
        key = os.path.basename(file_path)  # If no key provided, use the filename as the key

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        s3_client.upload_file(file_path, bucket, key)
        print(f"Successfully uploaded {file_path} to bucket {bucket} as {key}.")
    except NoCredentialsError:
        print("AWS credentials not found.")
    except ClientError as e:
        print(f"Error uploading {file_path} to bucket {bucket}: {e}")


@app.command(name="dnf")
def download_file(bucket: str, key: str, download_path: Optional[str] = None):
    """Download a file from the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    if download_path is None:
        download_path = key  # If no download path provided, use the key as the download file name

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        s3_client.download_file(bucket, key, download_path)
        print(f"Successfully downloaded {key} from bucket {bucket} to {download_path}.")
    except NoCredentialsError:
        print("AWS credentials not found.")
    except ClientError as e:
        print(f"Error downloading {key} from bucket {bucket}: {e}")


@app.command(name="synctos3")
def sync_to_s3(bucket: str, local_dir: str):
    """Sync a local directory to the specified S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    if not os.path.isdir(local_dir):
        print(f"The directory {local_dir} does not exist.")
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    for root, dirs, files in os.walk(local_dir):
        for file in files:
            file_path = os.path.join(root, file)
            s3_key = os.path.relpath(file_path, local_dir)

            try:
                s3_client.upload_file(file_path, bucket, s3_key)
                print(f"Successfully uploaded {file_path} to bucket {bucket}/{s3_key}.")
            except ClientError as e:
                print(f"Error uploading {file_path} to {bucket}/{s3_key}: {e}")


@app.command(name="syncme")
def sync_from_s3(bucket: str, local_dir: str):
    """Sync an S3 bucket to a local directory"""
    credentials = load_credentials()
    if credentials is None:
        return

    if not os.path.exists(local_dir):
        os.makedirs(local_dir)

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        paginator = s3_client.get_paginator('list_objects_v2')
        for page in paginator.paginate(Bucket=bucket):
            if 'Contents' in page:
                for obj in page['Contents']:
                    s3_key = obj['Key']
                    local_path = os.path.join(local_dir, s3_key)

                    # Create directories if they don't exist
                    local_file_dir = os.path.dirname(local_path)
                    if not os.path.exists(local_file_dir):
                        os.makedirs(local_file_dir)

                    # Download the file
                    s3_client.download_file(bucket, s3_key, local_path)
                    print(f"Successfully downloaded {s3_key} from bucket {bucket} to {local_path}.")

    except ClientError as e:
        print(f"Error syncing from bucket {bucket} to local directory {local_dir}: {e}")


# New Commands for bucket operations with short forms

@app.command(name="crb")
def create_bucket(bucket_name: str):
    """Create a new S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        s3_client.create_bucket(Bucket=bucket_name)
        print(f"Successfully created bucket {bucket_name}.")
    except ClientError as e:
        print(f"Error creating bucket {bucket_name}: {e}")


@app.command(name="emb")
def empty_bucket(bucket_name: str):
    """Empty an S3 bucket (remove all objects but keep the bucket)"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                s3_client.delete_object(Bucket=bucket_name, Key=obj['Key'])
                print(f"Deleted {obj['Key']} from bucket {bucket_name}.")
        else:
            print(f"No objects to delete in bucket {bucket_name}.")
    except ClientError as e:
        print(f"Error emptying bucket {bucket_name}: {e}")


@app.command(name="rmb")
def remove_bucket(bucket_name: str):
    """Delete an S3 bucket"""
    credentials = load_credentials()
    if credentials is None:
        return

    s3_client = create_s3_client(credentials['access_key'], credentials['secret_key'])

    try:
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"Successfully deleted bucket {bucket_name}.")
    except ClientError as e:
        print(f"Error deleting bucket {bucket_name}: {e}")


# Main execution
if __name__ == "__main__":
    app()
