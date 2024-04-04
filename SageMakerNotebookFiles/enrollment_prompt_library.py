class EntityExtraction:
    @staticmethod
    def enrollment_prompt_generator(conversation,entities):
        prompt_claude = """Human: \"""" + conversation + """\"

        The above is a transcript between a call center agent and an insurance subscriber or patient. Identify and extract key entities such as \"""" + entities + """\" from the transcript. Include only the information present.

        Output the results as a structured JSON containing only the extracted fields.

        Assistant:
        """

        return prompt_claude
