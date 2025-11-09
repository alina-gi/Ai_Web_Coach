from flask import Flask, render_template, request, jsonify
from tk_app.response_engine import ResponseEngine
from tk_app.preference_learner import PreferenceLearner
from feedback_manager import FeedbackManager
import os

# Initialize Flask app
# Explicitly set template and static folder paths
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "templates"),
    static_folder=os.path.join(os.path.dirname(__file__), "static")
)

# Initialize your local AI engine
engine = ResponseEngine(mode="api")  # can switch to "api" later
learner = PreferenceLearner()

# Initialize feedback manager
feedback_manager = FeedbackManager()

# ----------------------------
# ROUTES
# ----------------------------

@app.route("/")
def home():
    """Render the main chat interface"""
    return render_template("chat.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Handle chat messages"""
    user_message = request.json.get("message", "")
    tone = learner.recommend_tone() or "Balanced"
    mood = engine.detect_mood(user_message)
    ai_response = engine.generate_response(user_message, tone, mood)

    return jsonify({
        "response": ai_response,
        "detected_mood": mood,
        "tone_used": tone
    })


@app.route("/feedback", methods=["POST"])
def feedback():
    """Handle feedback and save to JSON file"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        # Extract feedback data
        user_message = data.get("message", "")
        ai_response = data.get("response", "")
        feedback_type = data.get("feedback", "")
        detected_mood = data.get("mood", "")
        
        # Validate required fields
        if not feedback_type:
            return jsonify({"status": "error", "message": "Feedback type is required"}), 400
        
        # Save feedback using FeedbackManager
        success = feedback_manager.save_feedback(
            user_message=user_message,
            ai_response=ai_response,
            feedback=feedback_type,
            detected_mood=detected_mood
        )
        
        if success:
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Failed to save feedback"}), 500
            
    except Exception as e:
        print(f"[Feedback Route] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


# ----------------------------
# MAIN
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
