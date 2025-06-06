import discord
import time
from discord.ext import commands
from utils import (construct_prompt, get_response, get_channel_name, sanitize_channel_name, 
                   read_token_count, DISCORD_TOKEN, MODEL, N_CHANNEL_NAME_UPDATE,
                   get_model_providers, get_models_for_provider, get_model_id_by_name, find_model_by_id,
                   get_emoji_for_index, find_emoji_index)
from logger import logger

intents = discord.Intents.all()
intents.message_content = True
intents.messages = True
bot = commands.Bot(command_prefix='!', intents=intents)



@bot.command(name='init')
async def init(ctx):
    """Intializes the bot in the server"""
    if not (ctx.channel.category and 
            ctx.channel.category.name.lower() == "admin" and 
            ctx.channel.name.lower() == "admin"):
        return
    await ctx.send("Deleting all channels except admin")
    had_admin_channel = False
    all_channels = await ctx.guild.fetch_channels()
    for channel in all_channels:
        if channel.name.lower() == "admin":
            had_admin_channel = True
            continue
        else:
            await channel.delete()
    if not had_admin_channel:
        category = await ctx.guild.create_category(name="admin")
        await ctx.guild.create_text_channel(name="admin", category=category)

@bot.event
async def on_ready():
    logger.info(f'We have logged in as {bot.user}')

@bot.event
async def on_guild_channel_create(channel):
    # Skip if the channel is in the admin category
    if channel.name.lower() == "admin":
        return
    await channel.edit(topic=f"Input Tokens: 0 Output Tokens: 0")
    
    # Get providers dynamically from config
    providers = get_model_providers()
    
    model_selection_embed = discord.Embed(title=MODEL, description=f"Select a model provider to use for the conversation. By reacting to the message below, you will be able to select the model you want to use or just start chatting with {MODEL}")
    
    # Add emoji reactions for each provider (no longer limited to 6)
    for i, provider in enumerate(providers):
        emoji = get_emoji_for_index(i)
        model_selection_embed.add_field(name=emoji, value=f"{provider.title()} Models")
    
    message = await channel.send(embed=model_selection_embed)
    
    # Add reactions dynamically for all providers
    for i in range(len(providers)):
        emoji = get_emoji_for_index(i)
        await message.add_reaction(emoji)

@bot.event
async def on_raw_reaction_add(payload):
    global MODEL

    #Reaction from bot, so ignore
    if payload.user_id == bot.user.id:
        return

    channel = bot.get_channel(payload.channel_id)
    if not channel:
        return

    # Get the first message in the channel
    first_message = None
    async for message in channel.history(limit=1, oldest_first=True):
        first_message = message
        break

    # If the reaction is on the first message, then we need to handle the model selection
    if payload.message_id == first_message.id:
        await first_message.remove_reaction(payload.emoji, payload.member)
        
        if not first_message.embeds:
            return
            
        embed_title = first_message.embeds[0].title
        providers = get_model_providers()
        
        # Check if we're selecting a provider (initial selection)
        if embed_title == MODEL:  # This is the initial provider selection
            emoji_index = find_emoji_index(payload.emoji.name)
            
            if emoji_index is not None and emoji_index < len(providers):
                selected_provider = providers[emoji_index]
                models = get_models_for_provider(selected_provider)
                
                # Create embed for model selection within this provider
                provider_embed = discord.Embed(
                    title=f"{selected_provider.title()} Models", 
                    description=f"You have selected {selected_provider.title()} Models. Choose a specific model to use for the conversation."
                )
                
                # Add all models from this provider (no longer limited to 6)
                for i, model in enumerate(models):
                    emoji = get_emoji_for_index(i)
                    # Truncate description if too long for Discord field limit
                    description = model.get('DESCRIPTION', 'No description')
                    if len(description) > 900:  # Leave room for model name
                        description = description[:897] + "..."
                    provider_embed.add_field(
                        name=emoji, 
                        value=f"**{model['NAME']}**\n{description}",
                        inline=False
                    )
                
                await first_message.edit(embed=provider_embed)
                
                # Add reactions for available models (clear existing ones first)
                await first_message.clear_reactions()
                for i in range(len(models)):
                    emoji = get_emoji_for_index(i)
                    await first_message.add_reaction(emoji)
                    
        else:
            # We're selecting a specific model within a provider
            provider_name = None
            for provider in providers:
                if embed_title == f"{provider.title()} Models":
                    provider_name = provider
                    break
            
            if provider_name:
                models = get_models_for_provider(provider_name)
                emoji_index = find_emoji_index(payload.emoji.name)
                
                if emoji_index is not None and emoji_index < len(models):
                    selected_model = models[emoji_index]
                    MODEL = selected_model["MODEL_ID"] 
                    
                    finished_embed = discord.Embed(
                        title=MODEL, 
                        description=f"You have selected: **{selected_model['NAME']}**\n\n{selected_model.get('DESCRIPTION', '')}\n\nGo ahead and start chatting!"
                    )
                    finished_embed.add_field(name="Provider", value=provider_name.title(), inline=True)
                    finished_embed.add_field(name="Context Limit", value=f"{selected_model.get('CONTEXT_LIMIT', 'N/A'):,} tokens", inline=True)
                    finished_embed.add_field(name="Pricing", value=f"In: ${selected_model.get('INPUT_PRICE', 0)}/M | Out: ${selected_model.get('OUTPUT_PRICE', 0)}/M", inline=True)
                    
                    await first_message.edit(embed=finished_embed)
                    await first_message.clear_reactions()
                    
    return

@bot.event
async def on_message(message):
    # Process commands first
    await bot.process_commands(message)
    
    # Skip if this message is a command
    if message.content.startswith(bot.command_prefix):
        return
    
    # Skip if the channel is in the admin category
    if message.channel.name.lower() == "admin":
        return
    
    channel_model = MODEL
    if message.author == bot.user:
        return

    # Initialize channel and messages
    channel = message.channel
    messages = []
    time_start = time.time()
    
    # Fetch all messages once and process them
    first_message = None
    total_input_tokens = 0
    total_output_tokens = 0
    
    async for all_message in channel.history(limit=None, oldest_first=True):
        if first_message is None:
            first_message = all_message
            # Extract model from first message embed title if it exists
            if first_message and first_message.embeds:
                try:
                    channel_model = first_message.embeds[0].title
                    logger.info(f"Using model: {channel_model}")
                except (IndexError, AttributeError):
                    logger.warning("Could not extract model from first message embed")
            continue  # Skip the first message (model selection)
            
        if all_message.content.startswith(bot.command_prefix):
            continue
            
        if all_message.author != bot.user:
            if all_message.content:
                messages.append((all_message.author.name, all_message.content, 'text'))
            if all_message.attachments:
                for attachment in all_message.attachments:
                    if attachment.content_type and 'image' in attachment.content_type:
                        messages.append((all_message.author.name, attachment.url, 'image_url'))
        # wompus case - check if message has embeds before accessing
        elif all_message.author == bot.user and all_message.embeds:
            if all_message.embeds[0].description:
                messages.append(("Wompus", all_message.embeds[0].description, 'text'))
            if all_message.embeds[0].image:
                messages.append(("Wompus", all_message.embeds[0].image.url, 'image_url'))
            # Calculate token totals while we're already iterating
            if all_message.embeds[0].footer:
                footer_text = all_message.embeds[0].footer.text
                if footer_text and "Input Tokens:" in footer_text and "Output Tokens:" in footer_text:
                    try:
                        # Parse footer text: "Time taken: X.XX seconds | Input Tokens: XXX | Output Tokens: XXX"
                        parts = footer_text.split(" | ")
                        for part in parts:
                            if part.startswith("Input Tokens:"):
                                total_input_tokens += int(part.split(":")[1].strip())
                            elif part.startswith("Output Tokens:"):
                                total_output_tokens += int(part.split(":")[1].strip())
                    except (ValueError, IndexError):
                        # Skip if we can't parse the footer
                        continue

    response_embed = discord.Embed(title=channel_model, description="Thinking...")
    response_message = await message.channel.send(embed=response_embed)
    prompt = construct_prompt(messages)
    logger.debug(prompt)
    response = await get_response(prompt, channel_model)
    
    # Handle API errors gracefully
    if "error" in response:
        error_data = response["error"]
        status = error_data.get('code', 'N/A')
        message = error_data.get('message', 'Unknown error')
        error_embed = discord.Embed(title=f"API Error ({status})", description=message, color=discord.Color.red())
        await response_message.edit(embed=error_embed)
        return
        
    content = response["choices"][0]["message"]["content"]
    input_tokens = response["usage"]["prompt_tokens"]
    output_tokens = response["usage"]["completion_tokens"]
    response_embed = discord.Embed(title=channel_model, description=content)
    response_embed.set_footer(text=f"Time taken: {time.time() - time_start:.2f} seconds | Input Tokens: {input_tokens} | Output Tokens: {output_tokens}")
    await response_message.edit(embed=response_embed)
    edit_kwargs = {"position": 0}
    # Check if we need to rename channel and update topic
    if len(prompt) % N_CHANNEL_NAME_UPDATE == 0:
        new_topic = f"Input Tokens: {total_input_tokens + input_tokens} Output Tokens: {total_output_tokens + output_tokens}"
        edit_kwargs["topic"] = new_topic
        
        # Update channel name
        channel_name = await get_channel_name(prompt)
        sanitized_name = sanitize_channel_name(channel_name)
        if sanitized_name:
            edit_kwargs["name"] = sanitized_name
            logger.info(f"Channel renamed to: {sanitized_name}")
        else:
            logger.warning(f"Invalid channel name received: '{channel_name}'")
    
    # Single channel edit with all changes (only if there are changes to make)
    if len(edit_kwargs) >= 1: 
        try:
            await channel.edit(**edit_kwargs)
        except discord.errors.HTTPException as e:
            logger.error(f"Failed to edit channel: {e}")

bot.run(DISCORD_TOKEN)