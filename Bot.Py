import discord
from discord.ext import commands
import os
import json
from pathlib import Path

# --- CONFIGURATION ---
TOKEN = "MTUxODU0Mjc0MDk2NTgyMjQ2NA.Gpk7xN.ZLP1BrLfBEYhNj1rcdwDdgXCv68N7-xL108jnY"
COMMAND_PREFIX = "!"
DATA_FOLDER = "./bot_data"  # Folder where your message files are stored
FORWARD_CONFIG_FILE = "forward_config.json"

# Ensure data folder exists
os.makedirs(DATA_FOLDER, exist_ok=True)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix=COMMAND_PREFIX, intents=intents)

# --- FORWARD CONFIG MANAGEMENT ---
def load_forward_config():
    if os.path.exists(FORWARD_CONFIG_FILE):
        with open(FORWARD_CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"forwards": []}

def save_forward_config(config):
    with open(FORWARD_CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

forward_config = load_forward_config()

# --- COMMANDS ---

@bot.command()
async def sendfile(ctx, filename: str):
    """
    Send a file from the data folder by name.
    Usage: !sendfile message.txt
    """
    file_path = os.path.join(DATA_FOLDER, filename)
    
    if not os.path.exists(file_path):
        await ctx.send(f"❌ File `{filename}` not found in `{DATA_FOLDER}`.")
        return
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        await ctx.send(content)
        await ctx.message.add_reaction("✅")
    except Exception as e:
        await ctx.send(f"❌ Error reading file: {e}")

@bot.command()
async def listfiles(ctx):
    """
    List all available files in the data folder.
    Usage: !listfiles
    """
    files = [f for f in os.listdir(DATA_FOLDER) if os.path.isfile(os.path.join(DATA_FOLDER, f))]
    
    if not files:
        await ctx.send("📂 No files found in the data folder.")
        return
    
    file_list = "\n".join([f"• `{f}`" for f in files])
    await ctx.send(f"📁 **Available files:**\n{file_list}")

@bot.command()
async def sendmessage(ctx, *, message_text: str):
    """
    Send a custom message.
    Usage: !sendmessage Hello everyone!
    """
    await ctx.send(message_text)
    await ctx.message.add_reaction("✅")

@bot.command()
async def uploadsend(ctx):
    """
    Send the file attached to this command.
    Usage: !uploadsend (attach a file)
    """
    if not ctx.message.attachments:
        await ctx.send("❌ Please attach a file to this command.")
        return
    
    attachment = ctx.message.attachments[0]
    
    # Save to data folder
    file_path = os.path.join(DATA_FOLDER, attachment.filename)
    await attachment.save(file_path)
    
    # Send file content if it's text, otherwise send as file
    if attachment.filename.endswith(('.txt', '.md', '.json', '.py', '.js', '.html', '.css', '.log')):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        await ctx.send(f"📄 **{attachment.filename}:**\n```{content[:1900]}```")
    else:
        await ctx.send(f"📎 Sent file: `{attachment.filename}`", file=discord.File(file_path))
    
    await ctx.message.add_reaction("✅")

# --- FORWARDING SYSTEM ---

@bot.command()
@commands.has_permissions(administrator=True)
async def forward(ctx, source_channel: discord.TextChannel, target_channel: discord.TextChannel):
    """
    Forward all messages from source channel to target channel.
    Usage: !forward #source #target
    """
    config = load_forward_config()
    
    # Check if already exists
    for fwd in config["forwards"]:
        if fwd["source"] == source_channel.id and fwd["target"] == target_channel.id:
            await ctx.send("⚠️ This forward already exists.")
            return
    
    config["forwards"].append({
        "source": source_channel.id,
        "target": target_channel.id,
        "guild": ctx.guild.id
    })
    save_forward_config(config)
    
    await ctx.send(f"✅ Now forwarding messages from {source_channel.mention} to {target_channel.mention}")

@bot.command()
@commands.has_permissions(administrator=True)
async def stopforward(ctx, source_channel: discord.TextChannel, target_channel: discord.TextChannel):
    """
    Stop forwarding from source to target.
    Usage: !stopforward #source #target
    """
    config = load_forward_config()
    original_len = len(config["forwards"])
    
    config["forwards"] = [
        f for f in config["forwards"] 
        if not (f["source"] == source_channel.id and f["target"] == target_channel.id)
    ]
    
    if len(config["forwards"]) == original_len:
        await ctx.send("⚠️ No such forward configuration found.")
        return
    
    save_forward_config(config)
    await ctx.send(f"🛑 Stopped forwarding from {source_channel.mention} to {target_channel.mention}")

@bot.command()
async def listforwards(ctx):
    """
    List all active forwards.
    Usage: !listforwards
    """
    config = load_forward_config()
    
    if not config["forwards"]:
        await ctx.send("📭 No active forwards.")
        return
    
    lines = []
    for fwd in config["forwards"]:
        source = bot.get_channel(fwd["source"])
        target = bot.get_channel(fwd["target"])
        src_name = source.mention if source else f"`{fwd['source']}`"
        tgt_name = target.mention if target else f"`{fwd['target']}`"
        lines.append(f"• {src_name} → {tgt_name}")
    
    await ctx.send("🔄 **Active Forwards:**\n" + "\n".join(lines))

# --- EVENT LISTENERS ---

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user.name}")
    print(f"Bot ID: {bot.user.id}")
    print("------")

@bot.event
async def on_message(message):
    # Don't respond to bot's own messages
    if message.author == bot.user:
        return
    
    # Handle forwarding
    config = load_forward_config()
    for fwd in config["forwards"]:
        if message.channel.id == fwd["source"]:
            target = bot.get_channel(fwd["target"])
            if target:
                # Forward the message content
                content = f"**{message.author}** in <#{message.channel.id}>:\n{message.content}"
                
                # Forward attachments
                files = []
                for attachment in message.attachments:
                    file_path = os.path.join(DATA_FOLDER, attachment.filename)
                    await attachment.save(file_path)
                    files.append(discord.File(file_path))
                
                await target.send(content, files=files)
    
    # Process commands
    await bot.process_commands(message)

# --- ERROR HANDLING ---

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ You don't have permission to use this command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing argument. Usage: `{ctx.command.usage or ctx.command.name}`")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Ignore unknown commands
    else:
        await ctx.send(f"❌ Error: {error}")

# --- RUN ---
if __name__ == "__main__":
    bot.run(TOKEN)
