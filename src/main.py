import json
import os
import traceback

from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, ValidationError

from embeddings import MemeEmbeddings
from instructions import get_analysis_prompt
from utils import Spinner, encode_image, get_google_api_key

# Load environment variables
load_dotenv()


# Define the data structure for meme search results
class MemeSearch(BaseModel):
    image_path: str
    score: int
    summary: str


def search_memes(query, vector_store, memes_folder, top_k=10):
    """Search memes using vector similarity and then analyze with Gemini."""
    # First, get the most similar memes using vector search
    similar_memes = vector_store.similarity_search(query, k=top_k)

    # Prepare content for Gemini analysis
    message_content = [
        {"type": "text", "text": get_analysis_prompt(top_k, query)}]

    # Only analyze the top similar memes
    with Spinner("Processing top similar memes"):
        for doc in similar_memes:
            image_path = doc.metadata["image_path"]
            image_filename = os.path.basename(image_path)
            image = encode_image(image_path)
            message_content.extend(
                [
                    {"type": "text", "text": f"\nImage filename: {image_filename}"},
                    {
                        "type": "image_url",
                        "image_url": f"data:image/jpeg;base64,{image}",
                    },
                ]
            )

    # Create the LLM instance
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")

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

            json_match = re.search(r"\[.*?\]", response, re.DOTALL)
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
                validated_meme_dict["image_path"] = os.path.join(
                    memes_folder, validated_meme_dict["image_path"]
                )
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
    memes_folder = "memes"

    # Initialize embeddings and vector store
    print("\nInitializing meme analysis system...")
    meme_embeddings = MemeEmbeddings()

    # Create or load vector store
    vector_store_path = "vector_store"
    if os.path.exists(vector_store_path):
        print("Loading existing meme embeddings...")
        vector_store = FAISS.load_local(
            vector_store_path,
            meme_embeddings,
            allow_dangerous_deserialization=True,  # Only enable if you trust the source
        )
    else:
        print("Creating new meme embeddings (this may take a while)...")
        vector_store = meme_embeddings.create_vector_store(memes_folder)
        # Save for future use
        vector_store.save_local(vector_store_path)

    # Get meme count
    meme_count = len(os.listdir(memes_folder))
    print(f"\nFound {meme_count} memes in the memes folder.")
    print("Search for relevant memes by entering keywords.\n")

    # Main search loop
    while True:
        query = input("Enter search query (or 'exit' to quit): ").strip()
        if query.lower() == "exit":
            break

        results = search_memes(query, vector_store, memes_folder)

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
