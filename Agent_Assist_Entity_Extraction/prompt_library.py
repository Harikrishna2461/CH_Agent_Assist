#Defining LLM function for the prompt generator for entity extraction  
class EntityExtraction:
    @staticmethod
    def enrollment_prompt_generator(conversation,entities):
        prompt_claude = """Human: \"""" + conversation + """\"

        The above is a transcript between a call center agent and an insurance subscriber or patient. Identify and extract key entities such as \"""" + entities + """\" from the transcript. Include only the information present.

        Output the results as a structured JSON containing only the extracted fields.

        Assistant:
        """

        return prompt_claude
    
class TextSummarisation:
    @staticmethod
    def summarisation_prompt_generator(context):
        prompt_llama = f"""
                       Instruction: "Summarise this call transcript between a patient and an agent and provide it in a precise paragraph : " :
                       {context}.
             
                       Response :  
                       """
        return prompt_llama


class Conversational:
    @staticmethod
    def Conversational_QnA_prompt_generator_llama(final_summary,patient_data,question):
        prompt_llama = f"""Using the information from the conversation summary : {final_summary} 
                           and 
                           The patient enrollment data : 
                           {patient_data},
                           Answer the following Question : 
                           {question}

                            If you do not know the answer and if the Current conversation summary or the Patient enrollment data doesn't contain the answer,then 
                            truthfully say I don't know.
                            Response:
                        """
        return prompt_llama

    @staticmethod
    def Conversational_QnA_prompt_generator_claude2(final_summary,patient_data,question):
        prompt_llama = f"""Human: \"""" + question + """\"

                           The above is a question/query asked by a patient to a call center agent.Using the conversation_summary which is \"""" + final_summary + """\" 
                           and the patient's enrollment data which is \"""" + patient_data + """\",answer the patient's question or query.

                           Assistant:
                        """
        return prompt_llama