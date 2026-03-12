from google import genai
from config import MODEL_NAME, RULES_PROMPT, QUERY_TEMPLATE
import os
from dotenv import load_dotenv

load_dotenv()


def init_chat():
    """Create the Gemini client and start a chat session.
    Returns the chat object.
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    client = genai.Client(api_key=api_key)

    chat = client.chats.create(model=MODEL_NAME)

    return client, chat


def send_rules(chat):
    """Send the rules prompt as the first message in the chat.
    Returns the model's confirmation response text.
    """

    response = chat.send_message(RULES_PROMPT)

    confirmation = response.text

    print("Model Confirmation")
    print(confirmation)

    return confirmation


def send_query(chat, category, tags):
    """Send a category/tag generation query.
    Returns the raw response text.
    """

    tags_str = ", ".join(tags)

    query = QUERY_TEMPLATE.format(category=category, tags=tags_str)

    response = chat.send_message(query)

    return response.text


if __name__ == "__main__":
    client, chat = init_chat()
    send_rules(chat)
    raw = send_query(chat, "Brightness/Spectral", ["bright", "dark"])
    print(raw)
