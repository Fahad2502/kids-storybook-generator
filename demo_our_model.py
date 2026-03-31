"""
demo_our_model.py
-----------------
Demonstrates our fine-tuned GPT-2 model trained on the TinyStories dataset.
Run with: venv\Scripts\python demo_our_model.py

This is SEPARATE from the main app (app.py).
It shows the research contribution: a domain-specific model fine-tuned
for children's story generation.
"""

from transformers import GPT2Tokenizer, GPT2LMHeadModel, pipeline
import textwrap, sys

MODEL_PATH = "tinystories-gpt2-final"

# ── Load model ────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("  Kids Story Generator — Fine-tuned GPT-2 Demo")
print("  Model: GPT-2 (117M) fine-tuned on TinyStories dataset")
print("  Dataset: 50,000 children's stories from roneneldan/TinyStories")
print("  Perplexity: 3.68 (vs 10.44 for base GPT-2 — 2.8x improvement)")
print("="*60 + "\n")

print("Loading fine-tuned model...")
try:
    tokenizer = GPT2Tokenizer.from_pretrained(MODEL_PATH)
    tokenizer.pad_token = tokenizer.eos_token
    model = GPT2LMHeadModel.from_pretrained(MODEL_PATH)
    # Fix smart quotes that cause encoding issues on Windows console
    import sys
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    gen = pipeline(
        "text-generation",
        model=model,
        tokenizer=tokenizer,
        device=-1,  # CPU
    )
    print("Model loaded successfully!\n")
except Exception as e:
    print(f"Error loading model: {e}")
    print(f"Make sure '{MODEL_PATH}/' folder exists with model.safetensors inside.")
    sys.exit(1)


def generate_story(prompt: str, max_length: int = 200) -> str:
    result = gen(
        prompt,
        max_new_tokens=max_length,
        do_sample=True,
        temperature=0.8,
        top_p=0.9,
        repetition_penalty=1.3,   # reduces the "The end. The end." repetition
        pad_token_id=tokenizer.eos_token_id,
    )
    return result[0]["generated_text"]


def print_story(title: str, prompt: str, story: str):
    print("─" * 60)
    print(f"  {title}")
    print("─" * 60)
    print(f"  Prompt: \"{prompt}\"\n")
    # Word-wrap the output nicely
    wrapped = textwrap.fill(story, width=58, initial_indent="  ", subsequent_indent="  ")
    print(wrapped)
    print()


# ── Demo stories ──────────────────────────────────────────────────────────────
prompts = [
    ("Adventure Story",    "Once upon a time, a little boy named Ali found a mysterious map in the forest"),
    ("Friendship Story",   "Sara wanted to keep the baby bird forever, but her mother said"),
    ("Fantasy Story",      "The dragon offered Omar great power, but Omar knew that"),
]

print("Generating stories with our fine-tuned model...\n")

for title, prompt in prompts:
    story = generate_story(prompt)
    print_story(title, prompt, story)

print("="*60)
print("  Model Stats:")
print(f"  - Architecture:  GPT-2 Small (117M parameters)")
print(f"  - Training data: 50,000 TinyStories samples")
print(f"  - Epochs:        2")
print(f"  - Base PPL:      10.44")
print(f"  - Fine-tuned PPL: 3.68")
print(f"  - Improvement:   2.8x better on children's stories")
print("="*60 + "\n")
