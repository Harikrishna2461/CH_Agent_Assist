#Defining LLM function for the prompt generator for insights generation
insurance_type_prompt_generator = """Human:

    You are Agent assist tracking the Patient and agent conversation and help the agent by generating an insight, based on the patient's data for insurance type "{insurance_type}"
    Provide the details.

    Note: Only consider the cases when the patient is with Hub.
    
    Assistant:
    """
    

insurance_type_and_provider_prompt_generator =  """Human:

    You are Agent assist tracking the Patient and agent conversation and help the agent by generating an insight based on the patient's data for insurance type "{insurance_type}" and insurance provider
    "{insurance_provider}" 
    Provide all the details including details around PA

    Note: Only consider the cases when the patient is with Hub.
    
    Assistant:
    """

    
insurance_type_provider_pharmacy_ttf_prompt_generator = """Human:

    You are Agent assist helping the agent to recommend a better specialty pharmacy with the lower time to fill days.
    For a hub patient with insurance_type as  "{insurance_type}" and insurance provider as "{insurance_provider}" 
    Recommend the specialty pharmacies with theirTime to Fill days and compare the time to fill days with the patient's specialty pharmacy "{pharmacy_name}"
    
    Note: Only consider the cases when the patient is with Hub.

    Provide the response in a structured and readable format.
    
    Assistant:
    """
    

insurance_type_provider_pharmacy_prompt_generator = """Human:

    You are Agent assist helping the agent and help the agent by generating an insight based on the patient's data based on the patient's insurance_type as  "{insurance_type}" and insurance provider as "{insurance_provider}" 
    and specialty pharmacy "{pharmacy_name}", provide all the important metrics for the same combination
    
    Note: Only consider the cases when the patient is with Hub.

    Provide the response in a structured and readable format.
    
    Assistant:
    """