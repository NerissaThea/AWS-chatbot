# AWS-chatbot
Lambda code for AWS Chatbot
Ah, I see! You would like to bundle the dependencies along with the Python files, zip them, and upload them to AWS Lambda. Here’s the step-by-step guide on how to achieve this.

### Step-by-Step Guide for Deploying the Lambda Function with Dependencies

1. **Install the Dependencies Locally**  
   First, we need to install the necessary libraries into a local directory. This will ensure that the Lambda function can include these dependencies.

   ```bash
   mkdir python
   pip install -r requirements.txt -t ./python
   ```

   The `requirements.txt` file should contain the following dependencies (this file will be created in the project folder):

   ```
   requests==2.32.3
   beautifulsoup4==4.13.3
   markdown==3.7
   boto3==1.26.11
   ```

2. **Include Your Python Files**  
   Next, add your Python files (the Lambda function files) to the `python` directory.

   For example:
   - `lambda_function.py` from **SENDTOTELEGRAM** should go inside the `python` directory.
   - Similarly, copy the `lambda_function.py` file from **GETCHATBOTRESPONSE** to the `python` directory.

3. **Zip the Contents**  
   After adding the Python files and the dependencies into the `python` folder, zip the contents of the folder to create a deployment package. Make sure you are zipping the contents of the `python` folder, not the folder itself.

   ```bash
   cd python
   zip -r ../lambda-deployment-package.zip .
   ```

   This will create a `lambda-deployment-package.zip` file.

4. **Upload the ZIP to Lambda**  
   - Go to the **AWS Lambda Console**.
   - Click on **Create Function** or select an existing function.
   - Under the **Function code** section, choose **Upload a .zip file** from the dropdown.
   - Upload the `lambda-deployment-package.zip` file.

5. **Set Up the Handler and Environment Variables**  
   - In the **Handler** field, you should set the correct handler for your Lambda function. For example:
     - For `sendToTelegram.py`, set the handler to: `lambda_function.lambda_handler`.
     - For `getChatbotResponse.py`, set the handler to: `lambda_function.lambda_handler`.
   
   - Set up any necessary environment variables (e.g., API keys, URLs) in the **Environment variables** section of the Lambda configuration.

6. **Test the Function**  
   Once the Lambda function is deployed, you can test it using AWS Lambda's **Test** functionality by creating a test event or invoking the function through an API Gateway.

---

### Complete `README.md` with the Instructions

```markdown
# Chatbot Integration Project - Lambda Deployment

This repository contains AWS Lambda functions to process chatbot responses and send them to Telegram. The project requires several Python libraries that need to be packaged together with the Lambda function before deployment.

## Project Structure

### 1. **SENDTOTELEGRAM**
This directory contains the Lambda function for sending chatbot responses to a Telegram chat. It listens for incoming events, formats the chatbot's response, and sends it to a specified Telegram chat.

#### Files:
- **lambda_function.py**: The main Lambda function for sending messages to Telegram.
- **requests**: The `requests` library used for sending HTTP requests.
- **certifi**, **charset_normalizer**: Dependencies for secure connections and character encoding detection.

---

### 2. **GETCHATBOTRESPONSE**
This directory contains the Lambda function that processes incoming questions, searches AWS Kendra for relevant answers, and invokes Claude 3.5 Sonnet via AWS Bedrock. It stores conversations in DynamoDB and interacts with other systems.

#### Files:
- **lambda_function.py**: The main Lambda function for processing incoming requests and generating responses.
- **beautifulsoup4**, **markdown**: Dependencies for HTML parsing and Markdown conversion.

---

## Dependencies

The following Python packages are required for running the Lambda functions:

- **requests**: For making HTTP requests to external APIs (Telegram).
- **beautifulsoup4**: For parsing and cleaning HTML content.
- **markdown**: For converting Markdown to HTML.
- **boto3**: AWS SDK for Python to interact with services like DynamoDB and Kendra.

## Installation and Deployment

### 1. Install the Dependencies
Create a directory to store the dependencies, and install the required packages into it.

```bash
mkdir python
pip install -r requirements.txt -t ./python
```

The `requirements.txt` file should contain the following content:

```
requests==2.32.3
beautifulsoup4==4.13.3
markdown==3.7
boto3==1.26.11
```

### 2. Add Your Python Files
After installing the dependencies, place the following Python files in the `python` folder:
- **lambda_function.py** from `SENDTOTELEGRAM` (for sending messages to Telegram).
- **lambda_function.py** from `GETCHATBOTRESPONSE` (for processing chatbot responses).

### 3. Create the Deployment Package
Zip the contents of the `python` directory to create a deployment package:

```bash
cd python
zip -r ../lambda-deployment-package.zip .
```

This will create a file called `lambda-deployment-package.zip`.

### 4. Upload the ZIP to AWS Lambda
- Go to the **AWS Lambda Console**.
- Create a new Lambda function or choose an existing one.
- Under the **Function code** section, select **Upload a .zip file**.
- Upload the `lambda-deployment-package.zip` file.

### 5. Set Handler and Environment Variables
- Set the **Handler** to:
  - `lambda_function.lambda_handler` for both `sendToTelegram.py` and `getChatbotResponse.py`.
- Add any necessary environment variables (like API keys, URLs, etc.) in the **Environment variables** section.

### 6. Test the Lambda Function
Use the AWS Lambda **Test** functionality or invoke the Lambda function using API Gateway.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```

---

This should guide you through installing dependencies, packaging your Lambda function, and deploying it to AWS. Let me know if you need further assistance!
