import os
from typing import List

import torch
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from PIL import Image
from tqdm import tqdm
from transformers import CLIPModel, CLIPProcessor


class MemeEmbeddings(Embeddings):
    def __init__(self):
        """Initialize CLIP model for both image and text embeddings"""

        # Initialize CLIP model
        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        self.processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

        # Set device
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model.to(self.device)

    def get_image_embedding(self, image_path):
        """Generate embedding for a single image."""
        image = Image.open(image_path)
        inputs = self.processor(images=image, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            image_features = self.model.get_image_features(**inputs)

        return image_features.cpu().numpy()[0].tolist()

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        results = []
        for text in texts:
            inputs = self.processor(text=text, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)

            results.append(text_features.cpu().numpy()[0].tolist())

        return results

    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single text query."""
        inputs = self.processor(text=text, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}

        with torch.no_grad():
            text_features = self.model.get_text_features(**inputs)

        return text_features.cpu().numpy()[0].tolist()

    def create_vector_store(self, memes_folder):
        """Create a vector store from all memes in the folder."""
        meme_files = [
            f
            for f in os.listdir(memes_folder)
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp"))
        ]

        documents = []

        print(f"\nCreating embeddings for {len(meme_files)} memes...")
        # Using tqdm for progress bar
        for meme_file in tqdm(meme_files, desc="Creating embeddings", unit="meme"):
            image_path = os.path.join(memes_folder, meme_file)
            try:
                # Get image embedding and store it in the document's metadata
                embedding = self.get_image_embedding(image_path)

                # Create Document object with embedding in metadata
                doc = Document(
                    page_content=f"Meme image: {meme_file}",
                    metadata={"image_path": image_path, "embedding": embedding},
                )
                documents.append(doc)

            except Exception as e:
                print(f"\nError processing {meme_file}: {str(e)}")

        print("\nCreating FAISS index...")

        # Create FAISS index directly from documents
        vector_store = FAISS.from_documents(documents, self)

        print("FAISS index created successfully!")
        return vector_store
