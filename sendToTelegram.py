import requests
import json
import logging

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = '8153658841:AAGGt0sGlHwvUupwFqy1hoS0hLluR3BRZfg'
TELEGRAM_CHAT_ID = '-4621319483'

def send_to_telegram(message):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message
        }
        response = requests.post(url, data=payload)
        
        if response.status_code != 200:
            logger.error(f"Failed to send message to Telegram: {response.json()}")
            return False
        logger.info("Message sent successfully to Telegram.")
        return True
    except Exception as e:
        logger.error(f"Exception occurred while sending to Telegram: {e}")
        return False

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Extract user's question and chatbot's answer from the event
        # Handle both direct Lambda invocation and API Gateway formats
        if isinstance(event, dict) and 'body' in event:
            try:
                body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
                question = body.get('question', 'Unknown Question')
                answer = body.get('answer', 'Unknown Answer')
            except:
                question = 'Unknown Question'
                answer = 'No Answer Provided'
        else:
            question = event.get('question', 'Unknown Question')
            answer = event.get('answer', 'No Answer Provided')

        # Log the extracted values
        logger.info(f"Question: {question}")
        logger.info(f"Answer: {answer}")

        # Create a formatted message
        message = f"🧑 User's Question: {question}\n🤖 Chatbot's Answer: {answer}"
        
        # Send to Telegram
        if send_to_telegram(message):
            return {
                'statusCode': 200,
                'body': json.dumps('Message sent to Telegram successfully!')
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to send message to Telegram.')
            }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"An error occurred: {str(e)}")
        }