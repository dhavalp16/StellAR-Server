from flask import Blueprint, request, jsonify
import ollama
import json
from typing import List, Dict, Union


llm_api = Blueprint('llm_api', __name__)

def generate_info_batch(keywords: Union[str, List[str]]) -> List[Dict]:
    """
    Generate info for multiple keywords using Ollama.
    Accepts a single string or a list of strings.
    Returns a list of dictionaries with info for each keyword.
    """
    # Handle single string input
    if isinstance(keywords, str):
        keywords = [keywords]
    elif not isinstance(keywords, list):
        keywords = list(keywords)
    
    # Remove duplicates while preserving order
    keywords = list(dict.fromkeys(keywords))
    
    if not keywords:
        raise ValueError("No keywords provided")
    
    results = []
    
    # Process each keyword individually
    for keyword in keywords:
        try:
            prompt = f"""
            Generate a JSON object about the following celestial body or scientific topic: "{keyword}".
            You are an educational API for a science app.
            In Facts you should give facts like radius, mass, temperature, etc. and only 3 facts per topic.
            The JSON must follow this exact schema (a single object, NOT an array):
            {{
                "title": "Name of the topic",
                "summary": "A 2-sentence summary suitable for a high school student.",
                "facts": [
                    "Interesting One Word fact 1",
                    "Interesting One Word fact 2",
                    "Interesting One Word fact 3"
                ]
            }}
            """

            # Call Ollama with format='json'
            response = ollama.chat(
                model='phi3:mini', 
                format='json', 
                messages=[
                    {
                        'role': 'user',
                        'content': prompt,
                    },
                ]
            )

            llm_output = response['message']['content']
            print(f"Raw LLM Output for '{keyword}': {llm_output[:100]}...")
            
            # Parse the JSON
            data = json.loads(llm_output)
            
            # Ensure it's a dict (not wrapped in array)
            if isinstance(data, list) and len(data) > 0:
                data = data[0]
            
            # Validation
            if not data.get('title'):
                data['title'] = keyword
            
            if not data.get('summary'):
                data['summary'] = "Information could not be generated at this time."
            
            if not data.get('facts') or len(data['facts']) == 0:
                data['facts'] = ["Data unavailable", "Data unavailable", "Data unavailable"]
            
            # Ensure facts are exactly 3
            data['facts'] = data['facts'][:3]
            while len(data['facts']) < 3:
                data['facts'].append("Data unavailable")
            
            results.append(data)
            print(f"✓ Generated info for: {keyword}")
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON Parse Error for '{keyword}': {e}")
            results.append({
                "title": keyword,
                "summary": "Failed to parse response.",
                "facts": ["Data unavailable", "Data unavailable", "Data unavailable"],
                "error": "JSON decode error"
            })
        except Exception as e:
            print(f"✗ Error generating info for '{keyword}': {str(e)}")
            results.append({
                "title": keyword,
                "summary": "Failed to generate information.",
                "facts": ["Data unavailable", "Data unavailable", "Data unavailable"],
                "error": str(e)
            })
    
    return results


def generate_info_internal(keyword: Union[str, List[str]]) -> List[Dict]:
    """
    Wrapper function for backward compatibility.
    Generates info for one or multiple keywords.
    """
    return generate_info_batch(keyword)

@llm_api.route('/api/generate_info', methods=['GET'])
def generate_info():
    """
    Public endpoint that wraps the internal function.
    """
    try:
        keyword = request.args.get('keyword')
        if not keyword:
            return jsonify({'error': 'Keyword parameter is required'}), 400

        data = generate_info_internal(keyword)
        return jsonify(data), 200

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({'error': str(e)}), 500