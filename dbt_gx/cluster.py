import os
import uuid
from databricks_api import DatabricksAPI

db = DatabricksAPI(
    host=os.environ.get("DATABRICKS_HOST", ""),
    token=os.environ.get("DATABRICKS_TOKEN", ""),
)

random_name = str(uuid.uuid4())

cluster_config = {
    "cluster_name": f"cluster-{random_name}",
    "spark_version": "PUT_DESIRED_SPARK_VERSION",
    "node_type_id": "COMPUTE_CAPACITY",
    "num_workers": 3,  # NO. OF WORKERS
    "autotermination_minutes": 20,  # INACTIVITY TIME FOR TERMINATION
}

response = db.cluster.create(**cluster_config)

if response.status_code == 200:
    print(f"Cluster {cluster_config['cluster_name']} created successfully")
else:
    print(f"Failed to create cluster: {response.json()}")
