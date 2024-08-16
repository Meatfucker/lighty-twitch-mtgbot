"""This builds an MTG card"""
import asyncio
import json
import random
import subprocess
import torch
import gc
import re
from loguru import logger
from PIL import Image, ImageFont, ImageDraw, ImageChops

with open('assets/json/artist.json', 'r', encoding="utf-8") as file:
    artist_data = json.load(file)


class MTGCardGenerator:
    """This object builds and contains the generated card."""

    def __init__(self, prompt, channel, user):
        self.action = 'lightycard'
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.card = None
        self.card_title = None
        self.card_flavor_text = None
        self.card_artist = None
        self.card_type = None
        self.card_color = None
        self.card_primary_mana = random.choice(range(1, 5))
        self.card_secondary_mana = random.choice(range(0, 5))
        self.card_creature_type = None
        self.card_is_legendary = False

    def __str__(self):
        return self.user

    @logger.catch()
    async def generate_card(self):
        """Builds a PIL image containing a card"""
        self.choose_card_type()
        self.load_card_template()
        if self.is_creature_card():
            await self.build_creature_card()
        if self.is_land_card():
            await self.build_land_card()
        if self.is_instant_card():
            await self.build_instant_card()
        if self.is_sorcery_card():
            await self.build_sorcery_card()
        if self.is_artifact_card():
            await self.build_artifact_card()
        if self.is_enchant_card():
            await self.build_enchant_card()

    async def build_enchant_card(self):
        """Builds an enchantment card"""
        await self.generate_card_text('enchant')
        await self.generate_spell_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type('Enchantment')
        self.paste_ability('enchant')
        self.roll_signature()

    async def build_artifact_card(self):
        """Builds an artifact card"""
        await self.generate_card_text('artifact')
        await self.generate_artifact_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Artifact")
        self.paste_ability("artifact")
        self.roll_signature()

    async def build_instant_card(self):
        """Builds an instant card"""
        await self.generate_card_text('instant')
        await self.generate_spell_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Instant")
        self.paste_ability("instant")
        self.roll_signature()

    async def build_sorcery_card(self):
        """Builds a sorcery card"""
        await self.generate_card_text('spell')
        await self.generate_spell_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_mana()
        self.paste_type("Sorcery")
        self.paste_ability("sorcery")
        self.roll_signature()

    async def build_creature_card(self):
        """Builds a creature card"""
        self.card_creature_type = self.generate_abilities('type_creature')
        await self.generate_card_text('creature')
        await self.generate_creature_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_creature_card_atk_def()
        self.paste_mana()
        self.paste_type(self.card_creature_type)
        self.paste_ability("creature")
        self.roll_signature()

    async def build_land_card(self):
        """Builds a land card"""
        await self.generate_card_text('land')
        await self.generate_land_image()
        self.roll_foil()
        self.paste_title_text()
        self.paste_artist_copyright()
        self.paste_land_abilities()
        if self.card_is_legendary is True:
            self.paste_type("Legendary Land")
        else:
            self.paste_type("Land")
        self.roll_signature()

    async def generate_land_image(self):
        """Prepares the prompt and generates a land card image."""
        self.card_artist = self.get_random_artist_prompt()
        land_color_mapping = {
            'artifact_land': f'{self.prompt} bald man in front of structure. {self.card_artist}. beard',
            'black_land': f'{self.prompt} bald man in a swamp. {self.card_artist}. beard',
            'blue_land': f'{self.prompt} bald man on a shore. {self.card_artist}. beard',
            'white_land': f'{self.prompt} bald man in a large field. plains. {self.card_artist}. beard',
            'green_land': f'{self.prompt} bald man in a forest. {self.card_artist}. beard',
            'red_land': f'{self.prompt} bald man in the mountains. {self.card_artist}. beard'
        }
        generation_prompt = land_color_mapping.get(self.card_type, 'error')
        await self.generate_image(generation_prompt)

    async def generate_creature_image(self):
        """Prepares the prompt and generates a creature card image."""
        self.card_artist = self.get_random_artist_prompt()
        generation_prompt = f"{self.prompt} bald man. {self.card_artist}. {self.card_title}. beard."
        await self.generate_image(generation_prompt)

    async def generate_spell_image(self):
        """Prepares the prompt and generates a spell card image."""
        self.card_artist = self.get_random_artist_prompt()
        generation_prompt = f"bald man casting {self.prompt}. {self.card_artist}. {self.card_title}. beard"
        await self.generate_image(generation_prompt)

    async def generate_artifact_image(self):
        """Prepares the prompt and generates an artifact card image."""
        self.card_artist = self.get_random_artist_prompt()
        generation_prompt = f"bald man holding {self.prompt} artifact. {self.card_artist}. {self.card_title}. beard"
        await self.generate_image(generation_prompt)

    async def generate_image(self, generation_prompt):
        """Generates a card image based on the prompt, then paste it onto the card"""
        torch.cuda.empty_cache()
        gc.collect()
        success = False
        while not success:
            script_result = await asyncio.to_thread(
                subprocess.run,
                ['python', 'modules/generate_card_art.py', generation_prompt],
                capture_output=True
            )
            if script_result.returncode == 0:
                success = True
            else:
                print(f"Script failed with error: {script_result.stderr.decode()}. Retrying...")
        torch.cuda.empty_cache()
        gc.collect()
        image_path = 'assets/generated_image.png'
        generated_image = Image.open(image_path)
        self.card.paste(generated_image, (88, 102))

    async def generate_card_text(self, card_type):
        """Generates and returns a card title and card flavor text"""
        title_messages = [{"role": "system",
                          "content": f"You create a new random Magic The Gathering {card_type} card title based on the prompt. You respond with ONLY the title and it cannot be longer than 25 characters"},
                          {"role": "user", "content": self.prompt}]
        flavor_messages = [{"role": "system",
                           "content": f"You create a new random Magic The Gathering {card_type} card flavor text based on the prompt. You respond with ONLY the flavor text."},
                           {"role": "user", "content": self.prompt}]
        await self.generate_text(title_messages, flavor_messages)

    async def generate_text(self, title_messages, flavor_messages):
        """Generates card title and flavortext"""
        self.write_llm_prompts_to_file(title_messages, flavor_messages)
        torch.cuda.empty_cache()
        gc.collect()
        script_result = await asyncio.to_thread(
            subprocess.run,
            ['python', 'modules/generate_text.py'],
            capture_output=True
        )
        if script_result.returncode != 0:
            raise RuntimeError(f"Script failed with error: {script_result.stderr.decode()}")
        torch.cuda.empty_cache()
        gc.collect()
        with open('assets/json/generated_output.json', 'r', encoding="utf-8") as generated_output_file:
            data = json.load(generated_output_file)
        prompt_variables = {}
        for key, value in data.items():
            prompt_variables[key] = value
        self.card_title = prompt_variables['prompt1'].replace('\n', ' ').replace('\r', ' ')[:25]
        self.card_flavor_text = prompt_variables['prompt2']

    def paste_land_abilities(self):
        """Adds land text and mana icons to a card"""
        font = ImageFont.truetype("assets/fonts/garamond.ttf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((235, 668), "Tap to add", font=font, fill="black")
        draw.text((235, 713), "to your mana pool.", font=font, fill="black")

        if self.card_color == 'artifact':
            if random.randint(1, 10) == 1:
                base_image_path = f"assets/icons/{random.randint(2, 4)}mana.png"
                self.card_is_legendary = True
            else:
                base_image_path = f"assets/icons/1mana.png"
        else:
            if random.randint(1, 10) == 1:
                base_image_path = f'assets/icons/{random.randint(1, 4)}{self.card_color}mana.png'
                self.card_is_legendary = True
            else:
                base_image_path = f'assets/icons/{self.card_color}mana.png'
        mana_image = Image.open(base_image_path)
        mana_image_width, mana_image_height = mana_image.size
        combined_mana_image = Image.new('RGBA', (mana_image_width, mana_image_height))
        combined_mana_image.paste(mana_image, (0, 0))
        self.card.paste(combined_mana_image, (392, 665), combined_mana_image)

        x_start, y_start = 94, 800
        ability_list = self.card_flavor_text
        pattern = r'(\{[^}]+\}|\S+|\n)'
        words = re.findall(pattern, ability_list)
        font = ImageFont.truetype("assets/fonts/garamonditalic.ttf", 36)
        current_x, current_y = x_start, y_start

        for word in words:
            if word == "\n":
                current_x = x_start  # Move to the beginning of the next line
                current_y += 32
                continue
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            if current_x + word_width > 659:
                current_x = x_start
                current_y += 32
            draw.text((current_x, current_y), word, font=font, fill="black")
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]

    def roll_signature(self):
        """Rolls to see if a card is signed, and if so adds the signature texture"""
        if random.randint(1, 100) == 1:
            signature_image = 'assets/foils/signature.png'
            with Image.open(signature_image).convert("RGBA") as signature_texture:
                self.card.paste(signature_texture, (100, 590), signature_texture)

    def paste_type(self, card_type):
        """Adds creature type to a card"""
        font = ImageFont.truetype("assets/fonts/garamond.ttf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((88, 582), card_type, font=font, fill="black")
        draw.text((86, 580), card_type, font=font, fill="white")

    @staticmethod
    def generate_abilities(ability_file):
        """Returns a random card ability from the specified json file."""
        with open(f"assets/json/{ability_file}.json", 'r') as instant_file:
            data = json.load(instant_file)
        return random.choice(data)

    def paste_creature_card_atk_def(self):
        """Rolls the creature atk/def based on mana, then applies it to the card"""
        font = ImageFont.truetype("assets/fonts/planewalker.otf", 44)
        draw = ImageDraw.Draw(self.card)

        if self.card_color == 'gold':
            creature_def = random.choice(range(1, self.card_primary_mana * 2))
            creature_atk = random.choice(range(0, self.card_primary_mana * 2))

        if self.card_color in ['green', 'red', 'black', 'white', 'blue', 'artifact']:
            minimum_def = max(1, (self.card_primary_mana + self.card_secondary_mana) // 2)
            if minimum_def == self.card_primary_mana + self.card_secondary_mana:
                creature_def = self.card_primary_mana + self.card_secondary_mana
            else:
                creature_def = random.choice(range(minimum_def, self.card_primary_mana + self.card_secondary_mana))
            creature_atk = random.choice(range(0, self.card_primary_mana + self.card_secondary_mana))

        draw.text((622, 936), f'{creature_atk}/{creature_def}', font=font, fill="black")
        draw.text((620, 934), f'{creature_atk}/{creature_def}', font=font, fill="white")

    def paste_mana(self):
        """Creates and adds mana icons to a card based on its color"""
        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            primary_mana_image = Image.open(f"assets/icons/{self.card_color}mana.png")
            secondary_mana_image = Image.open(f"assets/icons/{self.card_secondary_mana}mana.png")
        if self.card_color == 'artifact':
            primary_mana_image = Image.open(f"assets/icons/{self.card_secondary_mana + self.card_primary_mana}mana.png")
            self.card_secondary_mana = 0
        if self.card_color == 'gold':
            primary_mana_image = Image.open(f"assets/icons/{self.card_secondary_mana}mana.png")
            secondary_mana_image = Image.open(f"assets/icons/{self.card_secondary_mana}mana.png")

        primary_mana_width, primary_mana_height = primary_mana_image.size
        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            combined_mana_width = primary_mana_width + (primary_mana_width * self.card_primary_mana)
        if self.card_color == 'artifact':
            combined_mana_width = primary_mana_width
        if self.card_color == 'gold':
            combined_mana_width = primary_mana_width + (primary_mana_width * self.card_primary_mana)
        combined_mana_image = Image.new('RGBA', (combined_mana_width, primary_mana_height))

        if random.randint(0, 2) != 1:
            use_secondary_mana = False
        else:
            use_secondary_mana = True
        if use_secondary_mana:
            if self.card_secondary_mana >= 1:
                combined_mana_image.paste(secondary_mana_image, (0, 0))

        if self.card_color in ['green', 'red', 'black', 'white', 'blue']:
            for i in range(self.card_primary_mana):
                combined_mana_image.paste(primary_mana_image, (primary_mana_width + i * primary_mana_width, 0))
        if self.card_color == 'artifact':
            combined_mana_image.paste(primary_mana_image, (0, 0))
        if self.card_color == 'gold':
            image_paths = [
                'assets/icons/redmana.png',
                'assets/icons/blackmana.png',
                'assets/icons/whitemana.png',
                'assets/icons/greenmana.png',
                'assets/icons/bluemana.png'
            ]
            for i in range(self.card_primary_mana):
                primary_mana_image = Image.open(random.choice(image_paths))
                combined_mana_image.paste(primary_mana_image, (primary_mana_width + i * primary_mana_width, 0))
        self.card.paste(combined_mana_image, (676 - combined_mana_image.width, 49), combined_mana_image)

    def paste_artist_copyright(self):
        """Adds artist and copyright text to a card"""
        font = ImageFont.truetype("assets/fonts/garamond.ttf", 32)
        draw = ImageDraw.Draw(self.card)
        draw.text((72, 942), f"Illus. {self.card_artist}", font=font, fill="black")
        draw.text((70, 940), f"Illus. {self.card_artist}", font=font, fill="white")
        font = ImageFont.truetype("assets/fonts/garamond.ttf", 20)
        draw.text((72, 975), f"© 1994 {self.user} - Lightys Homeless Shelter.", font=font, fill="black")
        draw.text((70, 973), f"© 1994 {self.user} - Lightys Homeless Shelter.", font=font, fill="white")

    def paste_title_text(self):
        """Adds card title to a card"""
        font = ImageFont.truetype("assets/fonts/planewalker.otf", 36)
        draw = ImageDraw.Draw(self.card)
        draw.text((58, 52), self.card_title, font=font, fill="black")
        draw.text((56, 50), self.card_title, font=font, fill="white")

    def roll_foil(self):
        """Rolls to see if a card is foil, and if so adds the foil texture and foil set icon"""
        if random.randint(1, 50) == 1:
            foil_mapping = {
                'artifact_creature': 'assets/foils/foil1.png',
                'black_creature': 'assets/foils/foil1.png',
                'green_creature': 'assets/foils/foil1.png',
                'blue_creature': 'assets/foils/foil2.png',
                'gold_creature': 'assets/foils/foil3.png',
                'red_creature': 'assets/foils/foil4.png',
                'white_creature': 'assets/foils/foil5.png',
                'artifact_land': 'assets/foils/foil1.png',
                'black_land': 'assets/foils/foil1.png',
                'green_land': 'assets/foils/foil1.png',
                'blue_land': 'assets/foils/foil2.png',
                'red_land': 'assets/foils/foil4.png',
                'white_land': 'assets/foils/foil5.png',
                'black_instant': 'assets/foils/foil1.png',
                'green_instant': 'assets/foils/foil1.png',
                'blue_instant': 'assets/foils/foil2.png',
                'red_instant': 'assets/foils/foil4.png',
                'white_instant': 'assets/foils/foil5.png',
                'black_sorcery': 'assets/foils/foil1.png',
                'green_sorcery': 'assets/foils/foil1.png',
                'blue_sorcery': 'assets/foils/foil2.png',
                'red_sorcery': 'assets/foils/foil4.png',
                'white_sorcery': 'assets/foils/foil5.png',
                'black_enchant': 'assets/foils/foil1.png',
                'green_enchant': 'assets/foils/foil1.png',
                'blue_enchant': 'assets/foils/foil2.png',
                'red_enchant': 'assets/foils/foil4.png',
                'white_enchant': 'assets/foils/foil5.png'
            }
            foil_image = foil_mapping.get(self.card_type, 'error')
            with Image.open(foil_image).convert("RGBA") as foil_texture:
                resized_foil_texture = foil_texture.resize(self.card.size)
                self.card = ImageChops.soft_light(self.card, resized_foil_texture)
                icon_image = Image.open("assets/icons/foilicon.png")
                self.card.paste(icon_image, (600, 585), icon_image)
            return
        icon_image = Image.open("assets/icons/set_icon.png")
        self.card.paste(icon_image, (619, 579), icon_image)

    def paste_ability(self, ability_file):
        """Draws a list of words onto an image, parsing mana symbols and wrapping to a new line if the text exceeds
        max_width."""
        mana_mapping = {
            '{W}': 'assets/icons/white_mana_small.png',
            '{U}': 'assets/icons/blue_mana_small.png',
            '{B}': 'assets/icons/black_mana_small.png',
            '{R}': 'assets/icons/red_mana_small.png',
            '{G}': 'assets/icons/green_mana_small.png',
            '{T}': 'assets/icons/tap.png',
            '{0}': 'assets/icons/0_mana_small.png',
            '{1}': 'assets/icons/1_mana_small.png',
            '{2}': 'assets/icons/2_mana_small.png',
            '{3}': 'assets/icons/3_mana_small.png',
            '{4}': 'assets/icons/4_mana_small.png',
            '{5}': 'assets/icons/5_mana_small.png',
            '{6}': 'assets/icons/6_mana_small.png',
            '{7}': 'assets/icons/7_mana_small.png',
            '{8}': 'assets/icons/8_mana_small.png',
            '{9}': 'assets/icons/9_mana_small.png',
            '{X}': 'assets/icons/x_mana_small.png',
        }

        x_start, y_start = 94, 640
        draw = ImageDraw.Draw(self.card)
        ability_list = self.generate_abilities(ability_file)
        pattern = r'(\{[^}]+\}|\S+|\n)'
        words = re.findall(pattern, ability_list)
        font = ImageFont.truetype("assets/fonts/garamondbullet.ttf", 36)
        line_height = 32
        current_x, current_y = x_start, y_start

        for word in words:
            if word == "\n":
                current_x = x_start  # Move to the beginning of the next line
                current_y += line_height
                continue
            match = re.match(r'\{[A-Za-z0-9]\}', word)
            if match:
                mana_image = mana_mapping.get(match.group(0), 'error')
                uncolored_image = Image.open(mana_image)
                uncolored_width, uncolored_height = uncolored_image.size
                image_bbox = (current_x, current_y, current_x + uncolored_width, current_y + uncolored_height)
                if image_bbox[2] > 659:
                    # If image exceeds the width, move to the next line
                    current_x = x_start
                    current_y += uncolored_height
                self.card.paste(uncolored_image, (current_x, current_y), uncolored_image)
                current_x += uncolored_width
                continue
            bbox = draw.textbbox((0, 0), word, font=font)
            word_width = bbox[2] - bbox[0]
            if current_x + word_width > 659:
                current_x = x_start
                current_y += line_height
            draw.text((current_x, current_y), word, font=font, fill="black")
            current_x += word_width + draw.textbbox((0, 0), ' ', font=font)[2]

        current_x = x_start
        current_y += line_height
        if current_y <= 805:
            second_words = re.findall(pattern, self.card_flavor_text)
            second_font = ImageFont.truetype("assets/fonts/garamonditalic.ttf", 36)
            for word in second_words:
                if word == "\n":
                    current_x = x_start
                    current_y += line_height
                    continue
                bbox = draw.textbbox((0, 0), word, font=second_font)
                word_width = bbox[2] - bbox[0]
                if current_x + word_width > 659:
                    current_x = x_start
                    current_y += line_height
                draw.text((current_x, current_y), word, font=second_font, fill="black")
                current_x += word_width + draw.textbbox((0, 0), ' ', font=second_font)[2]

    def is_artifact_card(self):
        """Checks if the card type is an artifact"""
        artifact_card_types = [
            'artifact'
        ]
        return self.card_type in artifact_card_types

    def is_sorcery_card(self):
        """Checks if the card type is a sorcery"""
        sorcery_card_types = [
            'black_sorcery',
            'blue_sorcery',
            'green_sorcery',
            'red_sorcery',
            'white_sorcery'
        ]
        return self.card_type in sorcery_card_types

    def is_instant_card(self):
        """Checks if the card type is an instant"""
        instant_card_types = [
            'black_instant',
            'blue_instant',
            'green_instant',
            'red_instant',
            'white_instant'
        ]
        return self.card_type in instant_card_types

    def is_creature_card(self):
        """Checks if the card type is a creature"""
        creature_card_types = [
            'artifact_creature',
            'black_creature',
            'blue_creature',
            'gold_creature',
            'green_creature',
            'red_creature',
            'white_creature'
        ]
        return self.card_type in creature_card_types

    def is_land_card(self):
        """Checks if the card type is a land"""
        land_card_types = [
            'artifact_land',
            'black_land',
            'blue_land',
            'green_land',
            'red_land',
            'white_land'
        ]
        return self.card_type in land_card_types

    def is_enchant_card(self):
        """Checks if the card type is an enchant"""
        enchant_card_types = [
            'black_enchant',
            'blue_enchant',
            'green_enchant',
            'red_enchant',
            'white_enchant'
        ]
        return self.card_type in enchant_card_types

    def load_card_template(self):
        """Loads the base card template"""
        image_path = f"assets/templates/{self.card_type}.png"
        with Image.open(image_path) as card_image:
            self.card = card_image.copy()

    def choose_card_type(self):
        """Returns a random card type and associated color"""
        base_card_type = random.sample(['instant', 'sorcery', 'land', 'creature', 'artifact', 'enchant'], 1)[0]
        # base_card_type = 'enchant'  # Override for debugging.
        if base_card_type == 'instant':
            card_types = [
                'black_instant',
                'blue_instant',
                'green_instant',
                'red_instant',
                'white_instant',
            ]
            self.card_type = random.choice(card_types)

        if base_card_type == 'sorcery':
            card_types = [
                'black_sorcery',
                'blue_sorcery',
                'green_sorcery',
                'red_sorcery',
                'white_sorcery',
            ]
            self.card_type = random.choice(card_types)

        if base_card_type == 'land':
            card_types = [
                'artifact_land',
                'black_land',
                'blue_land',
                'green_land',
                'red_land',
                'white_land',
            ]
            self.card_type = random.choice(card_types)

        if base_card_type == 'creature':
            card_types = [
                'artifact_creature',
                'black_creature',
                'blue_creature',
                'gold_creature',
                'green_creature',
                'red_creature',
                'white_creature',
            ]
            self.card_type = random.choice(card_types)

        if base_card_type == 'artifact':
            card_types = [
                'artifact'
            ]
            self.card_type = random.choice(card_types)

        if base_card_type == 'enchant':
            card_types = [
                'black_enchant',
                'blue_enchant',
                'green_enchant',
                'red_enchant',
                'white_enchant',
            ]
            self.card_type = random.choice(card_types)

        card_color_mapping = {
            'artifact_creature': 'artifact',
            'black_creature': 'black',
            'blue_creature': 'blue',
            'gold_creature': 'gold',
            'green_creature': 'green',
            'red_creature': 'red',
            'white_creature': 'white',
            'artifact_land': 'artifact',
            'black_land': 'black',
            'blue_land': 'blue',
            'green_land': 'green',
            'red_land': 'red',
            'white_land': 'white',
            'black_instant': 'black',
            'blue_instant': 'blue',
            'green_instant': 'green',
            'red_instant': 'red',
            'white_instant': 'white',
            'black_sorcery': 'black',
            'blue_sorcery': 'blue',
            'green_sorcery': 'green',
            'red_sorcery': 'red',
            'white_sorcery': 'white',
            'artifact': 'artifact',
            'black_enchant': 'black',
            'blue_enchant': 'blue',
            'green_enchant': 'green',
            'red_enchant': 'red',
            'white_enchant': 'white',
        }
        self.card_color = card_color_mapping.get(self.card_type, 'error')

    @staticmethod
    def write_llm_prompts_to_file(*prompt_sets):
        """Writes the prompt to a file for use by the llm script"""
        all_prompts = []
        for prompts in prompt_sets:
            all_prompts.append(prompts)
        with open('assets/json/llm_prompt.json', 'w', encoding="utf-8") as llm_prompt_file:
            json.dump(all_prompts, llm_prompt_file, indent=4)

    @staticmethod
    def get_random_artist_prompt():
        """Returns a string containing a random artist from a csv file full of artists"""
        selected_artist = random.choice(artist_data)
        return selected_artist.get('prompt')
