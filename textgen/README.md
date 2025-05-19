# Text Generation Module

This module provides text generation functionality using OpenAI's API for the BiolecturesFlask application.

## Features

1. **Universal Text Generation**: Generate text for various purposes using different prompt templates.
2. **Automatic SEO Description Updates**: Automatically updates lecture descriptions every 7 days for SEO optimization.
3. **API Endpoint**: Provides an API endpoint for text rewriting.

## How It Works

### Text Generation API

The module exposes an API endpoint at `/api/textgen/rewrite` that accepts POST requests with the following JSON structure:

```json
{
  "base_text": "Your text to rewrite",
  "task_type": "friendly" // or "seo" or other supported types
}
```

Response:

```json
{
  "result": "Generated text"
}
```

### Automatic Description Updates

The module includes a scheduler that runs every 7 days to update lecture descriptions for SEO optimization. The process:

1. Finds lectures that haven't been updated in the last 7 days
2. Generates new SEO-optimized descriptions using OpenAI
3. Updates the lecture records in the database

## Prompt Templates

The module supports different prompt templates for various text generation tasks:

- **friendly**: Rewrites text in a more friendly tone
- **seo**: Optimizes text for search engines while maintaining key information

## Adding New Prompt Templates

To add a new prompt template, update the `PROMPT_TEMPLATES` dictionary in `plugin.py`:

```python
PROMPT_TEMPLATES = {
    'friendly': "Перепиши этот текст более дружелюбно, сохрани смысл:\n\n{text}",
    'seo': "Перепиши этот текст для SEO оптимизации, сделай его уникальным, сохраняя ключевые слова и основной смысл. Добавь релевантные ключевые слова и улучши читаемость:\n\n{text}",
    'your_new_type': "Your prompt template here:\n\n{text}"
}
```

## Testing

You can test the description update functionality by running:

```
python test_textgen.py
```

This will trigger the update process immediately without waiting for the scheduler.

## Requirements

- OpenAI API key (set in .env file)
- APScheduler for scheduling tasks