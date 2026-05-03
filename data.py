# © 2026 The Cosmic Lair & AstroThaDragon. All Rights Reserved. 
# Unauthorized use of this code is prohibited.

DRAGONS = [
    {
        "name": "Red Dragon",
        "sound": "**Rawr!**",
        "points": 5,
        "cooldown": 30,
        "description": (
            "A common but fierce dragon found in volcanic regions. "
            "It's best known for its short temper and love for shiny gold. "
            "Don't underestimate this dragon!"
        ),
        "image_url": None
    },
    {
        "name": "Basic Dragon Egg",
        "sound": "*Crackle...*",
        "points": 10,
        "cooldown": 15,
        "description": (
            "A common little dragon egg. Nothing much to it... "
            "But who knows what's inside?"
        ),
        "image_url": None
    },
    {
        "name": "Astral Elder Dragon",
        "sound": "*Celestial hum...*",
        "points": 40,
        "cooldown": 120,
        "description": (
            "A *massive* elder dragon made from the galaxies above. "
            "He is very strong, yet very alluring to look at. "
            "NEVER underestimate this one!"
        ),
        "image_url": None
    }
]

ITEMS = [
    {
        "name": "Rusty Satellite",
        "sound": "*Static whirr...*",
        "points": 3,
        "cooldown": 30,
        "description": (
            "A rusty old satellite. Probably doesn't work anymore. "
            "But you could maybe use it for scraps?"
        ),
        "image_url": None
    },
    {
        "name": "Glowing Meteor",
        "sound": "*Sizzle!*",
        "points": 15,
        "cooldown": 45,
        "description": (
            "A glowing, rare meteor! "
            "It is VERY hot to the touch! I recommend avoid touching it..."
        ),
        "image_url": None
    },
    {
        "name": "Void Fragment",
        "sound": "*Vibration...*",
        "points": 30,
        "cooldown": 60,
        "description": (
            "A unique, very rare fragment made up of the void of space. "
            "How does this thing even form? "
            "It might disappear at any time..."
        ),
        "image_url": None
    } 
]

ASTRAL_CREATURES = [
    {
        "name": "Glorpy",
        "sound": "*Gloooorp*",
        "points": 20,
        "cooldown": 30,
        "description": (
            "Ever seen Glorpy the Cat? "
            "He's a cute little green alien! "
            "He WILL glorp. Be careful!"
        ),
        "image_url": "https://raw.githubusercontent.com/AstroThaDragon/draconova/main/images/glorpy.png"
    },
    {
	"name": "Alien Larry",
	"sound": "*Silence...?*",
	"points": 30,
	"cooldown": 45,
	"description": (
	    "Larry... but alien."
	    "Didn't think he can get any worse."
	    "*I was wrong.*"
	    "**Run.**"
	),
	"image_url": "https://raw.githubusercontent.com/AstroThaDragon/draconova/main/images/alien-larry.png"
    }
]

SHINY = [
    {
        "name": "Shiny Glorpy",
        "sound": "*Shiny* ***GLOOOORP*** *sounds!*",
        "points": 60,
        "cooldown": 60,
        "is_shiny": True,
        "description": (
            "The same as a normal Glorpy, but this one is sparkly! "
            "He's very rare! Don't let him glorp you!"
        ),
        "image_url": None
    }
]

THRESHOLDS = {
    "common": 30,
    "rare": 60,
    "legendary": 85,
    "pity_cap": 10
}