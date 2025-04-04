import boto3
import json
import logging
import markdown
from bs4 import BeautifulSoup
import os

# Cấu hình logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Kết nối tới các dịch vụ AWS
s3 = boto3.client('s3')
kendra = boto3.client('kendra', region_name='ap-southeast-1')

# DynamoDB for conversation memory (if needed)
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
conversation_table = dynamodb.Table('ChatbotMemory')

# Kendra index ID
kendra_index_id = '1c088278-9865-482f-a9bd-02403d6e9fd0'

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Lấy thông tin bucket và file name từ event S3
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        file_name = event['Records'][0]['s3']['object']['key']
        
        # Download file markdown từ S3
        md_file = s3.get_object(Bucket=bucket_name, Key=file_name)
        md_content = md_file['Body'].read().decode('utf-8')
        
        # Chuyển đổi Markdown sang HTML
        html_content = markdown.markdown(md_content)
        
        # Create HTML document for Kendra
        document = {
            'Id': file_name,
            'Title': file_name,  # Tên file làm tiêu đề cho tài liệu
            'Blob': html_content.encode('utf-8'),  # Dữ liệu HTML
            'ContentType': 'HTML',  # Chúng ta sẽ sử dụng HTML
        }

        # Gửi tài liệu đến Kendra
        response = kendra.BatchPutDocuments(
            IndexId=kendra_index_id,
            Documents=[document]
        )

        # Đảm bảo tài liệu được xử lý thành công
        if 'FailedDocuments' in response and response['FailedDocuments']:
            logger.error(f"Failed to upload documents to Kendra: {response['FailedDocuments']}")
            raise Exception(f"Failed to upload documents to Kendra: {response['FailedDocuments']}")

        return {
            'statusCode': 200,
            'body': json.dumps('File successfully synced to Kendra')
        }

    except Exception as e:
        logger.error(f"Error syncing document to Kendra: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error syncing document to Kendra: {str(e)}")
        }
