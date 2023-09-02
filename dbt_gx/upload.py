import requests
import json
import base64

# Databricks instance host (replace with your own)
HOST = "https://<DATABRICKS-WORKSPACE-URL>"

# Databricks access token (replace with your own)
TOKEN = "<ACCESS-TOKEN>"

# The path in the Databricks workspace where you'd like to upload the script
workspace_path = "/Workspace/dbt-test/gx_dbt.py"

# Path to the local script to upload
local_path = "./gx_dbt.py"

# Read the Python script content
with open(local_path, 'r') as f:
    content = f.read()

# Encode the script content to base64
encoded_content = base64.b64encode(content.encode('utf-8')).decode()

# API endpoint for uploading to workspace
url = f"{HOST}/api/2.0/workspace/import"

# API request payload
payload = {
    "path": workspace_path,
    "format": "SOURCE",
    "language": "PYTHON",
    "content": encoded_content,
    "overwrite": True  # Set to False if you don't want to overwrite existing files
}

# API request headers
headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

# Make the API request
response = requests.post(url, headers=headers, json=payload)

# Check the response
if response.status_code == 200:
    print("Successfully uploaded the script to Databricks workspace.")
else:
    print("Failed to upload the script.")
    print("Response:", response.json())
