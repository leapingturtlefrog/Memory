#!/usr/bin/env python3
"""
AI Chat Interface for Screen Activity
Reads the most recent Gemini description and provides a chat interface to ask about screen activity
"""

import os
import re
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ActivityChatBot:
    def __init__(self):
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=api_key)
        
        # Use the correct model name based on research
        self.model = genai.GenerativeModel('gemini-2.5-flash-preview-05-20')
        
        # Load the most recent description
        self.context = self.load_most_recent_description()
        
        # Initialize Flask app
        self.app = Flask(__name__)
        self.setup_routes()
    
    def find_most_recent_description(self):
        """Find the most recent description file based on trailing number"""
        descriptions_dir = "gemini_descriptions"
        if not os.path.exists(descriptions_dir):
            raise FileNotFoundError(f"Directory {descriptions_dir} not found")
        
        # Get all description files
        files = [f for f in os.listdir(descriptions_dir) if f.startswith("descriptions_") and f.endswith(".md")]
        
        if not files:
            raise FileNotFoundError("No description files found")
        
        # Extract timestamps and find the most recent
        def extract_timestamp(filename):
            # Extract timestamp from filename like descriptions_20250531_194855.md
            match = re.search(r'descriptions_(\d{8}_\d{6})\.md', filename)
            if match:
                return match.group(1)
            return "00000000_000000"
        
        # Sort by timestamp (most recent first)
        files.sort(key=extract_timestamp, reverse=True)
        
        return os.path.join(descriptions_dir, files[0])
    
    def load_most_recent_description(self):
        """Load the content of the most recent description file"""
        try:
            filepath = self.find_most_recent_description()
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Loaded description from: {filepath}")
            return content
            
        except Exception as e:
            print(f"Error loading description: {e}")
            return "No screen activity context available."
    
    def chat_with_gemini(self, user_message):
        """Send message to Gemini with full context"""
        try:
            # Create the full prompt with context
            full_prompt = f"""
You are an AI assistant that can answer questions about screen activity and computer usage based on detailed descriptions.

CONTEXT - Screen Activity Descriptions:
{self.context}

USER QUESTION: {user_message}

Please answer the user's question based on the screen activity context provided above. Focus on:
- What applications were being used
- What tasks were being performed  
- What problems or issues were encountered
- Timeline of activities
- Technical details from the logs and code
- Any patterns or insights about the user's workflow

Provide a helpful, detailed response based on the available context.
"""
            
            # Generate response using Gemini
            response = self.model.generate_content(full_prompt)
            
            return response.text
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def index():
            return render_template('chat.html')
        
        @self.app.route('/chat', methods=['POST'])
        def chat():
            data = request.json
            user_message = data.get('message', '')
            
            if not user_message:
                return jsonify({'error': 'No message provided'}), 400
            
            # Get response from Gemini
            response = self.chat_with_gemini(user_message)
            
            return jsonify({
                'response': response,
                'timestamp': datetime.now().isoformat()
            })
        
        @self.app.route('/context')
        def get_context():
            """Get information about the loaded context"""
            filepath = self.find_most_recent_description()
            lines = self.context.split('\n')
            
            return jsonify({
                'file': os.path.basename(filepath),
                'lines': len(lines),
                'characters': len(self.context),
                'preview': self.context[:500] + "..." if len(self.context) > 500 else self.context
            })
    
    def run(self, debug=True, port=5000):
        """Run the Flask app"""
        print(f"Starting Activity Chat Bot...")
        print(f"Context loaded: {len(self.context)} characters")
        print(f"Server starting on http://localhost:{port}")
        self.app.run(debug=debug, port=port)

def main():
    try:
        # Create and run the chat bot
        bot = ActivityChatBot()
        bot.run()
        
    except Exception as e:
        print(f"Error starting application: {e}")
        print("\nMake sure you have:")
        print("1. GEMINI_API_KEY in your .env file")
        print("2. gemini_descriptions/ directory with description files")
        print("3. Required dependencies: pip install flask google-generativeai python-dotenv")

if __name__ == "__main__":
    main()
