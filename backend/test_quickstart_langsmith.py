import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("Checking environment variables...")
print(f"GEMINI_API_KEY set: {'Yes' if os.environ.get('GEMINI_API_KEY') else 'No'}")
print(f"PINECONE_API_KEY set: {'Yes' if os.environ.get('PINECONE_API_KEY') else 'No'}")
print(f"PINECONE_INDEX_NAME: {os.environ.get('PINECONE_INDEX_NAME')}")
print(f"LANGSMITH_API_KEY set: {'Yes' if os.environ.get('LANGSMITH_API_KEY') else 'No'}")
print(f"LANGSMITH_PROJECT: {os.environ.get('LANGSMITH_PROJECT')}")
print(f"DATABASE_URL set: {'Yes' if os.environ.get('DATABASE_URL') else 'No'}")

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

print("\nInitializing ChatGoogleGenerativeAI (gemini-2.5-flash)...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    google_api_key=os.environ.get("GEMINI_API_KEY"),
    temperature=0.2
)

response = llm.invoke([HumanMessage(content="Hello! Verify that LangSmith tracing is active and reply with a 1-sentence confirmation.")])
print("\nModel Response:")
print(response.content)
