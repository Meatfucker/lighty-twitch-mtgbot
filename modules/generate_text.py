"""This loads prompts from llm_prompts.json, then stores the results in generated_output.json"""
import json
import torch
import transformers
import gc
torch.cuda.empty_cache()
gc.collect()

# Load the multiple prompts
with open('assets/json/llm_prompt.json', 'r', encoding="utf-8") as file:
    llm_prompts_list = json.load(file)

llm_pipeline = transformers.pipeline(
    "text-generation",
    model="cognitivecomputations/Llama-3-8B-Instruct-abliterated-v2",
    model_kwargs={"torch_dtype": torch.float32, "quantization_config": {"load_in_8bit": True}},
    device_map="auto"
)

terminators = [
    llm_pipeline.tokenizer.eos_token_id,
    llm_pipeline.tokenizer.convert_tokens_to_ids("<|eot_id|>")
]
output_data = {}

# Iterate through each prompt set in the list
for idx, llm_prompts in enumerate(llm_prompts_list):
    title_output = llm_pipeline(
        llm_prompts,
        max_new_tokens=2000,
        eos_token_id=terminators,
        do_sample=True,
        temperature=1.4,
        top_p=0.9,
        pad_token_id=llm_pipeline.tokenizer.eos_token_id
    )
    title = title_output[0]["generated_text"][-1]["content"]
    output_data[f"prompt{idx + 1}"] = title

with open('assets/json/generated_output.json', 'w', encoding="utf-8") as outfile:
    json.dump(output_data, outfile, indent=4)

llm_pipeline = None
torch.cuda.empty_cache()
gc.collect()