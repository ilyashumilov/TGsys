from __future__ import annotations

import logging
import random
from typing import List


class CommentGenerator:
    """Generate comments for Telegram posts."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # Comment templates
        self._positive_comments = [
            "Great post! 👍",
            "Thanks for sharing this!",
            "Very interesting perspective",
            "I completely agree with this",
            "This is really helpful, thank you",
            "Excellent points here",
            "Well said! 👏",
            "This makes a lot of sense",
            "Thanks for the insights",
            "Really appreciate this content",
        ]
        
        self._neutral_comments = [
            "Interesting take on this",
            "Good to know",
            "Thanks for the information",
            "Noted, thanks",
            "Good point",
            "I see what you mean",
            "That's one way to look at it",
            "Fair enough",
            "Makes sense",
            "Thanks for sharing",
        ]
        
        self._engagement_comments = [
            "What do you think about this?",
            "Anyone else have thoughts on this?",
            "This raises some good questions",
            "I'd love to hear more about this",
            "How do others feel about this?",
            "This is definitely worth discussing",
            "Looking forward to more on this topic",
            "This deserves more attention",
            "What's the general consensus on this?",
            "This should be shared more widely",
        ]

    def generate_comment(self, context: dict = None) -> str:
        """Generate a contextual comment."""
        try:
            # Choose comment type based on context or random
            if context:
                comment_type = self._choose_comment_type(context)
            else:
                comment_type = random.choice(['positive', 'neutral', 'engagement'])
            
            # Get comment from appropriate category
            if comment_type == 'positive':
                comments = self._positive_comments
            elif comment_type == 'neutral':
                comments = self._neutral_comments
            else:
                comments = self._engagement_comments
            
            # Add some variation
            base_comment = random.choice(comments)
            
            # Occasionally add extra variation
            if random.random() < 0.3:  # 30% chance
                variations = [
                    "!",
                    " 👍",
                    " 👏",
                    " 💯",
                    " 🔥",
                    " ✨",
                ]
                base_comment += random.choice(variations)
            
            return base_comment
            
        except Exception as e:
            self._logger.error(f"Error generating comment: {e}")
            # Fallback to simple comment
            return "Thanks for sharing! 👍"

    def _choose_comment_type(self, context: dict) -> str:
        """Choose comment type based on context."""
        # Simple logic - can be enhanced based actual content analysis
        message_length = len(context.get('message_text', ''))
        
        if message_length > 200:
            # Longer posts get engagement questions
            return 'engagement'
        elif message_length > 50:
            # Medium posts get positive reactions
            return 'positive'
        else:
            # Short posts get neutral responses
            return 'neutral'

    def get_multiple_comments(self, count: int = 5, context: dict = None) -> List[str]:
        """Generate multiple unique comments."""
        comments = []
        attempts = 0
        max_attempts = count * 3  # Allow some duplicates
        
        while len(comments) < count and attempts < max_attempts:
            comment = self.generate_comment(context)
            if comment not in comments:
                comments.append(comment)
            attempts += 1
        
        return comments[:count]
