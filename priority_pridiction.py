import torch
from transformers import BertTokenizer, BertForSequenceClassification
from typing import Dict

class PriorityPredictor:
    """
    A class to load a fine-tuned BERT model and predict complaint priority.
    """
    def __init__(self, model_path: str = 'priority_prediction_model.pth'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        print("🚀 Loading BERT tokenizer...")
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased', do_lower_case=True)
        print("✅ Tokenizer loaded.")

        print(f"🚀 Loading fine-tuned model from {model_path}...")
        self.model = BertForSequenceClassification.from_pretrained(
            "bert-base-uncased",
            num_labels=2,
            output_attentions=False,
            output_hidden_states=False,
        )
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.to(self.device)
        self.model.eval()
        print("✅ Model loaded successfully!")

        self.priority_labels = ['low', 'high']

    def predict(self, complaint_text: str) -> Dict:
        """
        Predicts the priority of a single complaint.
        """
        encoded_input = self.tokenizer.encode_plus(
            complaint_text,
            add_special_tokens=True,
            max_length=64,
            truncation=True,
            padding='max_length',
            return_attention_mask=True,
            return_tensors='pt',
        )
        
        input_ids = encoded_input['input_ids'].to(self.device)
        attention_mask = encoded_input['attention_mask'].to(self.device)
        
        with torch.no_grad():
            outputs = self.model(input_ids, token_type_ids=None, attention_mask=attention_mask)
        
        logits = outputs.logits
        predicted_class = torch.argmax(logits, dim=1).item()
        predicted_priority = self.priority_labels[predicted_class]
        
        return {
            "predicted_priority": predicted_priority,
            "confidence": torch.nn.functional.softmax(logits, dim=1).max().item()
        }