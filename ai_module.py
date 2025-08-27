# ai_module.py

import re
from collections import Counter

# Categories and corresponding keywords
CATEGORIES = {
    "road": ["road", "pothole", "street", "highway", "sidewalk", "speedbreaker", "traffic"],
    "electricity": ["electricity", "power", "light", "transformer", "outage", "voltage", "cable"],
    "water": ["water", "pipeline", "drain", "sewage", "tap", "leak", "flood"],
    "garbage": ["garbage", "waste", "trash", "cleanliness", "bin", "dump", "rubbish"],
    "other": []  # catch-all
}

# Recommended schemes for each category
RECOMMENDED_SCHEMES = {
    "road": "Urban Development Grant",
    "electricity": "Power Infrastructure Support",
    "water": "Clean Water Initiative",
    "garbage": "Municipal Waste Management Scheme",
    "other": "General Civic Improvement Scheme"
}

def clean_text(text: str) -> str:
    """
    Basic text cleaning: lowercase, strip, remove special characters
    """
    text = text.lower().strip()
    text = re.sub(r'[^a-zA-Z0-9\s]', '', text)
    return text

def classify_complaint(text: str) -> str:
    """
    Classify complaint into a category based on keyword frequency.
    Returns the category with the most matches; defaults to 'other'.
    """
    text = clean_text(text)
    category_counts = Counter()

    for category, keywords in CATEGORIES.items():
        for keyword in keywords:
            # Count how many times each keyword appears
            occurrences = text.count(keyword)
            if occurrences > 0:
                category_counts[category] += occurrences

    if category_counts:
        # Return the category with the highest count
        return category_counts.most_common(1)[0][0]
    else:
        return "other"

def analyze_complaint(text: str) -> dict:
    """
    Returns a dict with category and recommended scheme
    """
    category = classify_complaint(text)
    scheme = RECOMMENDED_SCHEMES.get(category, "General Civic Improvement Scheme")
    return {
        "category": category,
        "recommended_scheme": scheme
    }

# Example usage
if __name__ == "__main__":
    sample_text = "There is a huge pothole on the street and the water pipeline nearby is leaking."
    result = analyze_complaint(sample_text)
    print(result)
