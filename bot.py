import discord
from discord.ext import commands, tasks
from discord.utils import get
import datetime
import json
import openai
import os

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True

bot = commands.Bot(command_prefix='/', intents=intents)

DATA_FILE = 'bot_data.json'
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai.api_key = OPENAI_API_KEY

def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {'last_processed_message_id': None}

def save_data(data):
    with open(DATA_FILE, 'w') as file:
        json.dump(data, file)

def analyze_messages(messages):
    combined_text = "\n".join(messages)
    # Limit characters to prevent exceeding token limits
    max_length = 4000  
    if len(combined_text) > max_length:
        combined_text = combined_text[-max_length:]
    
    prompt = (
        "Analyze the following conversation and list the key points as bullet points. "
        "Each bullet point should start with an emoji relevant to the nature of the task or reminder. "
        "Ensure the summary is clear and detailed, helping users with ADHD or Alzheimer's remember important tasks and appointments.\n\n"
        f"Conversation:\n{combined_text}\n\n"
        "Bullet Points:\n"
    )
    response = openai.Completion.create(
        engine="text-davinci-002",
        prompt=prompt,
        max_tokens=300,
        n=1,
        stop=["\n\n"],
        temperature=0.5,
    )
    return response.choices[0].text.strip()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    daily_digest.start()  # Start the daily digest loop

@tasks.loop(time=datetime.time(hour=18, minute=0))
async def daily_digest():
    data = load_data()
    last_processed_message_id = data['last_processed_message_id']
    channel = discord.utils.get(bot.get_all_channels(), name='cozy-home')
    reminder_channel = discord.utils.get(bot.get_all_channels(), name='reminder')
    goofballs_role = get(channel.guild.roles, name='goofballs')

    if channel is not None and reminder_channel is not None:
        messages = await channel.history(limit=100, after=last_processed_message_id).flatten()
        message_texts = [msg.content for msg in messages]
        if message_texts:
            summary = analyze_messages(message_texts)
            await reminder_channel.send(f"@{goofballs_role.name}\n**Daily Digest:**\n{summary}")
            data['last_processed_message_id'] = messages[-1].id
            save_data(data)

@bot.command()
async def wtm(ctx):
    if ctx.channel.name == 'cozy-home':
        data = load_data()
        last_processed_message_id = data['last_processed_message_id']
        reminder_channel = discord.utils.get(ctx.guild.channels, name='reminder')
        goofballs_role = get(ctx.guild.roles, name='goofballs')

        messages = await ctx.channel.history(limit=100, after=last_processed_message_id).flatten()
        message_texts = [msg.content for msg in messages]
        if message_texts:
            summary = analyze_messages(message_texts)
            await reminder_channel.send(f"@{goofballs_role.name}\n**Manual Digest:**\n{summary}")
            data['last_processed_message_id'] = messages[-1].id
            save_data(data)
        else:
            await ctx.send("No new messages found.")

bot.run('DISCORD_BOT_TOKEN')
