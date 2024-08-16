"""This takes a prompt via command line and saves the generated image to generated_image.png"""
import argparse
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
import torch
import gc
from settings import SETTINGS
from loguru import logger

torch.cuda.empty_cache()
gc.collect()

parser = argparse.ArgumentParser(
    description="Generate an image using Stable Diffusion XL and a prompt from the command line."
)
parser.add_argument('generate_prompt', type=str, help='The prompt to generate the image.')
args = parser.parse_args()
scheduler = DPMSolverMultistepScheduler.from_pretrained(
    "stabilityai/stable-diffusion-xl-base-1.0",
    subfolder="scheduler"
)
scheduler.config.algorithm_type = 'sde-dpmsolver++'
sd_pipeline = StableDiffusionXLPipeline.from_single_file(
    "https://huggingface.co/ykurilov/ZavyChromaXL_v6/blob/main/zavychromaxl_v60.safetensors",
    scheduler=scheduler,
    use_safetensors=True,
    device_map="auto",
    safety_checker=None,
    torch_dtype=torch.float32
)
if SETTINGS['sdxl_lora'][0]:
   sd_pipeline.load_lora_weights(f"assets/{SETTINGS['sdxl_lora'][0]}", weight_name=SETTINGS['sdxllora'][0])
sd_pipeline.to("cuda")


generated_image = sd_pipeline(
    prompt=args.generate_prompt,
    negative_prompt="flash photography, suit, film grain",
    guidance_scale=7,
    num_inference_steps=30
)
image = generated_image.images[0]
resized_image = image.resize((568, 465))
resized_image.save('assets/generated_image.png')
scheduler = None
sd_pipeline = None
generated_image = None
image = None
resized_image = None
del scheduler, sd_pipeline, generated_image, image, resized_image
torch.cuda.empty_cache()
gc.collect()