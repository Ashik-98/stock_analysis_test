import os
import io
import requests
import pandas as pd
import boto3
from datetime import datetime
import consonants as con
import json

# Initialize S3 client outside handler for connection reuse across warm starts
s3_client = boto3.client("s3")
ssm = boto3.client("ssm")
sns = boto3.client("sns")
parameter = ssm.get_parameter(
    Name="/stockurl",
    WithDecryption=True
)

# github_api_url = parameter["Parameter"]["Value"]
github_api_url = ssm.get_parameter(Name=con.urlapi, WithDecryption=True)["Parameter"]["Value"]

print(github_api_url)

S3_BUCKET_NAME = os.environ.get(
    "S3_BUCKET_NAME",
    "stockdev-0416"
)
def send_sns_success():
    success_sns_arn = ssm.get_parameter(Name=con.SUCCESSNOTIFICATIONARN, WithDecryption=True)["Parameter"]["Value"]
    component_name = con.COMPONENT_NAME
    env = ssm.get_parameter(Name=con.ENVIRONMENT, WithDecryption=True)['Parameter']['Value']
    success_msg = con.SUCCESS_MSG
    sns_message = (f"{component_name} :  {success_msg}")
    print(sns_message, 'text')
    succ_response = sns.publish(TargetArn=success_sns_arn,Message=json.dumps({'default': json.dumps(sns_message)}),
        Subject= env + " : " + component_name,MessageStructure="json")
    return succ_response
        
def send_error_sns(msg):
    error_sns_arn = ssm.get_parameter(Name=con.ERRORNOTIFICATIONARN)["Parameter"]["Value"]
    env = ssm.get_parameter(Name=con.ENVIRONMENT, WithDecryption=True)['Parameter']['Value']
    error_message=con.ERROR_MSG+msg
    component_name = con.COMPONENT_NAME
    sns_message = (f"{component_name} : {error_message}")
    err_response = sns.publish(TargetArn=error_sns_arn,Message=json.dumps({'default': json.dumps(sns_message)}),    Subject=env + " : " + component_name,
        MessageStructure="json")
    return err_response

def lambda_handler(event, context):

    try:
        # Generate a new S3 key for every Lambda invocation
        timestamp = datetime.now().strftime(
            "%d-%m-%Y/stock_data_%H:%M:%S"
        )

        S3_FILE_KEY = timestamp + ".csv"

        # github_api_url = (
        #     "https://api.github.com/repos/"
        #     "squareshift/stock_analysis/contents/"
        # )

        # GitHub API requires a User-Agent header
        headers = {
            "User-Agent": "AWS-Lambda-Stock-Analysis"
        }

        response = requests.get(
            github_api_url,
            headers=headers
        )

        response.raise_for_status()

        files = response.json()

        csv_files = [
            file["download_url"]
            for file in files
            if file["name"].endswith(".csv")
        ]

        if not csv_files:
            return {
                "statusCode": 400,
                "body": "No CSV files found in the repository."
            }

        # Extract metadata file and stock CSVs
        metadata_url = csv_files.pop()

        d = pd.read_csv(metadata_url)

        dataframes = []

        for url in csv_files:

            file_name = (
                url.split("/")[-1]
                .replace(".csv", "*")
            )

            df = pd.read_csv(url)

            df["Symbol"] = file_name

            dataframes.append(df)

        combined_df = pd.concat(
            dataframes,
            ignore_index=True
        )

        o_df = pd.merge(
            combined_df,
            d,
            on="Symbol",
            how="left"
        )

        # Date filtering
        o_df["timestamp"] = pd.to_datetime(
            o_df["timestamp"]
        )

        filtered_df = o_df[
            (o_df["timestamp"] >= "2021-01-01") &
            (o_df["timestamp"] <= "2021-05-26")
        ]

        # Aggregation
        result_time = (
            filtered_df
            .groupby("Sector")
            .agg({
                "open": "mean",
                "close": "mean",
                "high": "max",
                "low": "min",
                "volume": "mean"
            })
            .reset_index()
        )

        # Filter sectors
        list_sector = [
            "TECHNOLOGY",
            "FINANCE"
        ]

        result_time = result_time[
            result_time["Sector"].isin(list_sector)
        ].reset_index(drop=True)

        result_time.columns = [
            "Sector",
            "sector_open_mean",
            "sector_close_mean",
            "sector_high",
            "sector_low",
            "sector_volume_mean"
        ]

        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()

        result_time.to_csv(
            csv_buffer,
            index=False,
            header=True
        )

        # Upload to S3
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=S3_FILE_KEY,
            Body=csv_buffer.getvalue(),
            ContentType="text/csv"
        )
        print("sending the mail notification")
        send_sns_success()

        return {
            "statusCode": 200,
            "body": (
                "Data processed and uploaded successfully "
                f"to s3://{S3_BUCKET_NAME}/{S3_FILE_KEY}"
            )
        }

    except Exception as e:

        return {
            "statusCode": 500,
            "body": f"Error processing data: {str(e)}"
        }