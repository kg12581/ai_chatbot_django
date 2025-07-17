# AI Chatbot with Django and LangGraph

A modern AI chatbot built with Django, LangGraph, and LangChain that provides a web-based chat interface with real-time AI responses and tool integration.

## 🚀 Features

- **Modern Web UI**: Clean, responsive chat interface with markdown rendering
- **AI-Powered Responses**: Uses Google Gemini and Groq LLMs with fallback support
- **Tool Integration**: Built-in web search capabilities using Tavily
- **Conversation Memory**: Maintains chat history for contextual conversations
- **Real-time Chat**: WebSocket-like experience with loading indicators
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

## 📁 Project Structure

```
ai_chatbot_django/
├── chatbot.py                 # Core LangGraph chatbot logic
├── manage.py                  # Django management script
├── Pipfile                    # Python dependencies (Pipenv)
├── Pipfile.lock              # Locked dependencies
├── .env                      # Environment variables (create this)
├── templates/
│   └── index.html            # Chat interface HTML/CSS/JS
├── djangoapp/
│   ├── views.py              # Django views (API endpoints)
│   ├── models.py             # Django models
│   ├── admin.py              # Django admin
│   └── migrations/           # Database migrations
├── djangoproj/
│   ├── settings.py           # Django settings
│   ├── urls.py               # URL routing
│   ├── wsgi.py               # WSGI configuration
│   └── asgi.py               # ASGI configuration
├── using_api_endpoint.py     # Example API client script
├── chatbot.ipynb             # Jupyter notebook for testing
└── db.sqlite3                # SQLite database
```

## 🛠️ Installation Guide

### Prerequisites

- Python 3.12 or higher
- Pipenv (for dependency management)
- API keys for:
  - Google Gemini AI
  - Groq
  - Tavily Search

### Step 1: Clone the Repository

```bash
git clone https://github.com/kg12581/ai_chatbot_django.git
cd ai_chatbot_django
```

### Step 2: Install Dependencies

```bash
# Install Pipenv if you don't have it
pip install pipenv

# Install project dependencies
pipenv install
```

### Step 3: Set Up Environment Variables

Create a `.env` file in the project root:

```bash
# Create .env file
touch .env
```

Add your API keys to the `.env` file:

```env
# Google Gemini AI
GOOGLE_API_KEY=your_google_api_key_here

# Groq
GROQ_API_KEY=your_groq_api_key_here

# Tavily Search
TAVILY_API_KEY=your_tavily_api_key_here
```

### Step 4: Run Database Migrations

```bash
pipenv run python manage.py migrate
```

### Step 5: Start the Development Server

```bash
pipenv run python manage.py runserver
```

The application will be available at `http://localhost:8000`

## 🔧 Configuration

### API Keys Setup

1. **Google Gemini AI**: Get your API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **Groq**: Get your API key from [Groq Console](https://console.groq.com/)
3. **Tavily**: Get your API key from [Tavily](https://tavily.com/)

### Customizing the Chatbot

#### Changing LLM Models

Modify the LLM configuration in `chatbot.py`:

```python
# Change the primary model
llm_with_fallbacks = init_chat_model("your_model_name").with_fallbacks(
    [init_chat_model("fallback_model_name")]
)
```

## 🎯 Usage

### Web Interface

1. Open your browser and navigate to `http://localhost:8000`
2. Start chatting with the AI assistant
3. The chatbot will automatically use web search when needed

### API Usage

You can also use the chatbot programmatically:

```python
import requests

url = "http://localhost:8000/api/chatbot/"
data = {
    "messages": [],
    "query": "What is the latest news about AI?"
}

response = requests.post(url, json=data)
result = response.json()
print(result["messages"][-1]["content"])
```

### Example Script

Use the provided `using_api_endpoint.py` for testing:

```bash
pipenv run python using_api_endpoint.py
```

## 🏗️ Architecture

### Backend Components

- **Django**: Web framework for API endpoints and serving the UI
- **LangGraph**: Orchestrates the conversation flow and tool usage
- **LangChain**: Provides LLM integration and tool bindings
- **Tavily**: Web search tool for real-time information

### Frontend Components

- **HTML/CSS/JavaScript**: Modern, responsive chat interface
- **Marked.js**: Markdown rendering for AI responses
- **Real-time Updates**: Dynamic message display with loading states

### Data Flow

1. User sends message via web interface
2. Django view processes the request
3. LangGraph orchestrates the conversation
4. LLM generates response (with tool usage if needed)
5. Response is serialized and sent back to frontend
6. Frontend displays the response with markdown rendering

## 🔍 Troubleshooting

### Common Issues

1. **API Key Errors**: Ensure all API keys are correctly set in `.env`
2. **Import Errors**: Make sure all dependencies are installed with `pipenv install`
3. **Port Conflicts**: Change the port if 8000 is in use: `python manage.py runserver 8001`

### Debug Mode

Enable debug logging by adding print statements in `chatbot.py`:

```python
def get_chatbot_response(messages: list):
    print(f"Input messages: {messages}")
    result = graph.invoke({"messages": messages})
    print(f"Graph result: {result}")
    return result
```

## 📦 Dependencies

### Core Dependencies

- `django`: Web framework
- `langgraph`: Conversation orchestration
- `langchain`: LLM integration
- `langchain-tavily`: Web search tool
- `langchain-groq`: Groq LLM integration
- `langchain-google-genai`: Google Gemini integration
- `python-dotenv`: Environment variable management

### Development Dependencies

- `ipykernel`: Jupyter notebook support
- `requests`: HTTP client for API testing

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 🙏 Acknowledgments

- [LangChain](https://langchain.com/) for the LLM framework
- [LangGraph](https://langchain.com/langgraph) for conversation orchestration
- [Django](https://djangoproject.com/) for the web framework
- [Tavily](https://tavily.com/) for web search capabilities
