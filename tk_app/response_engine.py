# response_engine.py
from textblob import TextBlob
import random
import json
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from tk_app.preference_learner import PreferenceLearner
from openai import OpenAI
from dotenv import load_dotenv



class ResponseEngine:
    def __init__(self, mode="api"):
        self.mode = mode
        self.analyzer = SentimentIntensityAnalyzer()  # ← Initialize VADER here

        # Load API key and initialize client
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("[WARNING] No OpenAI API key found. Running in local mode.")
        self.client = OpenAI(api_key=api_key) if api_key else None

        # Load previous messages (memory)
        self.recent_messages = []
        self.load_conversation()  # ✅ keep this after initializing the variable, not before

        # Preference data loaded from user feedback
        self.user_feedback_path = "data/user_data.json"
        self.liked_tone_counts, self.liked_mood_counts = self._load_user_preferences()
        self.preference_learner = PreferenceLearner()

        print(f"[DotPi] ResponseEngine initialized in {self.mode.upper()} mode.")


    def save_conversation(self):
        """Save recent messages to a local JSON file."""
        with open("recent_messages.json", "w", encoding="utf-8") as f:
            json.dump(self.recent_messages, f, ensure_ascii=False, indent=2)

    def load_conversation(self):
        """Load previous messages from local JSON file."""
        if os.path.exists("recent_messages.json"):
            with open("recent_messages.json", "r", encoding="utf-8") as f:
                self.recent_messages = json.load(f)
        else:
            self.recent_messages = []


        


    def _load_user_preferences(self):
        """Load user feedback and aggregate likes for tone and mood."""
        liked_tone_counts = {"Blunt": 0, "Empathetic": 0, "Balanced": 0}
        liked_mood_counts = {"positive": 0, "negative": 0, "neutral": 0}

        try:
            if os.path.exists(self.user_feedback_path):
                with open(self.user_feedback_path, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            try:
                                if entry.get("feedback") == "like":
                                    tone = entry.get("tone_used")
                                    mood = entry.get("detected_mood")
                                    if tone in liked_tone_counts:
                                        liked_tone_counts[tone] += 1
                                    # Normalize mood keys to our template keys
                                    if mood in ("positive", "negative", "neutral"):
                                        liked_mood_counts[mood] += 1
                                    elif mood in ("happy",):
                                        liked_mood_counts["positive"] += 1
                                    elif mood in ("sad",):
                                        liked_mood_counts["negative"] += 1
                            except Exception:
                                # Skip malformed entries
                                continue
        except Exception:
            # On any error, return zeroed prefs to avoid breaking logic
            pass
        #print("Liked tones:", liked_tone_counts)
        #print("Liked moods:", liked_mood_counts)


        return liked_tone_counts, liked_mood_counts

    def test_openai_connection(self, message="Hello DotPi!"):
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a friendly AI coach."},
                    {"role": "user", "content": message}
                ]        )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"


    def _weighted_choice(self, weights_dict):
        """Return a key from weights_dict based on weighted random selection."""
        items = list(weights_dict.items())
        total = sum(max(w, 0) for _, w in items) or 1
        r = random.uniform(0, total)
        upto = 0
        for key, weight in items:
            w = max(weight, 0)
            if upto + w >= r:
                return key
            upto += w
        return items[-1][0]

    def detect_mood(self, message):
        """Smarter mood detection using VADER sentiment analysis."""
        try:
            scores = self.analyzer.polarity_scores(message)
            compound = scores["compound"]

            print("Scores:", scores, "Compound:", compound)


            if compound >= 0.3:
                return "positive"
            elif compound <= -0.3:
                return "negative"
            else:
                return "neutral"
        except Exception:
            return "neutral"


    def generate_local_response(self, message, tone, mood=None):
        """
        Local response generator.
        Accepts mood parameter but will still work if mood is None.
        """
        # If mood wasn't passed, try to detect it (fallback)
        if mood is None:
            mood = self.detect_mood(message)

        # map sentiments to our simple keys
        if mood in ("positive", "happy", "happy-ish"):
            base_key = "positive"
        elif mood in ("negative", "sad"):
            base_key = "negative"
        else:
            base_key = "neutral"

        templates = {
            "positive": [
                "That’s great! Keep that energy going.",
                "I like your attitude — positivity always helps.",
                "Nice progress — let’s build on that."
            ],
            "negative": [
                "That sounds tough, but let’s figure out a way forward.",
                "I get it — sometimes things just don’t feel right. What do you think caused it?",
                "I hear you. We'll take a small step together."
            ],
            "neutral": [
                "Hmm, tell me more about that.",
                "Alright, let’s break this down together.",
                "Okay — what's the most useful next step?"
            ]
        }

        tone_effect = {
            "Blunt": "Here’s my honest take: ",
            "Empathetic": "I understand how you feel. ",
            "Balanced": ""
        }

        # --- Weighted suggestion logic based on liked tone/mood ---
        # Start with small base weights to keep behavior stable
        weights = {"positive": 1, "negative": 1, "neutral": 1}

        # Preserve existing behavior by biasing toward detected/base_key
        weights[base_key] += 3

        # Boost if user liked this mood previously
        for mood_key, count in self.liked_mood_counts.items():
            if count > 0:
                weights[mood_key] += 10

        # Boost toward the detected/base_key if the current tone is among liked tones
        # (tone is fixed by caller; we only bias mood key selection)
        if tone in self.liked_tone_counts and self.liked_tone_counts[tone] > 0:
            weights[base_key] += 10

        # Choose the mood key using weighted random selection
        chosen_key = self._weighted_choice(weights)

        prefix = tone_effect.get(tone, "")
        choice = random.choice(templates.get(chosen_key, templates["neutral"]))
        return prefix + choice

    def generate_response(self, message, tone, mood=None):
        """Main function — accepts mood and switches between local or API."""
        if self.mode == "local":
            # Get preferred tone from learner
            preferred_tone = self.preference_learner.recommend_tone()
            #print(f"[DEBUG] Tone in use: {preferred_tone or tone}")  # Debug confirmation
            
            # Generate response with preferred tone if available
            return self.generate_local_response(message, preferred_tone or tone, mood)
        else:
            return self.generate_ai_response(message, tone, mood)



    # --- Refresh user preferences ---
    def refresh_user_preferences(self):
        """Reload liked tone and mood counts from user feedback file."""
        self.liked_tone_counts, self.liked_mood_counts = self._load_user_preferences()
    

    def generate_ai_response(self, message, tone, mood=None):
        """
        Generate AI response with memory, tone, and mood awareness.
        Remembers last few exchanges and uses them in context.
        """

        try:
            # 1️⃣ Detect mood if not provided
            if mood is None:
                mood = self.detect_mood(message)

            # 2️⃣ Get preferred tone (learned locally)
            preferred_tone = self.preference_learner.recommend_tone() or tone

            # 3️⃣ Load conversation memory (recent_messages is stored in JSON)
            self.load_conversation()

            # 4️⃣ Build short memory context (only last few lines)
            context = ""
            if self.recent_messages:
                for u, a in self.recent_messages[-5:]:
                    context += f"Taiba: {u}\nDotPi: {a}\n"
            else:
                context = "(No prior chat history yet.)\n"

            # 5️⃣ Build advanced system prompt
            system_prompt = (
                "You are DotPi — Taiba’s personal AI coach and creative partner. "
                "You remember your recent chats and use that context naturally in conversation. "
                "Speak warmly, honestly, and with emotional intelligence. "
                "Always call her by name, 'Taiba'. "
                "You are realistic yet motivating, using humor or depth only when it fits. "
                f"\n\nHere’s the recent chat context:\n{context}\n"
                f"Detected mood: {mood}. "
                f"Preferred tone: {preferred_tone}. "
                "Your reply should feel natural, human-like, and emotionally attuned. "
                "Be concise — a few sentences at most unless depth is clearly needed."
            )

            # 6️⃣ Generate GPT-based response with context
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.8
            )

            ai_message = response.choices[0].message.content.strip()

            # 7️⃣ Save new pair (for memory)
            self.recent_messages.append((message, ai_message))
            if len(self.recent_messages) > 10:
                self.recent_messages = self.recent_messages[-10:]

            self.save_conversation()

            return ai_message

        except Exception as e:
            # 8️⃣ Fallback if API fails
            print(f"[DotPi] API error → Falling back to local mode: {e}")
            return self.generate_local_response(message, preferred_tone, mood)
