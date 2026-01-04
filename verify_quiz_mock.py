
import os
import sys
import json
from unittest.mock import MagicMock

# Ensure modules can be imported
sys.path.append(os.getcwd())

# Mock ollama BEFORE importing modules that use it
sys.modules['ollama'] = MagicMock()

# Mock response data
mock_json_response = """
[
    {
        "question": "What is the fourth planet from the Sun?",
        "options": ["Earth", "Mars", "Jupiter", "Venus"],
        "correct_answer": "Mars"
    },
    {
        "question": "What is the core of Mars made of?",
        "options": ["Gold", "Iron and Nickel", "Silica", "Hydrogen"],
        "correct_answer": "Iron and Nickel"
    }
]
"""

# Setup the mock return values
mock_chat_response = {'message': {'content': mock_json_response}}
sys.modules['ollama'].chat.return_value = mock_chat_response

try:
    from modules.quiz_generator import generate_quiz_from_text
    print("Successfully imported generate_quiz_from_text")
except ImportError as e:
    print(f"ImportError: {e}")
    sys.exit(1)

# Sample text 
sample_text = "Mock text about Mars."

try:
    print(f"Testing quiz generation on mock data...")
    questions = generate_quiz_from_text(sample_text)
    
    print(f"Generated {len(questions)} questions (mocked).")
    
    if len(questions) == 2:
        print("PASS: Correct number of questions parsed.")
        print(json.dumps(questions[0], indent=2))
    else:
        print(f"FAIL: Expected 2 questions, got {len(questions)}")
        
except Exception as e:
    print(f"An error occurred: {e}")
