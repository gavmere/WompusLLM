# Wompus LLM Discord Bot

This guide will walk you through setting up and running the Wompus LLM Discord bot.

## Getting Started

To use the Wompus LLM bot, you'll need two things: a Discord bot token and an OpenRouter API key.

### 1. Getting a Discord Bot Token

A Discord bot token is how the bot authenticates with the Discord API. Here's how to get one:

1.  **Create a new application on the Discord Developer Portal:**
    *   Go to the [Discord Developer Portal](https://discord.com/developers/applications).
    *   Click the "New Application" button.
    *   Give your application a name and click "Create".

2.  **Create a Bot User:**
    *   In your application's settings, go to the "Bot" tab.
    *   Click "Add Bot".
    *   You can give your bot a custom username and avatar here.

3.  **Get your Bot Token:**
    *   On the "Bot" tab, you'll see your bot's token. Click "Reset Token" to reveal it, and be sure to copy it somewhere safe. **This token is a secret and should not be shared with anyone.**

4.  **Invite the bot to your server:**
    *   Go to the "OAuth2" -> "URL Generator" tab in your application's settings.
    *   Select the `bot` scope.
    *   In the "Bot Permissions" section that appears, select the permissions your bot needs. For basic functionality, you'll need:
        *   `Read Messages/View Channels`
        *   `Send Messages`
        *   `Manage Messages`
        *   `Embed Links`
        *   `Attach Files`
        *   `Read Message History`
        *   `Use External Emojis`
    *   Copy the generated URL and paste it into your browser to invite the bot to your Discord server.

### 2. Getting an OpenRouter API Key

OpenRouter provides access to a wide variety of large language models.

1.  **Create an OpenRouter Account:**
    *   Go to [OpenRouter.ai](https://openrouter.ai/).
    *   Sign up for an account.

2.  **Get your API Key:**
    *   Once you're logged in, go to your account settings or dashboard.
    *   You should find your API key there. Copy it.
    *   You should also fund the account.

### 3. Installing Requirements

Before running the bot, you'll need to install the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```


## Configuration

The bot is configured using the `config.yaml` file. Open it in a text editor and fill in the required values.

### `config.yaml` Options

Here is a breakdown of the available options in `config.yaml`:

*   `DISCORD_TOKEN`: Your Discord bot token.
*   `OPENROUTER_API_KEY`: Your OpenRouter API key.
*   `SYSTEM_PROMPT`: The default system prompt used by the bot. This sets the personality and instructions for the AI.
*   `DEFAULT_MODEL`: The default model to use for conversations. This is also the model used for automatically renaming channels.
*   `N_MESSAGES_CHANNEL_NAME_UPDATE`: The number of messages the model will consider when automatically renaming a channel. Set to `-1` to use the entire conversation history.
*   `N_CHANNEL_NAME_UPDATE`: The number of messages that need to be sent in a channel before the bot attempts to automatically rename it.
*   `CHAT_COMPLETION`: Settings for the AI's responses.
    *   `MAX_TOKENS`: The maximum length of the AI's response.
    *   `TEMPERATURE`: Controls the randomness of the output. Higher values (like 1.0) are more creative, while lower values (like 0.1) are more deterministic.
    *   `TOP_P`: An alternative to temperature that samples from a smaller set of likely next words.
    *   `FREQUENCY_PENALTY`: Reduces the chance of the AI repeating the same line of text.
    *   `PRESENCE_PENALTY`: Reduces the chance of the AI talking about new topics when it's not appropriate.
*   `LOGGING`: Configures logging for the bot.
    *   `ENABLED`: Set to `true` to enable logging.
    *   `TO_CONSOLE`: Set to `true` to print logs to the console.
    *   `LEVEL`: The minimum level of logs to record (e.g., `INFO`, `DEBUG`, `WARNING`, `ERROR`).
    *   `FILE`: The name of the log file.
    *   `MAX_SIZE`: The maximum size of the log file in bytes.
*   `UI`:
    *   `SELECTION_EMOJIS`: The emojis used for model selection in the Discord UI.
*   `MODEL_DATA`: This section defines the models available to the bot. You can add, remove, or modify the models in this list. You can find more models and their details on the [OpenRouter models page](https://openrouter.ai/models). It is a list of model groups, where each group has:
    *   `SERIES`: A grouping of models, often by the provider (e.g., OpenAI, Anthropic, Google).
    *   `PROVIDER`: The company that created the model.
    *   `MODELS`: A list of models from that provider, each with:
        *   `NAME`: A user-friendly name for the model.
        *   `DESCRIPTION`: A short description of the model's capabilities.
        *   `MODEL_ID`: The specific ID for the model from OpenRouter.
        *   `INPUT_PRICE`: The cost per 1 million input tokens.
        *   `OUTPUT_PRICE`: The cost per 1 million output tokens.
        *   `CONTEXT_LIMIT`: The maximum number of tokens the model can process in a single request.
        *   `ENABLE_IMAGES`: Whether the model can process images.

## Running the Bot

Once you have configured `config.yaml` with your `DISCORD_TOKEN` and `OPENROUTER_API_KEY`, you can run the bot:

```bash
python Wompus.py
```

## Usage

### Initial Setup

For the best experience, it's recommended to initialize the server with a specific channel structure.

> **⚠️ Warning:** The `!init` command will delete **all existing channels and roles** on your server. There is no way to recover them. Use this command with extreme caution and only on a new or test server.

To initialize the server, run the `!init` command in any channel. This will:
1.  Delete all current channels and roles.
2.  Create an `ADMIN` category with a channel that the bot will ignore.
3.  Set up the server for the bot's features.

### Creating and Using AI Channels

1.  **Create a new text channel.**
2.  The bot will automatically post a message allowing you to select an AI model for that channel using emoji reactions.
3.  Once a model is selected, you can start chatting with the AI.
4.  The bot supports text and, for compatible models, images.
5.  Active channels will naturally stay at the top of your channel list in Discord.
6.  Updates to the channel name will occur as defined in the config file