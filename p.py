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
        """Find the most recent description file based on trailing timestamp"""
        descriptions_dir = "gemini_descriptions"
        if not os.path.exists(descriptions_dir):
            raise FileNotFoundError(f"Directory {descriptions_dir} not found")
        
        # Get all description files
        all_files = os.listdir(descriptions_dir)
        print(f"Found {len(all_files)} total files in {descriptions_dir}")
        
        # Filter for description files
        files = [f for f in all_files if f.startswith("descriptions_") and f.endswith(".md")]
        print(f"Found {len(files)} description files: {files}")
        
        if not files:
            raise FileNotFoundError("No description files found")
        
        # Extract timestamps and find the most recent
        def extract_timestamp(filename):
            # Extract timestamp from filename like descriptions_20250531_201602.md
            # Format: descriptions_YYYYMMDD_HHMMSS.md
            match = re.search(r'descriptions_(\d{8}_\d{6})\.md', filename)
            if match:
                timestamp = match.group(1)
                print(f"Extracted timestamp '{timestamp}' from file '{filename}'")
                return timestamp
            else:
                print(f"WARNING: Could not extract timestamp from file '{filename}'")
                return "00000000_000000"
        
        # Create list of (filename, timestamp) tuples for debugging
        file_timestamps = [(f, extract_timestamp(f)) for f in files]
        print("File timestamps:")
        for filename, timestamp in file_timestamps:
            print(f"  {filename} -> {timestamp}")
        
        # Sort by timestamp (most recent first)
        files.sort(key=extract_timestamp, reverse=True)
        
        most_recent = files[0]
        most_recent_timestamp = extract_timestamp(most_recent)
        
        print(f"Selected most recent file: {most_recent} (timestamp: {most_recent_timestamp})")
        
        # Parse and display the timestamp in a readable format
        try:
            # Parse timestamp: YYYYMMDD_HHMMSS
            date_part = most_recent_timestamp[:8]  # YYYYMMDD
            time_part = most_recent_timestamp[9:]  # HHMMSS
            
            year = date_part[:4]
            month = date_part[4:6]
            day = date_part[6:8]
            hour = time_part[:2]
            minute = time_part[2:4]
            second = time_part[4:6]
            
            readable_time = f"{year}-{month}-{day} {hour}:{minute}:{second}"
            print(f"Most recent file timestamp: {readable_time}")
            
        except Exception as e:
            print(f"Error parsing timestamp: {e}")
        
        return os.path.join(descriptions_dir, most_recent)
    
    def load_most_recent_description(self):
        """Load the content of the most recent description file"""
        try:
            filepath = self.find_most_recent_description()
            
            # Check file size
            file_size = os.path.getsize(filepath)
            print(f"Loading file: {filepath}")
            print(f"File size: {file_size:,} bytes")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"Successfully loaded {len(content):,} characters from: {os.path.basename(filepath)}")
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
            
            # Extract timestamp from filename for display
            filename = os.path.basename(filepath)
            timestamp_match = re.search(r'descriptions_(\d{8}_\d{6})\.md', filename)
            readable_timestamp = "Unknown"
            
            if timestamp_match:
                timestamp = timestamp_match.group(1)
                try:
                    date_part = timestamp[:8]
                    time_part = timestamp[9:]
                    year = date_part[:4]
                    month = date_part[4:6]
                    day = date_part[6:8]
                    hour = time_part[:2]
                    minute = time_part[2:4]
                    second = time_part[4:6]
                    readable_timestamp = f"{year}-{month}-{day} {hour}:{minute}:{second}"
                except:
                    pass
            
            return jsonify({
                'file': filename,
                'timestamp': readable_timestamp,
                'lines': len(lines),
                'characters': len(self.context),
                'preview': self.context[:500] + "..." if len(self.context) > 500 else self.context
            })
    
    def run(self, debug=True, port=5000):
        """Run the Flask app"""
        print(f"Starting Activity Chat Bot...")
        print(f"Context loaded: {len(self.context):,} characters")
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
