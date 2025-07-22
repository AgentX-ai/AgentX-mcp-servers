# AgentX MCP Servers Collection

[![Documentation](https://img.shields.io/badge/Documentation-📖-green)](https://docs.agentx.so/)
[![Website](https://img.shields.io/badge/Website-🌐-purple)](https://www.agentx.so/mcp)
[![Discord](https://img.shields.io/badge/Discord-Join-7289DA?logo=discord&logoColor=white)](https://discord.gg/dJkAbUq9rU)
[![YouTube Demo](https://img.shields.io/badge/Demo-YouTube-red)](https://www.youtube.com/@AgentX-2023)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

🤖 **AgentX makes it effortless to connect to production-ready MCP servers, empowering builders to create powerful AI agents with minimal setup.** Get your AI agents talking to the world's services in minutes, not months.

## 🗂️ Available MCP Servers

### [YouTube DLP Server](https://github.com/AgentX-ai/youtube-dlp-server)

**Extract video information, subtitles, and comments from YouTube**

### 📈 [Yahoo Finance Server](https://github.com/AgentX-ai/yahoo-finance-server)

**Get real-time stock, marco eco, market sentiment, financial news, etc from Yahoo Finance**

### 📓 [Notion MCP Server](https://github.com/AgentX-ai/notion-mcp-server)

**Connect and let your Agent, search, create, write, modify your notion content**

### [Apollo MCP Server](https://github.com/AgentX-ai/apollo-io-mcp-server)

**Let your AI agent handle lead generation and enrichment**

### [Mailchimp MCP Server](https://github.com/AgentX-ai/mailchimp-mcp)

**Read only Mailchimp MCP Server. Allows your AI Agent to read your campagin data.**

### 🔄 More Servers Coming Soon...

---

## 🎯 What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that enables AI models to securely access external tools, data sources, and services. Think of it as a universal API that lets your AI agents interact with databases, web services, file systems, and more.

## ⚡ Why AgentX MCP Servers?

- 🚀 **Production-Ready** - Battle-tested servers used by thousands of developers
- 🔧 **Plug & Play** - Install with one command, zero configuration required
- 🌍 **Universal Compatibility** - Works with Claude, GPT, and any MCP-compatible AI
- 🛡️ **Enterprise Grade** - Built with security, reliability, and performance in mind
- 📦 **Growing Ecosystem** - New integrations added regularly based on community needs

We're actively developing MCP servers.

_Want a specific integration? [Request it here](https://github.com/AgentX-ai/AgentX-mcp-servers/issues/new)!_

## 🧪 Testing Your Setup

Use the MCP Inspector to test any server:

```bash
# Install MCP Inspector
npm install -g @modelcontextprotocol/inspector

# Test a server
npx @modelcontextprotocol/inspector uvx run youtube-dlp-server
```

## 🏗️ For Developers

### Creating Your Own MCP Server

Each `python` server in this collection follows our proven template:

```
your_server/
├── src/your_server/
│   ├── __init__.py
│   ├── __main__.py      # Entry point
│   ├── server.py        # MCP server logic
│   └── helper.py        # Business logic
├── pyproject.toml       # Dependencies & metadata
├── README.md           # Server-specific docs
└── LICENSE             # MIT License
```

## 🤝 Contributing

We welcome contributions! Here's how to help:

1. **⭐ Star this repo** - Show your support
2. **🐛 Report bugs** - [Open an issue](https://github.com/AgentX-ai/AgentX-mcp-servers/issues)
3. **💡 Request features** - Tell us what integrations you need
4. **🔧 Submit PRs** - Add new servers or improve existing ones
5. **📖 Improve docs** - Help others get started faster

### Development Workflow

```bash
# 1. Fork & clone
git clone https://github.com/yourusername/AgentX-mcp-servers.git

# 2. Create feature branch
git checkout -b feature/awesome-server

# 3. Make changes & test
cd your_new_server
npm run test

# 4. Submit PR
git push origin feature/awesome-server
```

## 📞 Support & Community

- 💬 **Discord**: [Join our community](https://discord.gg/dJkAbUq9rU)
- 📧 **Email**: contact@agentx.so
- 🐦 **Twitter**: [@AgentX_AI](https://x.com/AgentX_AI)
- 📖 **Docs**: [docs.agentx.so](https://docs.agentx.so)
- 🎥 **YouTube**: [Tutorials & Demos](https://www.youtube.com/@AgentX-2023)

## 📄 License

All servers are released under the [MIT License](LICENSE). Free for commercial and personal use.

---

<div align="center">

**🚀 Ready to supercharge your AI agents?**

[Get Started](https://docs.agentx.so) • [Join Discord](https://discord.gg/dJkAbUq9rU) • [Watch Demo](https://www.youtube.com/@AgentX-2023)

</div>
