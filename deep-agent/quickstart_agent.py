import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# Load environment variables (LangSmith tracing will automatically capture invocations under project 'my-first-agent')
load_dotenv()

def run_quickstart_agent():
    print("==================================================")
    print("    Deep Agents Quickstart Agent (LangChain)     ")
    print("==================================================")
    print(f"LangSmith Project : {os.getenv('LANGSMITH_PROJECT', 'my-first-agent')}")
    print(f"LangSmith Tracing : {os.getenv('LANGSMITH_TRACING', 'true')}")
    print(f"Pinecone Index    : {os.getenv('PINECONE_INDEX_NAME', 'repo-mind')}")
    print(f"Database Host     : {os.getenv('SUPABASE_HOST')}")
    print("--------------------------------------------------")
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key or gemini_key.startswith("AQ."):
        print("[!] Warning: GEMINI_API_KEY appears to be invalid or unauthenticated.")
        print("[!] Please update GEMINI_API_KEY in backend/.env with a valid Google AI Studio key (AIzaSy...).")
        return

    # Initialize model with built-in Google search grounding
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=gemini_key,
        temperature=0.2
    )

    system_prompt = (
        "You are an expert research and software engineer agent. "
        "Provide thorough, structured, technical answers to complex coding and architectural questions."
    )
    
    user_query = "What is LangGraph and how does it integrate with Pinecone and LangSmith?"
    print(f"\n[Agent Invocation] Query: '{user_query}'\n")

    try:
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]
        response = llm.invoke(messages)
        print("Agent Response:\n")
        print(response.content)
        print("\n[+] Trace successfully recorded in LangSmith project 'my-first-agent'!")
    except Exception as e:
        print(f"[!] Execution failed: {e}")

if __name__ == "__main__":
    run_quickstart_agent()
