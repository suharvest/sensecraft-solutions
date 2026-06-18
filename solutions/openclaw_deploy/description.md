## What This Solution Does

Want to use AI chatbots on WeChat, Telegram, or Discord — but don't want to juggle multiple integrations or worry about data privacy? OpenClaw connects 20+ messaging apps to any AI model through one simple gateway, running entirely on your own reComputer device.

## Core Value

| Benefit | Details |
|---------|---------|
| One gateway, 20+ platforms | WeChat, Telegram, Discord, Slack, DingTalk, Feishu, and more — manage all from one place |
| Switch AI models freely | Use OpenAI, DeepSeek, or any compatible AI service — switch anytime without reconfiguration |
| Your data stays with you | Everything runs on your own device — no conversations sent to third-party services |
| Optional local AI | Use device GPU to run AI models locally — fully offline conversations with zero privacy concerns |

## Use Cases

| Scenario | How It Works |
|----------|-------------|
| Personal AI assistant | Connect your WeChat or Telegram to ChatGPT/DeepSeek — chat with AI right in your messaging app |
| Team chatbot | Set up a shared AI assistant in your Slack or Discord workspace for the whole team |
| Privacy-first AI | Run AI models locally on your device so conversations never leave your network |
| Edge AI on Jetson | Deploy on reComputer Jetson for GPU-accelerated local AI with messaging integration |

## What You Need

### Inputs and Outputs

- Input: Chat messages (WeChat, Telegram, Discord, Slack, etc. — 20+ platforms)
- Output: AI responses sent back to the corresponding chat platform

### Configuration

- Enter the target AI model's API key or local model address
- Enter bot token / webhook for each messaging platform

## Deployment Comparison

| Option | AI Mode | Core Device | Best For |
|--------|---------|-------------|----------|
| **OpenClaw AI Compute Gateway** | Local AI model | reComputer Jetson | Privacy-first, offline environments, high concurrent chats |
| **OpenClaw Gateway** | Cloud AI providers | reComputer R1100 / R2000 | Lightweight setup, stable network, cost-conscious |

### Performance and Cost Reference

- **Local AI model (Jetson)**: 2B model 20+ tokens/sec; 4B/7B slower (limited by device compute); no token fees
- **Cloud AI service (R1100/R2000)**: Response speed depends on cloud service; pay per LLM API call
