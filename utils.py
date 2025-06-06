import yaml
import aiohttp
import re
from logger import logger

with open('config.yaml', 'r') as f:
    data = yaml.load(f, Loader=yaml.SafeLoader)
    
DISCORD_TOKEN = data["DISCORD_TOKEN"]
OPENROUTER_API_KEY = data["OPENROUTER_API_KEY"]
SYSTEM_PROMPT = data["SYSTEM_PROMPT"]
MODEL = data["DEFAULT_MODEL"]
CHAT_COMPLETION_OPTIONS = data["CHAT_COMPLETION"]
N_CHANNEL_NAME_UPDATE = data["N_CHANNEL_NAME_UPDATE"]
MODEL_DATA = data["MODEL_DATA"]
SELECTION_EMOJIS = data["UI"]["SELECTION_EMOJIS"]
N_MESSAGES_CHANNEL_NAME_UPDATE = data["N_MESSAGES_CHANNEL_NAME_UPDATE"]

def get_emoji_for_index(index):
    """Get emoji for a given index, cycling through available emojis if needed"""
    if index < len(SELECTION_EMOJIS):
        return SELECTION_EMOJIS[index]
    # If we run out of emojis, cycle through them
    return SELECTION_EMOJIS[index % len(SELECTION_EMOJIS)]

def find_emoji_index(emoji):
    """Find the index of an emoji in the selection list"""
    try:
        return SELECTION_EMOJIS.index(emoji)
    except ValueError:
        return None

def get_model_providers():
    """Get all model providers from config"""
    providers = []
    for series_item in MODEL_DATA["SERIES"]:
        providers.extend(list(series_item.keys()))
    return providers

def get_models_for_provider(provider):
    """Get all models for a specific provider"""
    for series_item in MODEL_DATA["SERIES"]:
        if provider in series_item:
            return series_item[provider]
    return []

def get_model_by_name(provider, model_name):
    """Get model details by provider and model name"""
    models = get_models_for_provider(provider)
    for model in models:
        if model["NAME"] == model_name:
            return model
    return None

def get_model_id_by_name(provider, model_name):
    """Get model ID for API calls by provider and model name"""
    model = get_model_by_name(provider, model_name)
    return model["MODEL_ID"] if model else None

def find_model_by_id(model_id):
    """Find model details by MODEL_ID (reverse lookup)"""
    for series_item in MODEL_DATA["SERIES"]:
        for provider_name, models in series_item.items():
            for model in models:
                if model["MODEL_ID"] == model_id:
                    return {
                        "provider": provider_name,
                        "model": model
                    }
    return None

def construct_prompt(messages):
    prompt = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # Group consecutive messages from the same author
    current_role = None
    current_content = []
    
    for message in messages:
        author, content, msg_type = message
        role = "assistant" if author == "Wompus" else "user"

        # Assistant messages cannot contain images.
        if role == "assistant" and msg_type == 'image_url':
            continue
        
        # If role changes, add the previous message to prompt
        if current_role is not None and current_role != role:
            if current_role == "assistant":
                # Consolidate text parts for assistant into a single string
                text_content = " ".join([part['text'] for part in current_content if part['type'] == 'text'])
                if text_content:
                    prompt.append({"role": current_role, "content": text_content})
            else:  # User messages are always multipart
                prompt.append({"role": current_role, "content": current_content})
            current_content = []
        
        current_role = role
        
        # Add content based on message type
        if msg_type == 'text':
            current_content.append({"type": "text", "text": content})
        elif msg_type == 'image_url' and role == 'user':
            # Format image URL according to OpenRouter API specification
            current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": content  # The URL from Discord is already in the correct format
                }
            })
    
    # Add the last message if there is one
    if current_role is not None and current_content:
        if current_role == "assistant":
            text_content = " ".join([part['text'] for part in current_content if part['type'] == 'text'])
            if text_content:
                prompt.append({"role": current_role, "content": text_content})
        else:  # User messages are always multipart
            prompt.append({"role": current_role, "content": current_content})
    
    return prompt

async def make_openrouter_request(messages, model=None):
    """Make an async request to OpenRouter API using aiohttp"""
    if model is None:
        model = MODEL
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    logger.info(f"Making request to {url} with model {model}")
    payload = {
        "temperature":CHAT_COMPLETION_OPTIONS["TEMPERATURE"],
        "top_p":CHAT_COMPLETION_OPTIONS["TOP_P"],
        "frequency_penalty":CHAT_COMPLETION_OPTIONS["FREQUENCY_PENALTY"],
        "presence_penalty":CHAT_COMPLETION_OPTIONS["PRESENCE_PENALTY"],
        "max_tokens":CHAT_COMPLETION_OPTIONS["MAX_TOKENS"]  ,
        "model": model,
        "messages": messages,
        "usage": True
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as response:
            if response.status == 200:
                result = await response.json()
                return result
            else:
                try:
                    # Try to parse the error response as JSON
                    error_data = await response.json()
                    logger.error(f"API request failed with status {response.status}: {error_data}")
                    return error_data
                except Exception:
                    # If it's not JSON, create a synthetic error object
                    error_text = await response.text()
                    logger.error(f"API request failed with status {response.status}: {error_text}")
                    return {
                        "error": {
                            "message": f"API request failed with status {response.status}: {error_text}",
                            "code": response.status
                        }
                    }

async def get_response(prompt, model):
    return await make_openrouter_request(prompt, model)

async def get_channel_name(messages):
    if N_MESSAGES_CHANNEL_NAME_UPDATE == -1:

        messages_copy = messages.copy()
    else:
        messages_copy = messages[-N_MESSAGES_CHANNEL_NAME_UPDATE:].copy() if N_MESSAGES_CHANNEL_NAME_UPDATE > 0 else messages.copy()
    messages_copy.append({"role": "user", "content": "Based on the previous couple of messages, summarize the conversation in 2-3 words separated by a dash(-). Omit any other text besides the words, you may use emojis."})
    response = await make_openrouter_request(messages_copy)
    return response["choices"][0]["message"]["content"]

def sanitize_channel_name(name):
    if not name:
        return None
    name = name.strip()
    name = re.sub(r'[^a-zA-Z0-9\-_\s]', '', name.lower())
    name = re.sub(r'\s+', '-', name)
    name = re.sub(r'-+', '-', name)
    name = name.strip('-')

    if len(name) < 1:
        return None
    if len(name) > 100:
        name = name[:100].rstrip('-')
    
    return name if len(name) >= 1 else None

def read_token_count(topic_string):
    """Reads the token count from the topic string that is int the format of f"Input Tokens: {input_tokens} Output Tokens: {output_tokens}" """
    if not topic_string:
        return 0, 0
    numbers = re.findall(r'\d+', topic_string)
    return int(numbers[0]), int(numbers[1])