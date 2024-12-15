def get_analysis_prompt(num_images, query):
    return f"""Analyze {num_images} memes for the query: '{query}'

IMPORTANT RESPONSE INSTRUCTIONS:
- Respond EXACTLY in this JSON format: 
[
  {{"image_path": "filename.jpg", "score": 8, "summary": "Meme description"}},
  ...
]
- Select ONLY the top 5 most relevant memes
- Each image above is labeled with its filename - USE THE EXACT FILENAME shown
- Scores must be integers from 0-10
- Summaries must be one concise line
- The response should be only JSON. Nothing else.
"""
