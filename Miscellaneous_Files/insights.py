import boto3
import json
import base64
import time
import re
from botocore.exceptions import ClientError
import logging
import redis

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name='us-east-1'
)

def decoder(data):
    decodedBytes = base64.b64decode(data)
    decodedStr = decodedBytes.decode("ascii") 
    json_str=json.loads(decodedStr)
    return json_str

##Processing data to fetch role and content
def construct_call_conversation(data):
    segments = json.loads(data)
    convo = "" 
    # Extract transcripts, participant roles, and content
    for segment in segments:
        transcript = segment['transcript'][0]
        participant_role = transcript['ParticipantRole']
        content = transcript['Content']
        convo += participant_role + " : " + content + "\n"
    
    return convo

def model_output_postprocessing(data):
    result = ""
    start_index = data.find("{")
    end_char_indices = [i.start() for i in re.finditer("}",data)]
    end_index = end_char_indices[len(end_char_indices)-1]
    result = data[start_index:end_index+1]
    
    return result

#Defining function to connect to Bedrock LLM
def load_claude2(bedrock_runtime , prompt , temp , top_p,top_k):
    try:
        body = {
            "prompt": prompt,
            "temperature": temp,
            "top_p": top_p,
            "top_k":top_k,
            "max_tokens_to_sample": 1000
            }

        response = bedrock_runtime.invoke_model(
            modelId="anthropic.claude-v2", body=json.dumps(body), accept="application/json", contentType="application/json"
                 )
        
        response_body = json.loads(response["body"].read())
        completion = response_body.get("completion")

        return completion

    except ClientError:
        logging.error("Couldn't invoke Llama 2")
        raise

#Passing the payer vs pharmacy stats as part of the context

def get_enrollment_prompt(bucket,file,prompt_category,required_prompt,conversation):
    entities = "name of patient, status of insurance, insurance number, demographic details etc."
    s3 = boto3.client('s3') 
    response = s3.get_object(Bucket=bucket,Key=file)
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)
    prompt = json_content[prompt_category][required_prompt].format(conversation=conversation,entities=entities)
    
    return prompt

def get_insights_prompt(bucket,file,prompt_category,required_prompt,insurance_provider):
    entities = "name of patient, status of insurance, insurance number, demographic details etc."
    s3 = boto3.client('s3') 
    response = s3.get_object(Bucket=bucket,Key=file)
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)
    prompt = json_content[prompt_category][required_prompt].format(insurance_provider=insurance_provider,insurance_statistics=insurance_statistics)
    
    return prompt

def enrollment_prompt_generator(conversation,entities):
    prompt_claude = f"""Human: {conversation}

    The above is a transcript between a call center agent and an insurance subscriber or patient. Identify and extract key entities such as {entities} from the transcript. Include only the information present.

    Output the results as a structured JSON containing only the extracted fields.
    
    Strictly Follow the rules to provide ouput in JSON format and do not provide the extra sentence 'Here are the key entities extracted from the conversation before the JSON' as part of your response.

    Assistant:
    """

    return prompt_claude
    
def insights_prompt_generator(insurance_provider,insurance_statistics):
    prompt_claude = """Human: 
 
You are Agent assist tracking the Patient and agent conversation and help the agent recommend meaningful insights on the 
insurance and insurance details related insights like for example suggesting which pharmacy to select based on the
patient's Insurance provider using metrics like how soon the pharmacy dispenses the medication to the patient.The lesser the
number of days to dispense the medication,the higher are the chances of recommendation of that pharmacy.

The patients's insurance provider is  \" """ + insurance_provider + """ \" and use the following json data to provide the insights:
\" """ + insurance_statistics + """ \".

In the Json Data,the keys represent the insurance provider and the value represents the pharmacy company and the number of days
it takes to dispense the medication to the patient.

Provide the response in a structured and easily readable format.
 
Assistant:
"""
    return prompt_claude

def sns_publisher(json_data):
    # Create an SNS client
    sns = boto3.client('sns')
    # Specify the topic ARN
    topic_arn = 'arn:aws:sns:us-east-1:383299343633:ch-agent-assist-processor-sns.fifo'
    # Publish JSON data to SNS topic
    response = sns.publish(TopicArn=topic_arn,Message=json.dumps({'default': json.dumps(json_data)}),MessageStructure='json',MessageGroupId=json_data["streamConnectionId"])
    print(f"SNS published : {response}")
        
def sns_data_postprocessing(event,insights_data):
    json_response = {
            "stream": "INSIGHTS_DATA",
            "streamConnectionId": json.loads(event["Records"][0]['body'])["streamConnectionId"],
             "body": {
                 "transactionId": "f830e890-3ff2-4fdc-a08e-dd9b78a2dc28",
                  "contactId": json.loads(event["Records"][0]['body'])["streamConnectionId"],
            "form_data": insights_data,
                     }  
            }
    return json_response