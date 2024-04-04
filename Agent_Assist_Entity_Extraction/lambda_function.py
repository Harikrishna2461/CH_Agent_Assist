import boto3
import json
import base64
import time
import re
from botocore.exceptions import ClientError
import logging

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name='us-east-1'
)

brt = boto3.client(service_name='bedrock-runtime')

def decoder(data):
    decodedBytes = base64.b64decode(data)
    decodedStr = decodedBytes.decode("ascii") 
    json_str=json.loads(decodedStr)
    return json_str

##Processing data to fetch role and content
def data_preprocessing(data):
    #data = json_data['Records'][0]["body"]
    convo = ""
    content = json.loads(data["body"])["body"]["transcript"][0]["Content"]
    role = json.loads(data["body"])["body"]["transcript"][0]["ParticipantRole"]
    convo = convo + role + " : " + content
    #parsed_data = json.loads(data)
    #content = data#["body"]#["transcript"]#[0]#["Content"]
    #role = data["body"]["transcript"][0]["ParticipantRole"]
    
    #convo = ""
    #for i in range(len(transcription['transcriptions'])):
        #convo = convo + transcription['transcriptions'][i]['ParticipantRole'] + ": " + transcription['transcriptions'][i]['Content']
        #convo += "\n"
    #role = transcription["Segments"][0]["Transcript"]["ParticipantRole"]
    #content = transcription["Segments"][0]["Transcript"]["Content"]
    #convo = convo + role + " : " + content
    
    return convo

def data_postprocessing(data):
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

#Defining LLM function for the prompt generator for entity extraction  
entities = "name of patient, status of insurance, insurance number, demographic details etc."
def enrollment_prompt_generator(conversation,entities):
    prompt_claude = """Human: \" """ + conversation + """ \"
 
The above conversation is an automated transcript between a call centre agent and an insurance subscriber or 
patiet. I want to extract few key entities like \" """ + entities + """ \"". All or some information may be present in this transcript.
Extract the entities that you are able to find from this piece of call transcript.
 
The output would be a structured json with only the extracted fields. Just print the exact output without any extra sentences at the end or beggining. 
No need to print any extra text. Also do not generate an answer if that is not found in the transcript.
 
Assistant:
"""
    return prompt_claude

# Lambda handler to intgerate with AWS
def lambda_handler(event,context):
    final_transcript = ""
    for i in range(len(event['Records'])):
        final_transcript += "\n" + data_preprocessing(event['Records'][i])
    prompt_enrollment = enrollment_prompt_generator(final_transcript,entities)
    enrollment_data = load_claude2(bedrock_runtime,prompt_enrollment,0,0.9,1)
    json_data = data_postprocessing(enrollment_data)
    enrollment_json_object = json.loads(json_data)
    return {"statusCode": 200,"body": json.dumps(enrollment_json_object)}