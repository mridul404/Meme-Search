import os
import json
import traceback
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

from utils import get_google_api_key, encode_image, Spinner
from instructions import get_analysis_prompt

# Load environment variables
load_dotenv()

# Define the data structure for meme search results
class MemeSearch(BaseModel):
    image_path: str
    score: int
    summary: str

def search_memes(query, memes_folder):
    """Search and rank memes based on the query."""
    # Create the LLM instance
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

    # Get all image files in the memes folder
    image_files = [f for f in os.listdir(memes_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]

    print(f"\nAnalyzing {len(image_files)} memes for relevance...")

    # Prepare content with multiple images
    message_content = [
        {
            "type": "text",
            "text": get_analysis_prompt(len(image_files), query)
        }
    ]

    # Add each image to the message content with its filename
    with Spinner("Processing images"):
        for image_filename in image_files:
            image_path = os.path.join(memes_folder, image_filename)
            image = encode_image(image_path)
            message_content.extend([
                {
                    "type": "text",
                    "text": f"\nImage filename: {image_filename}"
                },
                {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image}"
                }
            ])
    
    print("Sending request to AI model...")
    
    # Create the message
    message = HumanMessage(content=message_content)

    try:
        # Invoke the model and get the response
        with Spinner("Waiting for AI response"):
            response = llm.invoke([message]).content
        print("Response received! Processing results...")

        # Try to parse the JSON
        try:
            memes = json.loads(response)
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract JSON from the response
            import re
            json_match = re.search(r'\[.*?\]', response, re.DOTALL)
            if json_match:
                try:
                    memes = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    print("Failed to extract valid JSON")
                    return []
            else:
                print("No JSON-like structure found")
                return []

        # Validate each meme against the model
        validated_memes = []
        for meme in memes:
            try:
                validated_meme = MemeSearch(**meme)
                # Add full path to the meme
                validated_meme_dict = validated_meme.model_dump()
                validated_meme_dict['image_path'] = os.path.join(memes_folder, validated_meme_dict['image_path'])
                validated_memes.append(validated_meme_dict)
            except ValidationError as e:
                print(f"Validation error for meme: {meme}")
                print(e)

        return validated_memes

    except Exception as e:
        print("An error occurred:")
        print(traceback.format_exc())
        return []

def main():
    """Main function to run the meme search system."""
    # Ensure API key is set
    get_google_api_key()

    # Set the memes folder
    memes_folder = 'memes'
    
    # Get all image files in the memes folder
    image_files = [f for f in os.listdir(memes_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))]
    meme_count = len(image_files)
    
    print(f"\nFound {meme_count} memes in the memes folder.")
    print("Search for relevant memes by entering keywords.\n")

    # Main search loop
    while True:
        # Get search query from user
        query = input("Enter search query (or 'exit' to quit): ").strip()

        # Check for exit
        if query.lower() == 'exit':
            print("Exiting meme search system.")
            break

        # Search memes
        results = search_memes(query, memes_folder)

        # Print results
        if results:
            print("\nTop Relevant Memes:\n")
            for i, meme in enumerate(results, 1):
                print(f"{i}. Image Path: {meme['image_path']}")
                print(f"   Score: {meme['score']}/10")
                print(f"   Summary: {meme['summary']}\n")
        else:
            print("No memes found matching the query.")

if __name__ == "__main__":
    main()