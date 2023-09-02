import great_expectations as gx
from great_expectations.core.batch import BatchRequest, RuntimeBatchRequest
import pyspark as ps
import datetime
import boto3
import json
import os

# Need to configure databricks scopes through your local machine.
aws_access_key_id = dbutils.secrets.get(scope="aws", key="aws_access_key_id")
aws_secret_access_key = dbutils.secrets.get(scope="aws", key="aws_secret_access_key")

s3_client = boto3.client('s3', 
                         region_name="ap-south-1", 
                         aws_access_key_id=aws_access_key_id, 
                         aws_secret_access_key=aws_secret_access_key)


def init_data_context(root_dir: str) -> gx.DataContext:
    # Define config
    data_context_config = gx.data_context.types.base.DataContextConfig(
        store_backend_defaults=gx.data_context.types.base.FilesystemStoreBackendDefaults(
            root_directory=root_dir
        )
    )
    # Init context
    context = gx.get_context(project_config=data_context_config)

    return context

# Pointing to the S3 mount on DBFS
context = init_data_context(root_dir="/dbfs/mnt/mount_s3/great_expectations/")

##

def register_spark_data_source(context: gx.DataContext):
    source = gx.datasource.Datasource(
        name="spark_data_source",
        execution_engine={
            "module_name": "great_expectations.execution_engine",
            "class_name": "SparkDFExecutionEngine"
        },
        data_connectors={
            f"spark_data_source_connector": {
                "class_name": "RuntimeDataConnector",
                "batch_identifiers": ["timestamp"]
            }
        }
    )
    
    context.add_or_update_datasource(datasource=source)


register_spark_data_source(context)

##

def create_batch_request(df: ps.sql.DataFrame, df_name: str, timestamp: str) -> gx.core.batch.RuntimeBatchRequest:
    '''
    Creates a batch request from a Spark data frame.
    '''
    runtime_batch_request = gx.core.batch.RuntimeBatchRequest(
        datasource_name="spark_data_source",
        data_connector_name="spark_data_source_connector",
        data_asset_name="spark_batch_{}_{}".format(df_name, timestamp),
        runtime_parameters={"batch_data": df},
        batch_identifiers={
            "timestamp": timestamp,
        }
    )
    return runtime_batch_request

##

def current_timestamp() -> str:
    '''
    Returns the current timestamp.
    '''
    return datetime.datetime.utcnow().isoformat()

##
###You can add you spark dataframe here from any existing data. e.g.;
# file_type = "csv"
# infer_schema = True
# first_row_is_header = True
# delimiter = ","  # Assuming comma as the delimiter for a CSV file
# file_location = "/mnt/mount_s3/your_data.csv"

### Read the file using Spark
# df = spark.read.format(file_type) \
#   .option("inferSchema", infer_schema) \
#   .option("header", first_row_is_header) \
#   .option("sep", delimiter) \
#   .load(file_location)

### Display the first few rows of the DataFrame for verification if its neccessary.
# df.show()
##

timestamp = current_timestamp()
batch_request = create_batch_request(df=df, df_name=table, timestamp=timestamp)

##

# Run the default onboarding profiler on the batch request
result = context.assistants.onboarding.run(
    batch_request=batch_request,
    exclude_column_names=[],
)

# Get the suite with specific name
suite_name = "data_quality"
suite = result.get_expectation_suite(
    expectation_suite_name=suite_name
)

# Plot results
result.plot_expectations_and_metrics()

context.add_or_update_expectation_suite(expectation_suite=suite)

##Check Point

checkpoint_name="test_checkpoint"

# Create and persist checkpoint to store result for multiple batches
context.add_or_update_checkpoint(
    name = checkpoint_name,
    config_version = 1,
    class_name = "SimpleCheckpoint",
    validations = [
        {"expectation_suite_name": suite_name}
    ]
)

checkpoint_result = context.run_checkpoint(
    checkpoint_name=checkpoint_name,
    batch_request=batch_request
)



##Extracting success_rate

def extract_success_rate_from_checkpoint_v2(context, checkpoint_result):
    result_ids = checkpoint_result.list_validation_result_identifiers()
    all_results = []
    
    # Retrieve all validation results using their identifiers
    for result_id in result_ids:
        expectation_suite_name = result_id.expectation_suite_identifier.expectation_suite_name
        run_id = result_id.run_id
        validation_result = context.get_validation_result(expectation_suite_name, run_id=run_id)
        all_results.append(validation_result)
    
    # Calculate the success rate across all validation results
    total_expectations = sum([len(res["results"]) for res in all_results])
    successful_expectations = sum([len([e for e in res["results"] if e["success"]]) for res in all_results])

    success_rate = (successful_expectations / total_expectations) * 100
    return success_rate

success_rate = extract_success_rate_from_checkpoint_v2(context, checkpoint_result)
print(success_rate)

# Save and show data_doc

def display_and_save_checkpoint_results(context: gx.DataContext, 
                                        result: gx.checkpoint.types.checkpoint_result.CheckpointResult, 
                                        s3_save_path: str):
    result_ids = result.list_validation_result_identifiers()
    
    # Iterate validations results
    for result_id in result_ids:
        docs = context.get_docs_sites_urls(resource_identifier=result_id)
        
        # Iterate and display docs
        for doc in docs:
            path = doc["site_url"]
            
            # Remove the file:// prefix from the URL
            if path.startswith("file://"):
                path = path[len("file://"):]

            # Display the HTML in the Databricks notebook
            with open(path, "r") as f:
                html_content = f.read()
                displayHTML(html_content)

                # Save the Data Docs to the specified S3 path
                s3_target = os.path.join(s3_save_path, os.path.basename(path))
                with open(s3_target, "w") as target_file:
                    target_file.write(html_content)

# Usage:
display_and_save_checkpoint_results(context, checkpoint_result, "/dbfs/mnt/mount_s3/great_expectations/profilers/")

success_rate = extract_success_rate_from_checkpoint_v2(context, checkpoint_result)
print(success_rate)


## Invoke Lambda

client = boto3.client('lambda', region_name='ap-south-1', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

response = client.invoke(
    FunctionName='notifysns', #Please replace the Function name which was created through the terraform.
    InvocationType='RequestResponse',
    Payload=json.dumps({'success_rate': success_rate})
)

# Extracting response from the lambda function (optional)
response_payload = json.loads(response['Payload'].read())
print(response_payload)
