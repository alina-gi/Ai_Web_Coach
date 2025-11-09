import json
import os
from datetime import datetime
from typing import Dict, Any, List


class FeedbackManager:
    """Manages saving and loading feedback data to/from JSON file."""
    
    def __init__(self, json_file_path: str = "feedback_data.json"):
        """
        Initialize FeedbackManager.
        
        Args:
            json_file_path: Path to the JSON file where feedback will be stored.
                           Defaults to "feedback_data.json" in the current directory.
        """
        self.json_file_path = json_file_path
        # Get the directory of the current file (Web_app folder)
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.full_path = os.path.join(self.base_dir, json_file_path)
    
    def _load_feedback_data(self) -> List[Dict[str, Any]]:
        """
        Load existing feedback data from JSON file.
        
        Returns:
            List of feedback entries. Returns empty list if file doesn't exist or is invalid.
        """
        if not os.path.exists(self.full_path):
            return []
        
        try:
            with open(self.full_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure it's a list
                if isinstance(data, list):
                    return data
                else:
                    # If it's a dict or other type, wrap it in a list
                    return [data] if data else []
        except (json.JSONDecodeError, IOError) as e:
            print(f"[FeedbackManager] Warning: Could not load feedback data: {e}")
            return []
    
    def _save_feedback_data(self, data: List[Dict[str, Any]]) -> bool:
        """
        Save feedback data to JSON file.
        
        Args:
            data: List of feedback entries to save.
            
        Returns:
            True if successful, False otherwise.
        """
        try:
            with open(self.full_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"[FeedbackManager] Error: Could not save feedback data: {e}")
            return False
    
    def save_feedback(
        self,
        user_message: str,
        ai_response: str,
        feedback: str,
        detected_mood: str = ""
    ) -> bool:
        """
        Save a new feedback entry.
        
        Args:
            user_message: The user's original message.
            ai_response: The AI's response that was rated.
            feedback: Either "positive" or "negative".
            detected_mood: The mood that was detected from the user message.
            
        Returns:
            True if saved successfully, False otherwise.
        """
        # Load existing data
        feedback_list = self._load_feedback_data()
        
        # Create new entry
        new_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "ai_response": ai_response,
            "feedback": feedback,
            "detected_mood": detected_mood
        }
        
        # Append to list
        feedback_list.append(new_entry)
        
        # Save back to file
        success = self._save_feedback_data(feedback_list)
        
        if success:
            # Print console log
            emoji = "👍" if feedback.lower() == "positive" else "👎"
            feedback_type = "Positive" if feedback.lower() == "positive" else "Negative"
            print(f"[Feedback Saved] {emoji} {feedback_type} for message: \"{user_message}\"")
        
        return success
    
    def get_all_feedback(self) -> List[Dict[str, Any]]:
        """
        Get all saved feedback entries.
        
        Returns:
            List of all feedback entries.
        """
        return self._load_feedback_data()

