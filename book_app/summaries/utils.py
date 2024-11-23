import requests
from transformers import pipeline
import fitz
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
from PyPDF2 import PdfReader


def get_book_info(title):
    response = requests.get(f'https://www.googleapis.com/books/v1/volumes?q={'title'}')
    if response.status_code == 200:
        return response.json()
    return None 

summarizer = pipeline("summarization", model="distilgpt2")

def summarize_text(text):
    # Process the text using DistilGPT-2
    return summarizer(text, max_length=150, min_length=40, do_sample=False)[0]["summary_text"]

def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    return text

def generate_summary(pdf_path):
    # Load the model and tokenizer for DistilGPT-2
    model_name = "distilgpt2"
    model = GPT2LMHeadModel.from_pretrained(model_name)
    tokenizer = GPT2Tokenizer.from_pretrained(model_name)

    # Extract text from the PDF
    text = extract_text_from_pdf(pdf_path)
    
    # Limit the text to a manageable length (GPT-2 works best with shorter inputs)
    max_length = 500  # Adjust as needed
    if len(text) > max_length:
        text = text[:max_length]

    # Prepare input tokens
    inputs = tokenizer.encode(text, return_tensors="pt")

    # Generate summary
    summary_ids = model.generate(
        inputs,
        max_length=160,      # Maximum length of the summary
        num_beams=5,         # Beam search for quality
        no_repeat_ngram_size=2,
        early_stopping=True
    )

    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary
