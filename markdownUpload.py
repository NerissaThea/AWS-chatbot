import boto3
import json
import logging
import markdown
from bs4 import BeautifulSoup
import os
import uuid
import base64
from datetime import datetime

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Connect to AWS services
kendra_client = boto3.client('kendra', region_name='ap-southeast-1')
s3_client = boto3.client('s3')

# Configure Kendra Index ID
kendra_index_id = '1c088278-9865-482f-a9bd-02403d6e9fd0'
s3_bucket_name = 'chatbot-knowledgebase-md'

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Log event type and structure for debugging
        logger.info(f"Event type: {type(event)}")
        logger.info(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
        
        # Determine whether this is an S3 event or direct API upload
        if 'Records' in event and len(event['Records']) > 0 and 'eventSource' in event['Records'][0] and event['Records'][0]['eventSource'] == 'aws:s3':
            # Processing S3 trigger event
            s3_event = event['Records'][0]['s3']
            bucket_name = s3_event['bucket']['name']
            file_key = s3_event['object']['key']
            
            logger.info(f"Processing S3 event: file {file_key} in bucket {bucket_name}")
            return process_s3_file(bucket_name, file_key)
            
        elif 'body' in event:
            # Processing API Gateway event
            logger.info("Processing direct API upload")
            
            # Handle string or object body
            body = event['body']
            if isinstance(body, str):
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    logger.info("Body is not JSON, treating as raw string")
                    # Continue with body as string
                    pass
            
            # Handle API Gateway proxy integration
            if event.get('isBase64Encoded', False):
                try:
                    if isinstance(body, str):
                        decoded_body = base64.b64decode(body).decode('utf-8')
                        try:
                            body = json.loads(decoded_body)
                        except json.JSONDecodeError:
                            logger.info("Decoded body is not JSON")
                            # Use body as-is
                    else:
                        logger.error("Body is not a string for base64 decoding")
                        return error_response(400, "Invalid base64 encoded body")
                except Exception as e:
                    logger.error(f"Error decoding base64 body: {str(e)}")
                    return error_response(400, f"Error decoding base64 body: {str(e)}")
            
            # Handle file upload from structured JSON
            if isinstance(body, dict) and 'file' in body:
                file_data = body['file']
                file_content = file_data.get('content')
                file_name = file_data.get('fileName', 'document.md')
                
                # Check if content is base64 encoded
                if file_data.get('encoding') == 'base64':
                    try:
                        file_content = base64.b64decode(file_content)
                        if isinstance(file_content, bytes):
                            file_content = file_content.decode('utf-8')
                    except Exception as e:
                        logger.error(f"Error decoding file content base64: {str(e)}")
                        return error_response(400, f"Error decoding file content: {str(e)}")
                
                return upload_and_process_file(file_name, file_content)
            else:
                # Try to parse multipart form data
                logger.info("No file in body, trying multipart parsing")
                return handle_file_upload(event)
        else:
            # Debug dump of the event structure
            logger.error(f"Unrecognized event format. Event dump: {json.dumps(event)}")
            return error_response(400, "Invalid event format - missing required fields")
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return error_response(500, f"Error processing request: {str(e)}")

def error_response(status_code, message):
    """Helper function to create error responses"""
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({'error': message})
    }

def handle_file_upload(event):
    """Handle multipart form data file upload from API Gateway"""
    try:
        import cgi
        import io
        
        # Log headers for debugging
        headers = event.get('headers', {})
        logger.info(f"Request headers: {headers}")
        
        # Get content type
        content_type = None
        for key, value in headers.items():
            if key.lower() == 'content-type':
                content_type = value
                break
                
        logger.info(f"Content-Type: {content_type}")
        
        # Handle direct JSON with file content
        if 'body' in event and isinstance(event['body'], dict) and 'file' in event['body']:
            file_data = event['body']['file']
            file_name = file_data.get('fileName', 'document.md')
            file_content = file_data.get('content')
            
            if file_data.get('encoding') == 'base64':
                try:
                    file_content = base64.b64decode(file_content)
                    if isinstance(file_content, bytes):
                        file_content = file_content.decode('utf-8')
                except Exception as e:
                    logger.error(f"Error decoding base64: {str(e)}")
                    return error_response(400, f"Error decoding base64: {str(e)}")
            
            return upload_and_process_file(file_name, file_content)
            
        # If we have base64 encoded data from API Gateway
        if event.get('isBase64Encoded', False) and 'body' in event:
            try:
                # Parse raw body
                body = event['body']
                if isinstance(body, str):
                    decoded_body = base64.b64decode(body)
                    try:
                        # Try parsing as JSON
                        body_json = json.loads(decoded_body)
                        if isinstance(body_json, dict) and 'file' in body_json:
                            file_content = body_json['file'].get('content')
                            file_name = body_json['file'].get('fileName', 'document.md')
                            
                            if body_json['file'].get('encoding') == 'base64':
                                try:
                                    file_content = base64.b64decode(file_content)
                                    if isinstance(file_content, bytes):
                                        file_content = file_content.decode('utf-8')
                                except Exception as e:
                                    logger.error(f"Error decoding file content base64: {str(e)}")
                                    return error_response(400, f"Error decoding file content: {str(e)}")
                            
                            return upload_and_process_file(file_name, file_content)
                    except json.JSONDecodeError:
                        # Not JSON, might be multipart form data
                        logger.info("Decoded body is not JSON, continuing with multipart parsing")
                        pass
            except Exception as e:
                logger.error(f"Error handling base64 encoded body: {str(e)}")
                # Continue to try other methods
        
        # Handle direct JSON from frontend
        if content_type and 'application/json' in content_type.lower():
            try:
                body = event['body']
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        logger.error("Failed to parse JSON body")
                        return error_response(400, "Invalid JSON format")
                
                if isinstance(body, dict) and 'file' in body:
                    file_data = body['file']
                    file_name = file_data.get('fileName', 'document.md')
                    file_content = file_data.get('content')
                    
                    # Handle base64 encoded content
                    if file_data.get('encoding') == 'base64':
                        try:
                            file_content = base64.b64decode(file_content)
                            if isinstance(file_content, bytes):
                                file_content = file_content.decode('utf-8')
                        except Exception as e:
                            logger.error(f"Error decoding base64: {str(e)}")
                            return error_response(400, f"Error decoding base64: {str(e)}")
                    
                    return upload_and_process_file(file_name, file_content)
                else:
                    logger.error("No file data found in JSON body")
                    return error_response(400, "No file data found in request")
            except Exception as e:
                logger.error(f"Error parsing JSON body: {str(e)}")
                return error_response(400, f"Error parsing request body: {str(e)}")
                
        # Fall back to direct file processing if we have file content
        body = event.get('body', '')
        if isinstance(body, str) and body.strip():
            # Assume this is the direct file content
            file_name = "uploaded_document.md"
            # Try to get filename from headers if available
            if 'headers' in event and event['headers']:
                for key, value in event['headers'].items():
                    if key.lower() == 'x-filename':
                        file_name = value
                        break
            
            return upload_and_process_file(file_name, body)
        
        return error_response(400, "Unable to extract file data from request")
        
    except Exception as e:
        logger.error(f"Error handling file upload: {str(e)}")
        return error_response(500, f"Error handling file upload: {str(e)}")

def upload_and_process_file(file_name, file_content):
    """Upload the file to S3 and trigger processing"""
    try:
        # Ensure we have valid content
        if not file_content:
            return error_response(400, "Empty file content")
            
        logger.info(f"Processing file: {file_name}, content length: {len(str(file_content))}")
        
        # Ensure file has .md extension
        if not file_name.lower().endswith('.md'):
            file_name = f"{file_name}.md"
            
        # Create S3 key with uploads/ prefix and timestamp to avoid overwriting
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        file_key = f"uploads/{timestamp}_{file_name}"
        
        # Ensure file_content is in the right format for S3
        if isinstance(file_content, str):
            s3_body = file_content.encode('utf-8')
        elif isinstance(file_content, bytes):
            s3_body = file_content
        else:
            s3_body = str(file_content).encode('utf-8')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=s3_bucket_name,
            Key=file_key,
            Body=s3_body,
            ContentType='text/markdown'
        )
        
        logger.info(f"File uploaded to S3: {s3_bucket_name}/{file_key}")
        
        # Process the file immediately
        process_result = process_s3_file(s3_bucket_name, file_key)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'File uploaded and processed successfully',
                'fileKey': file_key,
                'processingResult': json.loads(process_result['body']) if isinstance(process_result.get('body'), str) else process_result.get('body', {})
            })
        }
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        return error_response(500, f"Error uploading file: {str(e)}")

def process_s3_file(bucket_name, file_key):
    """Process a Markdown file from S3 and update Kendra index"""
    try:
        # Get the file from S3
        file_obj = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        file_content = file_obj['Body'].read().decode('utf-8')
        
        # Extract file name without extension for title
        file_name = os.path.basename(file_key)
        title = os.path.splitext(file_name)[0]
        
        # Convert Markdown to HTML
        html_content = markdown.markdown(file_content)
        
        # Optional: Clean up the HTML if needed with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        cleaned_html = str(soup)
        
        # Extract plain text for better indexing
        plain_text = soup.get_text()
        
        logger.info(f"Processed file: {file_name}")
        logger.info(f"HTML content preview: {cleaned_html[:200]}...")
        
        # Generate a unique ID for the document
        document_id = f"{file_key.replace('/', '-')}-{uuid.uuid4()}"
        
        # Prepare document attributes
        attributes = [
            {
                'Key': '_language_code',
                'Value': {
                    'StringValue': 'en'  # Assuming English content
                }
            },
            {
                'Key': 'source_uri',
                'Value': {
                    'StringValue': f"s3://{bucket_name}/{file_key}"
                }
            },
            {
                'Key': 'title',
                'Value': {
                    'StringValue': title
                }
            },
            {
                'Key': 'updated_at',
                'Value': {
                    'DateValue': datetime.now()
                }
            }
        ]
        
        # Update Kendra index with HTML content
        response = kendra_client.batch_put_document(
            IndexId=kendra_index_id,
            Documents=[
                {
                    'Id': document_id,
                    'Title': title,
                    'Blob': cleaned_html.encode(),  # Send as binary data
                    'ContentType': 'HTML',
                    'Attributes': attributes
                }
            ]
        )
        
        logger.info(f"Kendra indexing response: {json.dumps(response)}")
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'message': 'File processed and indexed successfully',
                'documentId': document_id,
                'title': title
            })
        }
    
    except Exception as e:
        logger.error(f"Error processing S3 file: {str(e)}")
        return error_response(500, f"Failed to process file: {str(e)}")