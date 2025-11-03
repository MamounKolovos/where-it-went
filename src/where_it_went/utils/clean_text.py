import html
import re

def cleanText(text: str) -> str:
    """
    Convert markdown Gemini response to HTML and clean text.
    """
    text = html.unescape(text)  # Decode HTML entities
    text = re.sub(r"\*\*(Key Findings|Breakdown|Insights):\*\*", r"<h4>\1:</h4>", text)  # Convert section headers
    text = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", text)  # Convert bold text
    text = re.sub(r"\u2022\s*(.*)", r"<li>\1</li>", text)  # Convert bullet points
    text = re.sub(r"(<li>.*?</li>)", r"<ul>\1</ul>", text)  # Wrap bullet points in <ul>
    text = re.sub(r"</ul>\s*<ul>", "", text)  # Remove redundant <ul> tags
    return text.strip()