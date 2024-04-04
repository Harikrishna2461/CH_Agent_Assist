import boto3
import json
import base64
import time
import os
import re
from botocore.exceptions import ClientError
import logging
import redis

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name= os.environ.get("Region") #"us-east-1",
)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name= os.environ.get("Region")  #'us-east-1'
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

def get_insights_prompt(bucket,file,prompt_category,required_prompt,insurance_provider,insurance_statistics):
    entities = "name of patient, status of insurance, insurance number, demographic details etc."
    s3 = boto3.client('s3') 
    response = s3.get_object(Bucket=bucket,Key=file)
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)
    prompt = json_content[prompt_category][required_prompt].format(insurance_provider=insurance_provider,insurance_statistics=insurance_statistics)
    
    return prompt

def enrollment_prompt_generator(conversation,entities,today_date):
    prompt_claude = f"""Human: {conversation}

    The above is a transcript between a call center agent and an insurance subscriber or patient. 
    Identify and extract key entities such as {entities} from the transcript. Include only the information present.
    
    Ensure emails are recognized as valid email addresses in the format "email": "example@email.com" and phone numbers are in the standard format (e.g., (123) 456-7890 or +12345678900).
    Make sure that the words are gramatically correct and no spaces in the email address or phone number. 

    Based on today's date which is {today_date} and the patient's date of birth or dob,calculate the age of the patient and return it along with other entities in the output.
    
    Output the results as a structured JSON containing only the extracted fields.
    
    Strictly Follow the rules to provide ouput in JSON format and do not provide the extra sentence 'Here are the key entities extracted from the conversation before the JSON' as part of your response.
    Make sure you adhere to the list of entities extracted and create JSON with the exact key names passed and do not change the key names.
    Include only the information present in the provided conversation and do no not make-up any information on your own.
    The keys of the response json should be exactly same as the keys in {entities}.
    
    Assistant:
    """

    return prompt_claude
    
def insights_prompt_generator(insurance_provider,pharmacy_name,insurance_statistics):
    prompt_claude = """Human: 
    
You are Agent assist tracking the Patient and agent conversation and help the agent recommend meaningful insights based on the 
insurance and pharmacy details related insights like for example suggesting which pharmacy to select based on the
patient's Insurance provider and the pharmacy using metrics like how soon the other pharmacies if having a quicker dispense time can be helpful.
The lesser the number of days to dispense the medication,the higher are the chances of recommendation of that pharmacy.

If \" """ + insurance_provider + """ \"  or \" """ + pharmacy_name + """ \" is not present in \" """ + insurance_statistics + """ \" , then just provide a response telling that you don't have sufficient information to provide any insights and do not follow any of the information in rest of this prompt.

The patients's insurance provider is  \" """ + insurance_provider + """ \" and pharmacy is  \" """ + pharmacy_name + """ \" and use the following insurance statistics data to provide the insights:
\" """ + insurance_statistics + """ \".

In the insurance statistics data provided above,the keys represent the insurance provider and the value represents the pharmacy company and the number of days
it takes to dispense the medication to the patient.

Only provide the response when you have the values for both insurance provider and pharmacy name from the patient.Do not generate any insights unless you have both these information.
Also do not recommend any insights if the patient already has the pharmacy which is the quickest according to the insurance statistics and just suggest the patient to continue
with their existing pharmacy and not change their choice of pharmacy.


Please Provide the Insight in brief without missing any important details in about 6 lines.

Provide the response in a structured and easily readable format.

Assistant:
"""
    return prompt_claude

def sns_publisher(json_data):
    # Create an SNS client
    sns = boto3.client('sns')
    # Specify the topic ARN
    topic_arn = os.environ.get("SNSArn")  #'arn:aws:sns:us-east-1:383299343633:ch-agent-assist-processor-sns.fifo'
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
            "insights_data": insights_data,
                     }  
            }
    return json_response