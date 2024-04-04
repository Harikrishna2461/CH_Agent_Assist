class TextSummarisation:
    @staticmethod
    def summarisation_prompt_generator(context):
        prompt_llama = f"""
                       Instruction: "Summarise this call transcript between a patient and an agent and provide it in a precise paragraph : " :
                       {context}.
             
                       Response :  
                       """
        return prompt_llama