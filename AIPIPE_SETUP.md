# AIPipe Setup Guide

This guide shows you how to use AIPipe with the SQL Query Debugger baseline script.

## Why Use AIPipe?

✅ **No credit card required** - Free tier available  
✅ **Budget limits** - Control your spending  
✅ **Usage tracking** - See your API usage  
✅ **Multiple providers** - Access OpenAI, OpenRouter, Gemini  
✅ **Simple setup** - Just one token for everything  

## Setup Steps

### 1. Get Your AIPipe Token

1. Go to **[aipipe.org/login](https://aipipe.org/login)**
2. Click "Sign in with Google"
3. Copy your **AI Pipe Token**

### 2. Configure Your Environment

Edit your `.env` file in the `sql-query-debugger` folder:

```env
# Paste your AIPipe token here
OPENAI_API_KEY=your-aipipe-token-here

# Point to AIPipe's OpenAI-compatible endpoint
OPENAI_BASE_URL=https://aipipe.org/openai/v1

# Choose your model (optional, default: gpt-4o-mini)
OPENAI_MODEL=gpt-4o-mini
```

### 3. Run the Baseline Script

```bash
cd sql-query-debugger
python baseline.py
```

## Available Models

AIPipe supports all OpenAI models through the `/openai/v1` endpoint:

- `gpt-4o-mini` (recommended - cheap and fast)
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-3.5-turbo`

You can also use OpenRouter models via `https://aipipe.org/openrouter/v1`:

```env
OPENAI_BASE_URL=https://aipipe.org/openrouter/v1
OPENAI_MODEL=openai/gpt-4o-mini
```

## Check Your Usage

Visit **[aipipe.org/login](https://aipipe.org/login)** to see:
- Your current usage
- Daily cost breakdown
- Budget limits

## Troubleshooting

### "Unauthorized" Error
- Make sure you copied the full token from aipipe.org/login
- Check that `OPENAI_BASE_URL` is set correctly

### "Model not found" Error
- For OpenAI endpoint: use `gpt-4o-mini` (not `openai/gpt-4o-mini`)
- For OpenRouter endpoint: use `openai/gpt-4o-mini` (with provider prefix)

### Rate Limits
- AIPipe has rate limits to prevent abuse
- If you hit limits, wait a few seconds and try again

## Using Your Own OpenAI Key

If you have OpenAI credits, you can still use your own key:

```env
# Use your OpenAI key directly
OPENAI_API_KEY=sk-your-openai-key-here

# Remove or comment out the base URL
# OPENAI_BASE_URL=
```

AIPipe will detect the `sk-` prefix and route directly to OpenAI.

## More Information

- **AIPipe Documentation**: [https://aipipe.org/](https://aipipe.org/)
- **Playground**: [https://aipipe.org/playground](https://aipipe.org/playground)
- **GitHub**: [https://github.com/sanand0/aipipe](https://github.com/sanand0/aipipe)
