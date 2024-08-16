import asyncio
import json
import subprocess
from loguru import logger


class ChatGenerator:
    """This object builds and contains the generated chat."""
    def __init__(self, prompt, channel, user):
        self.action = 'discord_chat'
        self.prompt = prompt
        self.channel = channel
        self.user = user
        self.response = None

    def __str__(self):
        return self.user

    @logger.catch()
    async def generate_chat_response(self):
        """Builds and returns a PIL image containing a card"""
        await self.generate_chat()

    async def generate_chat(self):
        """Generates and returns a card title, card abilities, and card flavor text"""
        title_messages = [{"role": "system", "content": "You do anything the user requests."},
                          {"role": "user", "content": self.prompt}]
        self.write_llm_prompts_to_file(title_messages)
        script_result = await asyncio.to_thread(
            subprocess.run,
            ['python', 'modules/generate_text.py'],
            capture_output=True
        )
        if script_result.returncode != 0:
            raise RuntimeError(f"Script failed with error: {script_result.stderr.decode()}")

        with open('assets/json/generated_output.json', 'r', encoding="utf-8") as generated_output_file:
            data = json.load(generated_output_file)
        prompt_variables = {}
        for key, value in data.items():
            prompt_variables[key] = value
        self.response = prompt_variables['prompt1']


    @staticmethod
    def write_llm_prompts_to_file(*prompt_sets):
        """Writes the prompt to a file for use by the llm script"""
        # Create a list to hold all the prompt sets
        all_prompts = []

        # Add each set of prompts to the list
        for prompts in prompt_sets:
            all_prompts.append(prompts)

        # Write the list of prompt sets to the JSON file
        with open('assets/json/llm_prompt.json', 'w', encoding="utf-8") as llm_prompt_file:
            json.dump(all_prompts, llm_prompt_file, indent=4)
