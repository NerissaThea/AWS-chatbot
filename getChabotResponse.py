import boto3
import json
import logging
import markdown
import datetime
from bs4 import BeautifulSoup

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Connect to AWS services
kendra_client = boto3.client('kendra', region_name='ap-southeast-1')
kendra_index_id = '1c088278-9865-482f-a9bd-02403d6e9fd0'

# Use bedrock-runtime with Claude 3.5 Sonnet
bedrock_runtime_client = boto3.client('bedrock-runtime', region_name='ap-southeast-1')
bedrock_model_id = 'anthropic.claude-3-5-sonnet-20240620-v1:0'

# DynamoDB for conversation memory
dynamodb = boto3.resource('dynamodb', region_name='ap-southeast-1')
conversation_table = dynamodb.Table('ChatbotMemory') 

# Lambda function to call SendToTelegram Lambda
lambda_client = boto3.client('lambda')

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Try to extract question and session_id from different possible formats
        question = None
        session_id = 'default_session'  # Default session ID if not provided
        from_frontend = event.get('fromFrontend', False)  # Check for the flag
        
        # Format 1: Direct body from API Gateway integration
        if isinstance(event, dict) and 'question' in event:
            question = event['question']
            session_id = event.get('session_id', session_id)
        # Format 2: Body parsed by API Gateway
        elif isinstance(event, dict) and 'body' in event:
            try:
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                question = body.get('question')
                session_id = body.get('session_id', session_id)
            except:
                pass
        """
        Format 3: From AppSync arguments format
        elif isinstance(event, dict) and 'arguments' in event:
            question = event['arguments'].get('question')
            session_id = event['arguments'].get('session_id', session_id)
        """

        logger.info(f"Extracted question: {question}")
        logger.info(f"Using session_id: {session_id}")
        
        if not question:
            raise ValueError("Could not find 'question' in the request")

        # Retrieve previous conversations for this session to build context
        previous_conversations = get_previous_conversations(session_id, limit=3)
        logger.info(f"Retrieved {len(previous_conversations)} previous conversations")
        
        # Initialize context for memory
        context = ""
        if previous_conversations:
            context = "Previous conversation:\n"
            for conv in previous_conversations:
                context += f"User: {conv['question']}\nAssistant: {conv['answer']}\n\n"
            
            logger.info(f"Built context from previous conversations: {context[:100]}...")

        #1. Query Kendra for answers
        response = kendra_client.query(
            IndexId=kendra_index_id,
            QueryText=question,
            PageSize=5,
            AttributeFilter={
                "EqualsTo": {
                    "Key": "_language_code",
                    "Value": {
                        "StringValue": "en"
                    }
                }
            }
        )
        
        # Check if there are results from Kendra
        if 'ResultItems' in response and len(response['ResultItems']) > 0:
            result_item = response['ResultItems'][0]
            answer = result_item.get('DocumentExcerpt', {}).get('Text', 'No answer found.')

            # Process Markdown if present in answer from Kendra
            if answer:
                html_content = markdown.markdown(answer)
                soup = BeautifulSoup(html_content, 'html.parser')
                answer = soup.get_text()
                
            source = "kendra"
        else:
            # If there's no result from Kendra, call Claude 3.5 Sonnet
            logger.info("No results from Kendra, calling Claude 3.5 Sonnet...")
            
            # Include context from previous conversations if available
            prompt = question
            if context:
                prompt = f"{context}\n\nNew Question: {question}\n\nPlease respond to the new question using the context of our previous conversation when relevant."
            
            # Config requirements Claude 3.5 Sonnet
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }

            # Send request to Claude 3.5 Sonnet API
            response = bedrock_runtime_client.invoke_model(
                modelId=bedrock_model_id,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(request_body)
            )

            # Check and process result from Claude 3.5 Sonnet
            if response and 'body' in response:
                response_body = response['body'].read().decode('utf-8')
                logger.info(f"Raw Claude response: {response_body}")
                
                result = json.loads(response_body)
                if 'content' in result and len(result['content']) > 0:
                    answer = result['content'][0].get('text', 'No answer found')
                else:
                    answer = "No answer found from Claude 3.5 Sonnet."
                    
                source = "claude"
            else:
                answer = "No relevant information found in the knowledge base."
                source = "none"

        # Store the conversation in DynamoDB
        store_conversation(session_id, question, answer, source)
        logger.info(f"Stored conversation in DynamoDB for session {session_id}")

        # Check if it's from the frontend for all responses (both Kendra and AI)
        if from_frontend:
            # Send to Telegram for any type of response
            payload = {
                "question": question,
                "answer": answer
            }

            lambda_client.invoke(
                FunctionName="sendToTelegram", 
                InvocationType="Event",  # Asynchronous invocation
                Payload=json.dumps(payload)
            )

        # Return result with CORS headers
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'response': answer,
                'session_id': session_id
            })
        }
    
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Content-Type': 'application/json'
            },
            'body': json.dumps({
                'response': f"An error occurred while processing your question: {str(e)}"
            })
        }

def store_conversation(session_id, question, answer, source):
    """
    Store a conversation in DynamoDB
    """
    try:
        timestamp = datetime.datetime.now().isoformat()
        conversation_table.put_item(
            Item={
                'session_id': session_id,
                'timestamp': timestamp,
                'question': question,
                'answer': answer,
                'source': source
            }
        )
        return True
    except Exception as e:
        logger.error(f"Error storing conversation in DynamoDB: {str(e)}")
        return False

def get_previous_conversations(session_id, limit=3):
    """
    Retrieve previous conversations from DynamoDB
    Returns a list of conversation items ordered by timestamp (most recent last)
    """
    try:
        response = conversation_table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('session_id').eq(session_id),
            ScanIndexForward=False,  # Sort by timestamp in descending order (newest first)
            Limit=limit
        )
        
        # Return conversations in chronological order (oldest first)
        if 'Items' in response:
            return sorted(response['Items'], key=lambda x: x.get('timestamp', ''))
        return []
    except Exception as e:
        logger.error(f"Error retrieving conversations from DynamoDB: {str(e)}")
        return []
