# YouTube DLP MCP Server

🎬 **A Model Context Protocol (MCP) server that lets your AI interact with YouTube videos** - extract video information, subtitles, and top comments without downloading.

## ✨ Features

- 📹 **Extract Video Info** - Get comprehensive metadata (title, views, likes, description, etc.)
- 📝 **Extract Subtitles** - Download manual subtitles and auto-generated captions
- 💬 **Extract Comments** - Get top comments sorted by likes with creator badges
- 🌐 **Proxy Support** - Works with HTTP/HTTPS/SOCKS proxies
- 🚀 **Fast & Async** - Non-blocking operations using asyncio
- 🔧 **Easy Integration** - Standard MCP protocol for AI assistants

## 🚀 Quick Start

### Install with uvx (Recommended)

```bash
uvx run youtube-dlp-server
```

### Install with pip

```bash
pip install youtube-dlp-server
youtube-dlp-server
```

### Install from source

```bash
git clone <repository-url>
cd youtube-dlp-server
pip install -e .
python -m youtube_dlp_server
```

## 🛠️ Usage

### Available Tools

#### 1. **get-video-info**

Extract comprehensive video metadata:

```json
{
  "name": "get-video-info",
  "arguments": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  }
}
```

#### 2. **get-video-subtitles**

Extract subtitles and captions:

```json
{
  "name": "get-video-subtitles",
  "arguments": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "languages": ["en", "es"],
    "include_auto_captions": true
  }
}
```

#### 3. **get-top-comments**

Get top comments (max 20, default 10):

```json
{
  "name": "get-top-comments",
  "arguments": {
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "count": 10
  }
}
```

### Proxy Configuration

Set the `PROXY_URL` environment variable:

```bash
# HTTP/HTTPS proxy
export PROXY_URL="http://proxy.example.com:8080"

# SOCKS proxy with auth
export PROXY_URL="socks5://user:pass@127.0.0.1:1080/"

# Run with proxy
youtube-dlp-server
```

## 🧪 Testing

### With MCP Inspector

```bash
npx @modelcontextprotocol/inspector youtube-dlp-server
```

### Manual Testing

```bash
python -c "
import asyncio
from youtube_dlp_server.helper import extract_video_info
async def test():
    info = await extract_video_info('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
    print(f'✅ Video: {info[\"title\"]}')
asyncio.run(test())
"
```

## 📋 Requirements

- Python 3.11+
- yt-dlp for YouTube processing
- MCP framework for AI integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🔗 Links

- **Homepage**: [GitHub Repository](https://github.com/AgentX-ai/AgentX-mcp-servers)
- **Issues**: [Report Issues](https://github.com/AgentX-ai/AgentX-mcp-servers/issues)
- **MCP Documentation**: [Model Context Protocol](https://modelcontextprotocol.io)

---

**Made with ❤️ for the AI community**
