from sentence_transformers import SentenceTransformer
from merge_similer_test import RealtimeDBSCANProcessor
import pickle

# ✅ Load a real embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

processor = RealtimeDBSCANProcessor(model=model, groups={})

sample_complaints = [
    ("Power cut in my area", 29.391, 79.461),
    ("No electricity since morning", 29.392, 79.462),
    ("Water pipeline broken near market", 29.401, 79.471),
    ("Leakage in water supply line", 29.402, 79.472),
    ("Garbage not collected for 3 days", 29.395, 79.465),
    ("Dustbins overflowing in colony", 29.396, 79.466),
]

print("🚀 Training initial complaint clusters...")

for text, lat, lon in sample_complaints:
    result = processor.process_new_complaint(text, lat, lon)
    print("Processed:", text, "→", result)

with open("complaint_clustering_model.pkl", "wb") as f:
    pickle.dump(processor.groups, f)

print("✅ complaint_clustering_model.pkl saved with", len(processor.groups), "groups")



