import discord
from discord.ext import commands, tasks
import time
import random
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# --- SECURE TOKEN LOADING ---
load_dotenv()                       
TOKEN = os.getenv('DISCORD_TOKEN')

# --- RAILWAY DATA RECOVERY (VARIABLE INJECTION) ---
if not os.path.exists('data/hoard.json'):
    initial_data = os.getenv('INITIAL_DATA')
    if initial_data:
        os.makedirs('data', exist_ok=True)
        with open('data/hoard.json', 'w') as f:
            f.write(initial_data)
        print("Data successfully restored from Railway variables!")

intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# --- SETTINGS ---
ANNOUNCEMENT_CHANNEL_ID = 1306602160527507456 
CHAMPION_ROLE_ID = 1500011207929892884 
VETERAN_ROLE_ID = 1500010986835542138   

# --- GLOBALS ---
current_dragon = None  
last_spawn_message = None 
spawn_channel_id = 1109766164764184576  
next_spawn_time = 0 
last_roll_time = {}

# --- CUSTOM FLY AWAY MESSAGES ---
fly_away_messages = {
    "Red Dragon": "*The Red Dragon let out one last roar and flew away.*",
    "Basic Dragon Egg": "*The egg grew too cold and vanished into the brush.",
    "Astral Elder Dragon": "*The sky cleared as the Astral Elder Dragon ascended back to the stars.*",
    "Rusty Satellite": "*The satellite's signal flickered out as it drifted into deep space.*",
    "Glowing Meteor": "*The meteor finally cooled down and stopped glowing, becoming just a rock.*",
    "Void Fragment": "*The vibration stopped as the Void Fragment collapsed into nothingness.*"
}

# --- CUSTOM FAIL MESSAGES ---
fail_messages = {
    "Red Dragon": "The Red Dragon swiped its tail, knocking your dice out of your hand!",
    "Basic Dragon Egg": "The egg rolled into a thicket before you could grab it.",
    "Astral Elder Dragon": "The Elder Dragon simply ignored your presence as it hummed.",
    "Rusty Satellite": "The satellite spun wildly, making it impossible to catch.",
    "Glowing Meteor": "The heat was too intense! You had to jump back!",
    "Void Fragment": "Your hands passed right through the fragment. It's not fully in this dimension..."
}

# --- DATA HELPERS ---
def load_data():
    if os.path.exists('data/hoard.json'):
        with open('data/hoard.json', 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    if not os.path.exists('data'):
        os.makedirs('data')
    with open('data/hoard.json', 'w') as f:
        json.dump(data, f, indent=4)

# --- LEADERBOARD INTERFACE ---
class LeaderboardView(discord.ui.View):
    def __init__(self, data, title, key_type, requester):
        super().__init__(timeout=60)
        self.data = data
        self.title = title
        self.key_type = key_type
        self.requester = requester
        self.current_page = 0
        self.per_page = 10
        self.pages = [data[i:i + self.per_page] for i in range(0, len(data), self.per_page)]

    def create_embed(self):
        page_data = self.pages[self.current_page]
        description = ""
        start_rank = (self.current_page * self.per_page) + 1
        
        for i, (user_id, stats) in enumerate(page_data):
            rank = start_rank + i
            points = stats[self.key_type]
            description += f"**{rank}:** {points}pts from <@{user_id}>\n"

        embed = discord.Embed(title=self.title, description=description, color=discord.Color.gold())
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.pages)} | Requested by {self.requester}")
        return embed

    @discord.ui.button(label="◀", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="▶", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.create_embed(), view=self)
        else:
            await interaction.response.defer()

# --- TASKS ---
@tasks.loop(hours=24)
async def check_monthly_reset():
    now = datetime.now()
    if now.day == 1:
        data = load_data()
        if not data: return

        sorted_data = sorted(data.items(), key=lambda x: x[1].get('monthly', 0), reverse=True)
        top_10 = sorted_data[:10]
        
        if not top_10 or top_10[0][1].get('monthly', 0) == 0: return

        winner_id = top_10[0][0]
        data[winner_id]['wins'] = data[winner_id].get('wins', 0) + 1

        channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(title="🏆 THE MONTHLY HOARD RESULTS 🏆", color=discord.Color.gold())
            lb_text = ""
            for i, (user_id, stats) in enumerate(top_10):
                rank = i + 1
                points = stats.get('monthly', 0)
                if rank == 1:
                    lb_text += f"✨ **RANK {rank}:** {points}pts — <@{user_id}> ✨\n"
                else:
                    lb_text += f"**RANK {rank}:** {points}pts — <@{user_id}>\n"
            embed.add_field(name="Final Standings", value=lb_text, inline=False)
            await channel.send(embed=embed)

        for uid in data:
            data[uid]['monthly'] = 0
            data[uid]['inventory'] = {} 
            data[uid]['pity'] = 0 
        
        save_data(data)

@tasks.loop(minutes=1)
async def despawn_timer():
    global current_dragon, last_spawn_message, next_spawn_time
    
    if current_dragon and last_spawn_message:
        time_since_spawn = (datetime.utcnow() - last_spawn_message.created_at.replace(tzinfo=None)).total_seconds()
        
        if time_since_spawn > 600: # 10 minutes
            dragon_name = current_dragon['name']
            flew_msg = fly_away_messages.get(dragon_name, f"The {dragon_name} disappeared into the mist...")
            
            await last_spawn_message.edit(content=f"**{flew_msg}**")
            
            current_dragon = None
            last_spawn_message = None
            next_spawn_time = 0
            print(f"DEBUG: {dragon_name} timed out and despawned.")

@tasks.loop(seconds=10) 
async def spawn_dragon_loop():
    global current_dragon, last_spawn_message, next_spawn_time
    
    if next_spawn_time == 0:
        wait_seconds = random.randint(300, 1800)
        next_spawn_time = time.time() + wait_seconds
        return

    if time.time() >= next_spawn_time and current_dragon is None:
        channel = bot.get_channel(spawn_channel_id)
        if channel is None: return

        dragons = [
            {"name": "Red Dragon", "sound": "**Rawr!**", "points": 5},
            {"name": "Basic Dragon Egg", "sound": "*Crackle...*", "points": 10},
            {"name": "Astral Elder Dragon", "sound": "*Celestial hum...*", "points": 40}, 
            {"name": "Rusty Satellite", "sound": "*Static whir...*", "points": 3},
            {"name": "Glowing Meteor", "sound": "*Sizzle!*", "points": 15},
            {"name": "Void Fragment", "sound": "*Vibration...*", "points": 30} 
        ]
        current_dragon = random.choice(dragons)
        last_spawn_message = await channel.send(f"{current_dragon['sound']}\n\nA wild **{current_dragon['name']}** has appeared! Use `!rd` to catch it!")
        next_spawn_time = 0

# --- EVENTS ---
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!hoardhelp | Catching Dragons!"))
    
    print(f'Logged in as {bot.user.name}')
    if not spawn_dragon_loop.is_running(): 
        spawn_dragon_loop.start()
    if not check_monthly_reset.is_running(): 
        check_monthly_reset.start()
    if not despawn_timer.is_running():
        despawn_timer.start()
    print('Ready to catch some dragons!')

# --- COMMANDS ---
@bot.command()
async def hoardhelp(ctx):
    embed = discord.Embed(
        title="🐲 Dragon Catcher - Player Guide",
        description="Track your progress and catch rare beasts! Here are the commands you can use:",
        color=discord.Color.green()
    )
    embed.add_field(name="🎮 Gameplay", value="`!rd` - Try to catch a dragon when one appears.", inline=False)
    embed.add_field(name="👤 Stats", value="`!profile` (or `!p`) - View your rank and rarest catches.", inline=False)
    embed.add_field(name="📊 Leaderboards", value="`!hlb` - Monthly rankings.\n`!ghlb` - Lifetime rankings.", inline=False)
    embed.set_footer(text="Watch the spawn channel for dragon sounds!")
    await ctx.send(embed=embed)

@bot.command(aliases=['p', 'stats'])
async def profile(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    uid = str(member.id)
    
    if uid not in data:
        return await ctx.send(f"{member.display_name} hasn't caught any dragons yet!")

    u_stats = data[uid]
    m_pts = u_stats.get('monthly', 0)
    g_pts = u_stats.get('global', 0)
    u_wins = u_stats.get('wins', 0)
    u_inv = u_stats.get('inventory', {})

    monthly_list = sorted(data.items(), key=lambda x: x[1].get('monthly', 0), reverse=True)
    global_list = sorted(data.items(), key=lambda x: x[1].get('global', 0), reverse=True)
    
    final_m_rank = "N/A"
    final_g_rank = "N/A"

    for i, (user_key, _) in enumerate(monthly_list):
        if user_key == uid:
            final_m_rank = i + 1
            break

    for i, (user_key, _) in enumerate(global_list):
        if user_key == uid:
            final_g_rank = i + 1
            break

    if g_pts > 1000: p_title = "Hoard Lord 👑"
    elif g_pts > 500: p_title = "Dragon Stalker 🏹"
    elif g_pts > 100: p_title = "Scaled Scout 🦎"
    else: p_title = "Hatchling 🥚"

    embed = discord.Embed(title=f"{member.display_name} - Dragon Hunter Profile", color=discord.Color.blue())
    embed.set_thumbnail(url=member.display_avatar.url)
    
    medals = []
    if u_wins > 0: medals.append(f"🏆 Season Wins: {u_wins}")
    for role in member.roles:
        if role.id == CHAMPION_ROLE_ID: medals.append("🎖️ Champion")
        if role.id == VETERAN_ROLE_ID: medals.append("🎖️ Veteran")
    
    embed.add_field(name="Titles & Medals", value=" | ".join(medals) if medals else "No medals yet", inline=False)
    embed.add_field(name="Rankings", value=f"**Monthly:** #{final_m_rank}\n**Global:** #{final_g_rank}", inline=True)
    embed.add_field(name="Scores", value=f"**Monthly:** {m_pts}\n**Global:** {g_pts}", inline=True)

    if u_inv:
        sorted_inv = sorted(u_inv.items(), key=lambda x: x[1], reverse=True)[:3]
        inv_text = "\n".join([f"🐲 {name} (x{count})" for name, count in sorted_inv])
        embed.add_field(name="Seasonal Top 3", value=inv_text, inline=False)
    else:
        embed.add_field(name="Seasonal Top 3", value="No catches this season", inline=False)

    embed.set_footer(text=f"Current Title: {p_title}")
    await ctx.send(embed=embed)

@bot.command()
async def rd(ctx):
    global current_dragon, last_spawn_message, next_spawn_time
    user_id = ctx.author.id
    mention = ctx.author.mention
    current_time = time.time()

    if user_id in last_roll_time and current_time < last_roll_time[user_id]:
        seconds_left = int(last_roll_time[user_id] - current_time)
        await ctx.send(f"{mention} You were whooshed! Wait {seconds_left}s before tossing the dice!")
        return

    if current_dragon is None:
        last_roll_time[user_id] = current_time + 5
        await ctx.send(f"{mention} *Whoosh*")
    else:
        data = load_data()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {"monthly": 0, "global": 0, "wins": 0, "inventory": {}, "pity": 0}
        
        if "pity" not in data[uid]: data[uid]["pity"] = 0

        roll_sounds = {"Red Dragon": "*Hsssskkkk*", "Basic Dragon Egg": "*Crackle!*", "Astral Elder Dragon": "*ROOOOOARRR*", "Rusty Satellite": "*Clank-clatter!*", "Glowing Meteor": "*Fwoosh-hiss!*", "Void Fragment": "*V-v-v-vrrrrmmm...*"}
        current_sound = roll_sounds.get(current_dragon['name'], "*Clink!*")
        
        base_roll = random.randint(1, 100)
        pity_bonus = data[uid]["pity"]
        total_roll = base_roll + pity_bonus
        
        success = False
        if current_dragon['points'] <= 5 and total_roll > 30: success = True
        elif current_dragon['points'] <= 15 and total_roll > 60: success = True
        elif total_roll > 90: success = True 

        if success:
            data[uid]["monthly"] += current_dragon['points']
            data[uid]["global"] += current_dragon['points']
            
            inv = data[uid].get("inventory", {})
            d_name = current_dragon['name']
            inv[d_name] = inv.get(d_name, 0) + 1
            data[uid]["inventory"] = inv

            for player_id in data:
                data[player_id]["pity"] = 0

            save_data(data)
            if last_spawn_message: await last_spawn_message.edit(content=f"{current_dragon['sound']}\n\n**Caught!**")
            
            bonus_text = f" (+{pity_bonus} luck)" if pity_bonus > 0 else ""
            await ctx.send(f"{mention}\nYou caught the **{current_dragon['name']}** with a roll of {base_roll}{bonus_text}!")
            
            current_dragon = None 
            last_spawn_message = None
            next_spawn_time = 0 
        else:
            data[uid]["pity"] += 2
            save_data(data)

            dragon_name = current_dragon['name']
            custom_fail = fail_messages.get(dragon_name, "It got away!")

            # Determine cooldown time
            if dragon_name == "Astral Elder Dragon": wait_time = 120
            elif dragon_name == "Red Dragon": wait_time = 30
            else: wait_time = 15
            
            last_roll_time[user_id] = current_time + wait_time
            
            # Combined fail message with cooldown timer
            await ctx.send(f"{mention} {current_sound}\n{custom_fail}\n(Rolled {base_roll} + {pity_bonus} luck. Total: {total_roll})\n**You can't roll for {wait_time}s!**")

@bot.command(aliases=['leaderboard', 'hoard'])
async def hlb(ctx):
    raw_data = load_data()
    sorted_data = sorted(raw_data.items(), key=lambda x: x[1]['monthly'], reverse=True)
    if not sorted_data: return await ctx.send("The leaderboard is currently empty!")
    view = LeaderboardView(sorted_data, "Monthly Dragon Catching Leaderboard", "monthly", ctx.author.display_name)
    await ctx.send(embed=view.create_embed(), view=view)

@bot.command(aliases=['lifetimehoard'])
async def ghlb(ctx):
    raw_data = load_data()
    sorted_data = sorted(raw_data.items(), key=lambda x: x[1]['global'], reverse=True)
    if not sorted_data: return await ctx.send("The leaderboard is currently empty!")
    view = LeaderboardView(sorted_data, "Global Lifetime Leaderboard", "global", ctx.author.display_name)
    await ctx.send(embed=view.create_embed(), view=view)

# --- ADMIN COMMANDS ---
@bot.command()
@commands.has_permissions(administrator=True)
async def spawn(ctx):
    global current_dragon, last_spawn_message, next_spawn_time
    channel = bot.get_channel(spawn_channel_id)
    dragons = [{"name": "Red Dragon", "sound": "**Rawr!**", "points": 5}, {"name": "Basic Dragon Egg", "sound": "*Crackle...*", "points": 10}, {"name": "Astral Elder Dragon", "sound": "*Celestial hum...*", "points": 40}]
    current_dragon = random.choice(dragons)
    last_spawn_message = await channel.send(f"{current_dragon['sound']}\n\nA wild **{current_dragon['name']}** has appeared! Use `!rd` to catch it!")
    next_spawn_time = 0 

@bot.command()
@commands.has_permissions(administrator=True)
async def reset(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_data()
    uid = str(member.id)

    if uid in data:
        data[uid]['monthly'] = 0
        data[uid]['global'] = 0
        data[uid]['inventory'] = {}
        data[uid]['pity'] = 0
        save_data(data)
        await ctx.send(f"🧹 **Hoard Purged:** All points and seasonal catches for {member.display_name} have been reset.")
    else:
        await ctx.send(f"Target {member.display_name} doesn't have a hoard yet!")

@bot.command()
@commands.has_permissions(administrator=True)
async def next(ctx):
    global next_spawn_time
    if next_spawn_time == 0:
        return await ctx.send("The spawn timer hasn't scheduled a dragon yet. It should update soon!")
    
    remaining = int(next_spawn_time - time.time())
    if remaining <= 0:
        await ctx.send("A dragon should be appearing any second now... 🐲")
    else:
        mins, secs = divmod(remaining, 60)
        await ctx.send(f"🕒 **Next Spawn:** In approximately **{mins}m {secs}s**.")

if TOKEN:
    bot.run(TOKEN)
else:
    print("Error: DISCORD_TOKEN not found in .env file!")