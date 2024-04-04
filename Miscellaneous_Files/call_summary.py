import boto3
import json
import base64
import time
import re
from botocore.exceptions import ClientError
import logging
import redis
import os

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name='us-east-1'
)

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
    
    if start_index == -1:
        data1 = "{" + data
    else:
        data1 = data
    
    start_index_final = data.find("{")    
    print(f'start_index:{start_index_final}')
    
    end_char_indices = [i.start() for i in re.finditer("}",data1)]
    print(f'end_indices:{end_char_indices}')
    end_index = end_char_indices[len(end_char_indices)-1]
    print(f'end_index:{end_index}')
    if end_index == len(data1)-1:
        result = data1[start_index_final:]
    else:
        result = data1[start_index_final:end_index+1]
    print(f'result:{result}')
    
    return result
    
def summarisation_prompt_generator(context):
    prompt_llama = f"""
Instruction: "Summarise this call transcript between a patient and an agent and include the information shared by the patient in a precise paragraph":
NOTE: Consider the below context as your only source of information and provide the response in a paragraph

{context}
             
Response :  
    """
    return prompt_llama

def get_summary_prompt(bucket,file,prompt_category,required_prompt,conversation):
    s3 = boto3.client('s3') 
    response = s3.get_object(Bucket=bucket,Key=file)
    content = response['Body'].read().decode('utf-8')
    json_content = json.loads(content)
    prompt = json_content[prompt_category][required_prompt].format(context=conversation)
    
    return prompt

#Defining function to summarize context
def load_llama2(bedrock_runtime , prompt , temp , top_p):
    try:
        body = {
            "prompt" : prompt,
            "temperature" : temp,
            "top_p" : top_p,
            "max_gen_len" : 1000
            }

        response = bedrock_runtime.invoke_model(
            modelId="meta.llama2-13b-chat-v1", body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        completion = response_body["generation"]

        return completion

    except ClientError:
        logging.error("Couldn't invoke Llama 2")
        raise
    

def sns_data_postprocessing(event,data):
    json_response = {
            "stream": "SUMMARY",
            "streamConnectionId": json.loads(event["Records"][0]['body'])["streamConnectionId"],
             "body": {
                 "transactionId": "f830e890-3ff2-4fdc-a08e-dd9b78a2dc28",
                  "contactId": json.loads(event["Records"][0]['body'])["streamConnectionId"],
            "SUMMARY": data,
                     }  
            }
    return json_response
    
def sns_publisher(json_data):
    # Create an SNS client
    sns = boto3.client('sns')
    # Specify the topic ARN
    topic_arn = 'arn:aws:sns:us-east-1:383299343633:ch-agent-assist-processor-sns.fifo'
    # Publish JSON data to SNS topic
    response = sns.publish(TopicArn=topic_arn,Message=json.dumps({'default': json.dumps(json_data)}),MessageStructure='json',MessageGroupId=json_data["streamConnectionId"])
    print(f"SNS published : {response}")