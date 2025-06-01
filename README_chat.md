# 🤖 AI Activity Assistant

A beautiful chat interface that lets you ask questions about your screen activity and computer usage. The assistant uses Google's Gemini AI to analyze detailed screen descriptions and provide insights about your workflow.

## ✨ Features

- **Smart Context Loading**: Automatically reads the most recent screen activity descriptions
- **Beautiful Chat Interface**: Modern, responsive design with gradient backgrounds and smooth animations
- **Real-time AI Responses**: Uses Gemini 2.5 Flash for fast, accurate responses
- **Context Awareness**: Full access to your screen activity timeline, logs, and technical details
- **Mobile Friendly**: Responsive design that works on all devices

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up API Key

1. Get your Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Copy the example environment file:
   ```bash
   cp env_example.txt .env
   ```
3. Edit `.env` and add your API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### 3. Run the Application

```bash
python p.py
```

The application will start at `http://localhost:5000`

## 🎯 What You Can Ask

The AI assistant has access to your complete screen activity context and can answer questions like:

### Applications & Tasks
- "What applications was I using in the last session?"
- "What was I working on when I encountered errors?"
- "Show me the timeline of my coding session"

### Technical Issues
- "What errors did I encounter and how were they resolved?"
- "What API endpoints was I testing?"
- "What were the main problems with the Gemini integration?"

### Workflow Analysis
- "How much time did I spend debugging?"
- "What files did I modify during the session?"
- "What was the main focus of my development work?"

### Code & Logs
- "What error messages appeared in the console?"
- "What models was I experimenting with?"
- "What configuration changes did I make?"

## 🏗️ Architecture

- **Backend**: Flask web server with Gemini AI integration
- **Frontend**: Modern HTML/CSS/JavaScript chat interface
- **Context**: Automatically loads from `gemini_descriptions/` directory
- **Model**: Uses `gemini-2.5-flash-preview-05-20` for optimal performance

## 📁 File Structure

```
├── p.py                    # Main Flask application
├── templates/
│   └── chat.html          # Beautiful chat interface
├── gemini_descriptions/   # Screen activity descriptions
├── requirements.txt       # Python dependencies
├── env_example.txt       # Environment variables template
└── README_chat.md        # This file
```

## 🔧 Configuration

The application automatically:
- Finds the most recent description file (highest timestamp)
- Loads the complete context into memory
- Configures Gemini API with the latest model
- Provides real-time chat functionality

## 🎨 UI Features

- **Gradient Backgrounds**: Beautiful purple-blue gradients
- **Smooth Animations**: Slide-in effects for messages
- **Typing Indicators**: Visual feedback during AI responses
- **Context Modal**: View loaded context information
- **Auto-resize Input**: Text area expands as you type
- **Mobile Responsive**: Works perfectly on phones and tablets

## 🔗 API Endpoints

- `GET /` - Main chat interface
- `POST /chat` - Send message to AI assistant
- `GET /context` - Get information about loaded context

## 🛠️ Troubleshooting

### Common Issues

1. **"GEMINI_API_KEY not found"**
   - Make sure you created the `.env` file
   - Verify your API key is correct

2. **"No description files found"**
   - Ensure `gemini_descriptions/` directory exists
   - Check that description files follow the naming pattern

3. **Connection errors**
   - Verify internet connection
   - Check if API key has proper permissions

### Getting Help

If you encounter issues:
1. Check the console output for error messages
2. Verify all dependencies are installed
3. Ensure your API key is valid and has quota available

## 🚀 Next Steps

Try asking the AI assistant about:
- Recent debugging sessions
- Code changes and modifications
- Error patterns and solutions
- Workflow improvements
- Technical insights from your activity

Enjoy exploring your digital activity with AI assistance! 🎉 