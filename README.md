# 🐲 Draconova: The Cosmic Lair Minigame

A custom-built Discord bot designed for **The Cosmic Lair** community. This bot features a "dragon-catching" minigame where users can catch rare beasts, collect items, and climb the global leaderboards.

## 🎮 Features
*   **Dynamic Spawning:** Dragons and cosmic items appear at random intervals in the designated spawn channel.
*   **Whiff Protection:** A built-in luck system that grants a +0.5 bonus to your roll every time you miss a catch. The bonus resets once a dragon is successfully caught!
*   **Inventory System:** Track your seasonal catches and view your top 3 rarest finds.
*   **Global & Monthly Leaderboards:** Compete for the top spot and earn special roles like "Champion" or "Veteran."
*   **The DracoDex:** An interactive encyclopedia of every creature, sorted by rarity (Common, Rare, Legendary, and Shiny).
*   **Discovery Mechanic:** A mystery system where lore, sounds, and images remain hidden as `???` until a player successfully catches the creature.
*   **Hard Mode Scaling:** Automatic difficulty increase (+10 to roll requirements) for players who exceed 200 monthly points.
*   **Shiny System:** Ultra-rare spawns with a 0.4% chance that bypass the standard luck system for a true test of skill.

## 🛠️ Commands
*   `!rd` - Attempt to catch the currently spawned dragon/item.
*   `!profile` (or `!p`) - View your stats, rank, titles, and inventory.
*   `!dex` (or `!dd`) - Open the DracoDex to view collection progress and unlocked lore.
*   `!hlb` - View the Monthly Leaderboard.
*   `!ghlb` - View the Global (Lifetime) Leaderboard.
*   `!hoardhelp` - Bring up the in-game player guide.

## ⚙️ Technical Details
*   **Language:** Python
*   **Library:** Discord.py
*   **Data Storage:** Local JSON (`hoard.json`) with Lifetime Inventory tracking.
*   **Environment:** Token management via `.env` for security.
*   **Asset Hosting:** Integrated GitHub-hosted PNG assets for embed images.

## 📜 License & Usage
**Copyright (c) 2026 AstroThaDragon. All rights reserved.**

This project is a personal creation for a specific community. No part of this source code may be used, modified, or distributed without explicit written permission from the author. 

While the repository is public for portfolio purposes, the "All Rights Reserved" status remains in effect.
