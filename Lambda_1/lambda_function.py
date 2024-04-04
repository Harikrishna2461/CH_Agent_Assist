import boto3
import json
import requests
import os
import sys
import base64
import time
import tzlocal
import re
from botocore.exceptions import ClientError

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1",
)

bedrock = boto3.client(
    service_name='bedrock', 
    region_name='us-east-1'
)

# Initialize a boto3 Kinesis client
kinesis_client = boto3.client('kinesis', region_name='us-east-1')

# The name of your Kinesis stream
stream_name = 'CH_agent_call_streams'

# The sequence number you want to start reading from
sequence_number_for_shard = '49649059939264757358942140911703275325366952989042933794'

# Function to process records and create JSON
def process_records(records):
    for record in records:
        # Kinesis data is UTF-8 encoded so decode here
        payload = record["Data"].decode('utf-8')
        return payload

# Function to get records from Kinesis
def get_kinesis_records(stream_name, sequence_number_for_shard):
    response = kinesis_client.describe_stream(StreamName=stream_name)
    shard_id = response['StreamDescription']['Shards'][2]['ShardId']

    # Get a shard iterator using the sequence number
    shard_iterator = kinesis_client.get_shard_iterator(StreamName=stream_name,
                                                       ShardId=shard_id,
                                                       ShardIteratorType='AT_SEQUENCE_NUMBER',
                                                       StartingSequenceNumber=sequence_number_for_shard)['ShardIterator']

    out = kinesis_client.get_records(ShardIterator=shard_iterator, Limit=100)
    shard_iterator = out['NextShardIterator']
    records = out['Records']

    if records:
        json_data = process_records(records)

    time.sleep(1)  # Sleep to avoid hitting rate limits
    return json_data

def word_filter(text,start_search_word,start_word_index,end_word_index):
    # Check if the search word exists in the input string
    if start_word_index != -1:
        # Extract everything from the search word onwards
        extracted_text = text[start_word_index + len(start_search_word):end_word_index]
        roles = ["AGENT","CUSTOMER"]
        role_index = 0
        conv = ""
        for role in roles:
            if extracted_text.find(role) != -1 :
                role_index = extracted_text.find(role)
                content_index = extracted_text.find('"Content"')
                comma_indices = [i.start() for i in re.finditer(',',extracted_text)] 
                #temp = extracted_text[content_index+len('"Content"'):end_word_index]
                #comma_index = temp[content_index+len('Content'):].find(",")
                conv = conv + extracted_text[role_index:role_index+len(role)]
                conv += extracted_text[content_index+len('"Content"'):]#comma_indices[len(comma_indices)-1]]
                return conv
            else:
                pass
    else:
        pass
    
def preprocess_text(text):
    r1 = text.replace("[","").replace("]","").replace('Transcript','"Transcript"')
    r2 = r1.replace('ParticipantId','"ParticipantId"').replace('ParticipantRole','"ParticipantRole"').replace('Content','"Content"')
    r3 = r2.replace('BeginOffsetMillis','"BeginOffsetMillis"').replace('EndOffsetMillis','"EndOffsetMillis"')
    r4 = r3.replace('Sentiment','"Sentiment"').replace('Id','"Id"')
    
    start_word_indices = [i.start() for i in re.finditer('"ParticipantRole"',r4)]
    end_word_indices = [i.start() for i in re.finditer('"BeginOffsetMillis"',r4)]

    start_search_word = '"Participant_Role"'
    transcript = ""
    for i in range(len(start_word_indices)):
        transcript = transcript + word_filter(r4,start_search_word,start_word_indices[i],end_word_indices[i]) + "\n"
        
    return transcript

def load_llama2(bedrock_runtime , prompt , temp , top_p):
    try:
        body = {
            "prompt": prompt,
            "temperature": temp,
            "top_p": top_p,
            "max_gen_len": 200
            }

        response = bedrock_runtime.invoke_model(
            modelId="meta.llama2-13b-chat-v1", body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        completion = response_body["generation"]

        return completion

    except ClientError:
        logger.error("Couldn't invoke Llama 2")
        raise
        
def enrollment_prompt_generator(conversation):
    prompt_llama = f"""
Instruction: "Identify the different entities like Name,First Name,Last Name,Age,Email,Username etc of the patient/customer
from the below conersation and provide them in the following format :
Name : [Name]
Age : [Age] and so on in a json format and only provide the json object." :

{conversation}.
             
Response :  
    """
    return prompt_llama

# Lambda handler
def lambda_handler(stream_name,sequence_number_for_shard):
    response = get_kinesis_records(stream_name,sequence_number_for_shard)
    final_transcript = preprocess_text(response)
    prompt_enrollment = enrollment_prompt_generator(final_transcript)
    enrollment_data = load_llama2(prompt_enrollment, 0, 0.9)
    enrollment_json_object = json.loads(enrollment_data)
    return {"statusCode": 200,"body": json.dumps(enrollment_json_object)}

lambda_handler(stream_name,sequence_number_for_shard)