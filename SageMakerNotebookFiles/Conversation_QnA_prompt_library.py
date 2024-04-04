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