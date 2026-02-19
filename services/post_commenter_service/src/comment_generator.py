from __future__ import annotations

import random
import logging
from typing import List


class CommentGenerator:
    """Generates random comments for Telegram posts."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)
        
        # Comment templates organized by type
        self._comment_templates = {
            "positive": [
                "Great post! 👍",
                "Amazing content!",
                "Love this! ❤️",
                "Fantastic! 🔥",
                "Wonderful! ✨",
                "Perfect! 💯",
                "Excellent work!",
                "Brilliant! 🌟",
                "Outstanding! 🎉",
                "Superb! 💫",
            ],
            "engagement": [
                "Interesting perspective!",
                "Thanks for sharing!",
                "This is so true!",
                "Couldn't agree more!",
                "Well said!",
                "Great point!",
                "Absolutely!",
                "So relatable!",
                "This! 👏",
                "Exactly my thoughts!",
            ],
            "questions": [
                "How did you do this?",
                "What's your secret?",
                "Can you share more details?",
                "This is interesting, tell me more!",
                "How long did this take?",
                "What tools did you use?",
                "Any tips for beginners?",
                "Where can I learn more?",
                "Is this available everywhere?",
                "What's the next step?",
            ],
            "short": [
                "Nice!",
                "Cool!",
                "Wow!",
                "Good!",
                "Yes!",
                "True!",
                "Love it!",
                "Great!",
                "Amazing!",
                "Perfect!",
            ],
            "emoji": [
                "👍",
                "❤️",
                "🔥",
                "✨",
                "🎉",
                "💯",
                "🌟",
                "💫",
                "👏",
                "😊",
            ],
            "casual": [
                "lol nice",
                "good stuff",
                "pretty cool",
                "not bad",
                "solid work",
                "keep it up",
                "good job",
                "nice one",
                "well done",
                "great stuff",
            ],
        }

        # Additional random phrases to add variety
        self._prefixes = [
            "Wow, ",
            "Oh wow, ",
            "Damn, ",
            "Whoa, ",
            "Holy, ",
            "Man, ",
            "Dude, ",
            "Bro, ",
        ]
        
        self._suffixes = [
            "!",
            "!!",
            "!!!",
            " 💯",
            " 🔥",
            " 👍",
            " ❤️",
            " ✨",
        ]

    def generate_comment(self, max_length: int = 100) -> str:
        """Generate a random comment."""
        comment_type = random.choice(list(self._comment_templates.keys()))
        templates = self._comment_templates[comment_type]
        
        base_comment = random.choice(templates)
        
        # Occasionally add prefixes or suffixes for variety
        if random.random() < 0.2:  # 20% chance
            if random.random() < 0.5:
                base_comment = random.choice(self._prefixes) + base_comment.lower()
            else:
                base_comment = base_comment + random.choice(self._suffixes)
        
        # Ensure max length
        if len(base_comment) > max_length:
            base_comment = base_comment[:max_length-3] + "..."
        
        self._logger.debug(f"Generated {comment_type} comment: {base_comment}")
        return base_comment

    def generate_batch(self, count: int, max_length: int = 100) -> List[str]:
        """Generate multiple random comments."""
        comments = []
        for _ in range(count):
            comments.append(self.generate_comment(max_length))
        return comments

    def get_stats(self) -> dict:
        """Get generator statistics."""
        total_templates = sum(len(templates) for templates in self._comment_templates.values())
        return {
            "comment_types": len(self._comment_templates),
            "total_templates": total_templates,
            "prefixes": len(self._prefixes),
            "suffixes": len(self._suffixes),
        }
