
import ollama
import json
from typing import List, Dict

def generate_quiz_from_text(text: str) -> List[Dict]:
    """
    Generate as many multiple-choice questions as possible from the given text using Ollama.
    
    Args:
        text (str): The source text to generate questions from.
        
    Returns:
        List[Dict]: A list of dictionaries, where each dictionary represents a question:
            {
                "question": "The question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "The correct option text"
            }
    """
    if not text or not text.strip():
        return []

    prompt = f"""
    You are a quiz generator. Your task is to generate exactly 10 multiple-choice questions based on the text provided below.
    
    Text: "{text}"
    
    Output Format:
    Return a JSON object with a single key "questions" which is a list of 10 question objects.
    
    {{
        "questions": [
            {{
                "question": "Question text 1",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A"
            }},
            ... (4 more questions) ...
        ]
    }}
    
    Constraints:
    - Generate EXACTLY 10 questions.
    - Do not stop after 1 question.
    - No Null Answers.
    - No Duplicate Questions.
    - Ensure all strings are properly escaped.
    """

    try:
        response = ollama.chat(
            model='phi3:mini', 
            format='json', 
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
            options={
                'temperature': 0.7, 
                'num_predict': 2048  # Ensure enough tokens for multiple questions
            }
        )

        llm_output = response['message']['content']
        
        # Determine if we need to clean the output (sometimes models add extra tokens)
        clean_output = llm_output.strip()
        
        try:
            quiz_data = json.loads(clean_output)
        except json.JSONDecodeError:
            # Fallback: try to find the list part if there's header text
            start = clean_output.find('{')
            end = clean_output.rfind('}')
            if start != -1 and end != -1:
                clean_output = clean_output[start:end+1]
                quiz_data = json.loads(clean_output)
            else:
                raise ValueError("Could not parse JSON from model output")

        # Validate structure
        valid_questions = []
        
        # Handle new format: {"questions": [...]}
        if isinstance(quiz_data, dict) and "questions" in quiz_data and isinstance(quiz_data["questions"], list):
            quiz_list = quiz_data["questions"]
        elif isinstance(quiz_data, list):
            quiz_list = quiz_data
        elif isinstance(quiz_data, dict) and "question" in quiz_data:
            quiz_list = [quiz_data]
        else:
            quiz_list = []

        for q in quiz_list:
            if (isinstance(q, dict) and 
                "question" in q and 
                "options" in q and 
                "correct_answer" in q and
                isinstance(q["options"], list) and
                len(q["options"]) >= 2):
                valid_questions.append(q)

        return valid_questions

    except Exception as e:
        print(f"Error generating quiz: {e}")
        return []

def generate_summary_from_text(text: str) -> str:
    """
    Generate a summary of the provided text using Ollama.
    """
    if not text or not text.strip():
        return ""

    # Truncate text to avoid context limits (approx 5000 chars)
    truncated_text = text[:5000]

    prompt = f"""
    You are an intelligent teaching assistant. Summarize the following educational content into a concise paragraph suitable for students.
    
    Content: "{truncated_text}"
    """

    try:
        response = ollama.chat(
            model='phi3:mini', 
            messages=[
                {
                    'role': 'user',
                    'content': prompt,
                },
            ],
            options={
                'temperature': 0.5, 
            }
        )

        return response['message']['content'].strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Summary unavailable."
