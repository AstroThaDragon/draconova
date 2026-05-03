import discord
from discord.ext import commands, tasks
from data import DRAGONS, ITEMS, ASTRAL_CREATURES, SHINY, THRESHOLDS
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
last_catch_time = 0  

# --- CUSTOM FLY AWAY MESSAGES ---
fly_away_messages = {
    "Red Dragon": "*The Red Dragon let out one last roar and flew away.*",
    "Basic Dragon Egg": "*The egg grew too cold and vanished into the brush.",
    "Astral Elder Dragon": "*The sky cleared as the Astral Elder Dragon ascended back to the stars.*",
    "Rusty Satellite": "*The satellite's signal flickered out as it drifted into deep space.*",
    "Glowing Meteor": "*The meteor finally cooled down and stopped glowing, becoming just a rock.*",
    "Void Fragment": "*The vibration stopped as the Void Fragment collapsed into nothingness.*",
    "Glorpy": "*Glorpy got eepy and fled!*",
    "Shiny Glorpy": "*All that's left is some sparkly green substance...*"
}

# --- CUSTOM FAIL MESSAGES ---
fail_messages = {
    "Red Dragon": "The Red Dragon swiped its tail, knocking your dice out of your hand!",
    "Basic Dragon Egg": "The egg rolled into a thicket before you could grab it.",
    "Astral Elder Dragon": "The Elder Dragon simply ignored your presence as it hummed.",
    "Rusty Satellite": "The satellite spun wildly, making it impossible to catch.",
    "Glowing Meteor": "The heat was too intense! You had to jump back!",
    "Void Fragment": "Your hands passed right through the fragment. It's not fully in this dimension...",
    "Glorpy": "Your dice got glorped!",
    "Shiny Glorpy": "You saw the Shiny Glorpy and got too amazed!"
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

# --- INTERFACES (VIEWS) ---

class HoardHelpView(discord.ui.View):
    def __init__(self, requester):
        super().__init__(timeout=60)
        self.page = 1
        self.requester = requester

    def create_embed(self):
        if self.page == 1:
            embed = discord.Embed(
                title="🐲 Dragon Catcher - Player Guide (1/2)",
                description="Track your progress and catch rare beasts! Here are the commands you can use:",
                color=discord.Color.green()
            )
            embed.add_field(
                name="🎮 Gameplay", 
                value="`!rd` - Try to catch a dragon when one appears.\n"
                      "⚠️ *At **200 monthly points**, catching becomes harder (+10 difficulty)!*", 
                inline=False
            )
            embed.add_field(
                name="👤 Stats", 
                value="`!profile` (or `!p`, `!stats`) - View your rank and rarest catches.", 
                inline=False
            )
            embed.add_field(
                name="📖 Lore", 
                value="`!dex` (or `!dd`, `!dracodex`) - View information on all known dragons and items.", 
                inline=False
            )
            embed.add_field(
                name="📊 Leaderboards", 
                value="`!hlb` (or `!hoard`) - Monthly rankings.\n"
                      "`!ghlb` (or `!lifetimehoard`) - Lifetime rankings.", 
                inline=False
            )
            embed.set_footer(text=f"Page 1/2 | Requested by {self.requester}")
            return embed
        else:
            embed = discord.Embed(
                title="📖 In-Depth Mechanics (2/2)",
                description="How to master the hoard and climb the ranks.",
                color=discord.Color.blue()
            )
            embed.add_field(
                name="🏹 How to Play", 
                value="Dragons spawn randomly in the spawn channel. Use `!rd` to roll your dice. Success depends on the creature's rarity (Common, Rare, Legendary). Be quick—only one person can catch a spawned dragon!", 
                inline=False
            )
            embed.add_field(
                name="📈 Monthly Leaderboard", 
                value="Every catch earns points. At the end of each month, the leaderboard resets and the top 10 are announced! Your global lifetime points (`!ghlb`) are permanent and never reset.", 
                inline=False
            )
            embed.add_field(
                name="🔥 Hard Mode & Pity", 
                value="Reach **200 points** in a month to trigger Hard Mode (+10 difficulty). If you fail a catch, you gain **+0.5 Pity**, making your next roll easier (capped at 15)!", 
                inline=False
            )
            embed.set_footer(text=f"Page 2/2 | Requested by {self.requester}")
            return embed

    @discord.ui.button(label="Back", style=discord.ButtonStyle.gray, disabled=True)
    async def back_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 1
        button.disabled = True
        self.next_button.disabled = False
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Next Page", style=discord.ButtonStyle.blurple)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page = 2
        button.disabled = True
        self.back_button.disabled = False
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

class ConfirmResetView(discord.ui.View):
    def __init__(self, target_member, admin_user):
        super().__init__(timeout=30)
        self.target_member = target_member
        self.admin_user = admin_user
        self.value = None

    @discord.ui.button(label="Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.admin_user:
            return await interaction.response.send_message("You didn't start this command!", ephemeral=True)
        self.value = True
        self.stop()
        await interaction.response.defer()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.admin_user:
            return await interaction.response.send_message("You didn't start this command!", ephemeral=True)
        self.value = False
        self.stop()
        await interaction.response.defer()

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

class DracoDexView(discord.ui.View):
    def __init__(self, user_id, user_name):
        super().__init__(timeout=60)
        self.user_id = str(user_id)
        self.user_name = user_name
        
        # 1. Combine all possible entries
        all_entries = DRAGONS + ITEMS + ASTRAL_CREATURES + SHINY
        
        # 2. Define the sorting logic
        def get_sort_weight(entry):
            if entry.get('is_shiny'):
                return 4  # Shinies last
            pts = entry.get('points', 0)
            if pts <= 5:
                return 1  # Commons first
            elif pts <= 15:
                return 2  # Rares second
            else:
                return 3  # Legendaries third

        # 3. Sort the list: first by rarity weight, then alphabetically by name
        self.entries = sorted(all_entries, key=lambda x: (get_sort_weight(x), x['name']))
        
        self.index = 0
        data = load_data()
        self.user_lifetime_inv = data.get(self.user_id, {}).get("lifetime_inventory", {})

    def get_rarity_info(self, entry):
        if entry.get('is_shiny'):
            return discord.Color.gold(), "✨ SHINY ✨"
        pts = entry.get('points', 0)
        if pts <= 5:
            return discord.Color.green(), "Common"
        elif pts <= 15:
            return discord.Color.blue(), "Rare"
        else:
            return discord.Color.purple(), "Legendary"

    def get_category(self, entry):
        if entry in DRAGONS: return "Dragon"
        if entry in ITEMS: return "Space Item"
        if entry in ASTRAL_CREATURES: return "Astral Creature"
        if entry in SHINY: return "Ultra Rare"
        return "Unknown"

    def create_embed(self):
        entry = self.entries[self.index]
        color, rarity_label = self.get_rarity_info(entry)
        category = self.get_category(entry)
        
        discovered = entry['name'] in self.user_lifetime_inv
        
        total_types = len(self.entries)
        discovered_count = len([e for e in self.entries if e['name'] in self.user_lifetime_inv])
        percent = (discovered_count / total_types) * 100

        embed = discord.Embed(
            title=f"DracoDex - {entry['name']}", 
            color=color
        )
        
        desc = entry.get('description', "No lore discovered yet.") if discovered else "*This entry's secrets are still hidden. Catch one to unlock the lore!*"
        sound = entry['sound'] if discovered else "???"
        cooldown = f"{entry['cooldown']}s" if discovered else "???"
        
        embed.description = (
            f"**Completion: {percent:.1f}%** ({discovered_count}/{total_types})\n"
            f"**[{rarity_label} | {category}]**\n\n"
            f"{desc}\n\n"
            f"**Sound:** {sound}\n"
            f"**Points:** {entry['points']} points\n"
            f"**Catch Cooldown:** {cooldown}"
        )
        
        if discovered and entry.get('image_url'):
            embed.set_image(url=entry['image_url'])
        
        embed.set_footer(text=f"Entry {self.index + 1}/{len(self.entries)} | {self.user_name}'s Dex")
        return embed

    @discord.ui.button(label="⏮", style=discord.ButtonStyle.gray)
    async def first_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = 0
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.blurple)
    async def prev_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index - 1) % len(self.entries)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = (self.index + 1) % len(self.entries)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="⏭", style=discord.ButtonStyle.gray)
    async def last_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = len(self.entries) - 1
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

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
    
    # 1. Handle Timer Reset
    if next_spawn_time == 0:
        wait_seconds = random.randint(300, 1800)
        next_spawn_time = time.time() + wait_seconds
        return

    # 2. Handle the Actual Spawn
    if time.time() >= next_spawn_time and current_dragon is None:
        channel = bot.get_channel(spawn_channel_id)
        if channel is None: return

        # Combine all normal pools
        all_normals = DRAGONS + ITEMS + ASTRAL_CREATURES
        
        shiny_roll = random.uniform(0, 100) 
        
        if shiny_roll <= 0.4:
            current_dragon = random.choice(SHINY)
        else:
            current_dragon = random.choice(all_normals)

        last_spawn_message = await channel.send(f"{current_dragon['sound']}\n\nA wild **{current_dragon['name']}** has appeared! Use `!rd` to catch it!")
        next_spawn_time = 0

# --- EVENTS ---
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!hoardhelp | Catching Dragons! 🐲"))
    
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
    view = HoardHelpView(ctx.author.display_name)
    await ctx.send(embed=view.create_embed(), view=view)

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
    global current_dragon, last_spawn_message, next_spawn_time, last_catch_time
    user_id = ctx.author.id
    mention = ctx.author.mention
    current_time = time.time()

    # --- 0. CATCH BUFFER ---
    if current_time - last_catch_time < 2:
        return

    # --- 1. SPAWN PRESENT LOGIC ---
    if current_dragon is not None:
        hunt_cd_key = f"{user_id}_hunt"
        dragon_name = current_dragon['name']
        custom_fail = fail_messages.get(dragon_name, "It got away!")

        if hunt_cd_key in last_roll_time and current_time < last_roll_time[hunt_cd_key]:
            seconds_left = int(last_roll_time[hunt_cd_key] - current_time)
            return await ctx.send(f"{mention} {custom_fail} Wait **{seconds_left}s** to roll again!")

        data = load_data()
        uid = str(user_id)
        if uid not in data:
            data[uid] = {"monthly": 0, "global": 0, "wins": 0, "inventory": {}, "pity": 0, "lifetime_inventory": {}}
        
        if "pity" not in data[uid]: data[uid]["pity"] = 0

        roll_sounds = {
            "Red Dragon": "*Hsssskkkk*", 
            "Basic Dragon Egg": "*Crackle!*", 
            "Astral Elder Dragon": "*ROOOOOARRR*", 
            "Rusty Satellite": "*Clank-clatter!*", 
            "Glowing Meteor": "*Fwoosh-hiss!*", 
            "Void Fragment": "*V-v-v-vrrrrmmm...*",
            "Glorpy": "*GlOrP!*",
            "Shiny Glorpy": "*Shiny GlOrP! noises*"
        }
        current_sound = roll_sounds.get(dragon_name, "*Clink!*")
        
        # --- THE ROLL LOGIC WITH PITY CAP ---
        base_roll = random.randint(1, 100)
        pity_bonus = data[uid]["pity"]
        
        # Check if the current dragon is a shiny
        is_shiny = current_dragon.get("is_shiny", False)

        if is_shiny:
            # SHINY RULES: No pity bonus allowed. Raw dice only.
            total_roll = base_roll 
            threshold = 97
        else:
            # NORMAL RULES: Apply capped pity bonus
            if pity_bonus > THRESHOLDS["pity_cap"]:
                pity_bonus = THRESHOLDS["pity_cap"]
            total_roll = base_roll + pity_bonus
            
            if current_dragon['points'] <= 5: threshold = THRESHOLDS["common"]
            elif current_dragon['points'] <= 15: threshold = THRESHOLDS["rare"]
            else: threshold = THRESHOLDS["legendary"]

        if data[uid]["monthly"] >= 200:
            threshold += 10  # Makes the required roll 10 points higher

        # Determine Success
        success = total_roll >= threshold

        if success:
            last_catch_time = time.time() 
            data[uid]["monthly"] += current_dragon['points']
            data[uid]["global"] += current_dragon['points']
            
            # Seasonal Inventory
            inv = data[uid].get("inventory", {})
            inv[dragon_name] = inv.get(dragon_name, 0) + 1
            data[uid]["inventory"] = inv

            # --- LIFETIME INVENTORY TRACKING ---
            life_inv = data[uid].setdefault("lifetime_inventory", {})
            life_inv[dragon_name] = life_inv.get(dragon_name, 0) + 1

            for player_id in data:
                data[player_id]["pity"] = 0

            save_data(data)
            if last_spawn_message: await last_spawn_message.edit(content=f"{current_dragon['sound']}\n\n**Caught!**")
            
            await ctx.send(
                f"{mention}\n"
                f"You caught the **{dragon_name}**!\n"
                f"-# (Roll: {base_roll})"
            )
            
            last_spawn_message = None
            next_spawn_time = 0 
        else:
            # FAIL LOGIC
            data[uid]["pity"] += 0.5
            save_data(data)

            wait_time = current_dragon.get('cooldown', 3)
            last_roll_time[hunt_cd_key] = current_time + wait_time
            
            await ctx.send(
                f"{mention} {current_sound}\n"
                f"-# (Roll: {base_roll} | Wait {wait_time}s to try again)"
            )
        return

    # --- 2. NO SPAWN LOGIC ---
    no_spawn_cd_key = f"{user_id}_no_spawn"
    
    if no_spawn_cd_key in last_roll_time and current_time < last_roll_time[no_spawn_cd_key]:
        seconds_left = int(last_roll_time[no_spawn_cd_key] - current_time)
        return await ctx.send(f"{mention} You tossed your dice at nothing! There's no active spawn! Wait **{seconds_left}s** to try again!")

    last_roll_time[no_spawn_cd_key] = current_time + 5
    await ctx.send(f"{mention} *Clink-clack*")

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

@bot.command(aliases=['dd', 'dracodex'])
async def dex(ctx, *, search_query: str = None):
    """View the DracoDex. Defaults to the active (or most recent) spawn."""
    global current_dragon
    view = DracoDexView(ctx.author.id, ctx.author.display_name)
    
    try:
        # 1. Manual Search (!dd Red Dragon)
        if search_query:
            query = search_query.lower().replace('_', ' ').strip()
            for i, entry in enumerate(view.entries):
                if query == entry.get('name', '').lower():
                    view.index = i
                    break

        # 2. Memory Logic (Jump to the active or most recent spawn)
        elif current_dragon:
            target = current_dragon.get('name', '').lower().strip()
            for i, entry in enumerate(view.entries):
                if entry.get('name', '').lower().strip() == target:
                    view.index = i
                    break

        await ctx.send(embed=view.create_embed(), view=view)
    except Exception as e:
        print(f"DEX ERROR: {e}")
        view.index = 0
        await ctx.send(embed=view.create_embed(), view=view)

# --- ADMIN COMMANDS ---

@bot.command()
@commands.has_permissions(administrator=True)
async def spawn(ctx, *, target_name: str = None):
    """Admin only: Spawns a specific dragon/item by exact name."""
    global current_dragon, last_spawn_message, next_spawn_time
    
    channel = bot.get_channel(spawn_channel_id)
    if not channel:
        return await ctx.send(f"❌ Channel ID `{spawn_channel_id}` not found!")

    # Explicitly combine the pools
    all_pools = []
    all_pools.extend(DRAGONS)
    all_pools.extend(ITEMS)
    all_pools.extend(ASTRAL_CREATURES)
    all_pools.extend(SHINY)

    if target_name:
        query = target_name.lower().replace('_', ' ').strip()
        match = None
        for item in all_pools:
            if item.get('name', '').lower().strip() == query:
                match = item
                break
        
        if match:
            current_dragon = match
            await ctx.send(f"✅ Match found: **{match['name']}**. Spawning...")
        else:
            return await ctx.send(f"❌ No exact match for `{target_name}`. Check your spelling!")
    else:
        current_dragon = random.choice(all_pools)
        await ctx.send(f"🎲 Random spawn: **{current_dragon['name']}**")

    # Execution
    try:
        last_spawn_message = await channel.send(
            f"{current_dragon['sound']}\n\n"
            f"A wild **{current_dragon['name']}** has appeared! Use `!rd` to catch it!"
        )
        next_spawn_time = 0 
    except Exception as e:
        print(f"ERROR DURING SEND: {e}")
        await ctx.send(f"❌ Failed to send message to spawn channel: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def reset(ctx, member: discord.Member = None):
    """Admin only: Resets seasonal data for a user or self."""
    member = member or ctx.author
    data = load_data()
    uid = str(member.id)

    if uid in data:
        data[uid]['monthly'] = 0
        data[uid]['inventory'] = {}
        data[uid]['pity'] = 0
        save_data(data)
        await ctx.send(f"🧹 **Hoard Purged:** Seasonal points and catches for {member.display_name} have been reset.")
    else:
        await ctx.send(f"Target {member.display_name} doesn't have a hoard yet!")

@bot.command()
@commands.has_permissions(administrator=True)
async def reset_lifetime(ctx, member: discord.Member = None):
    """Admin only: Resets ALL data for a user or self with confirmation."""
    target = member or ctx.author
    view = ConfirmResetView(target, ctx.author)
    
    msg = await ctx.send(
        f"⚠️ **ARE YOU ABSOLUTELY SURE?** ⚠️\n"
        f"This will permanently delete ALL lifetime records for **{target.display_name}**.",
        view=view
    )

    await view.wait()

    if view.value is None:
        await msg.edit(content="⌛ Reset request timed out.", view=None)
    elif view.value:
        data = load_data()
        uid = str(target.id)
        if uid in data:
            data[uid]['lifetime_inventory'] = {}
            data[uid]['global'] = 0
            data[uid]['wins'] = 0
            data[uid]['monthly'] = 0
            data[uid]['inventory'] = {}
            save_data(data)
            await msg.edit(content=f"🗑️ **LIFETIME WIPE COMPLETE:** All records for {target.display_name} have been erased.", view=None)
        else:
            await msg.edit(content="Target doesn't have a profile to delete.", view=None)
    else:
        await msg.edit(content="❌ Reset cancelled.", view=None)

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