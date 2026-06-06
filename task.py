# ========================================
# Task Definition Function
# ========================================
def get_task() -> str:

    print("📋 Preparing automation task instructions...")
    
    task = f"""
    Steps:
    1. Go to "https://www.maersk.com/tracking/".
    2. Enter "721144157" in the BL Container number field.
    3. Click on Track button
    4. Wait for the result
    5. Extract the Actual Time of Arrival in Singapore.
    6. Return the status in a concise format.
    Output Format:
    {{
        "ATA": "<actual time of arrival>"
    }}
    
    IMPORTANT REQUIREMENTS:
    - AVOID clicking the X button at all costs - it clears the search field
    - Focus on finding the magnifying glass search icon or press ENTER
    - Do not include any other text in the response.
    - Ensure the JSON is properly formatted and valid.
    - Return only JSON data and don't save the data to results.md or any other file.
    - If no results are found, return an empty JSON object: {{}}
   """
    
    print("✅ Task instructions prepared")
    return task