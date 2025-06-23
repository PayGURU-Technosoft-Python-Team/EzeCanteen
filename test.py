import os
import openai

# Set your API key here (you can also set this as an environment variable)
openai.api_key = "sk-live-4nT8gV7sAj3F9wQl0GvRXsT9vB2MEyDqXpN2pIq7X9cWz4ZK"  # Replace with your actual key if not using env variable

# Simple prompt to send to ChatGPT
prompt = "Explain what an API key is in simple terms."

# Make a call to OpenAI Chat API (GPT-4 or GPT-3.5)
response = openai.ChatCompletion.create(
    model="gpt-4",  # You can change this to "gpt-3.5-turbo" if not on Plus/Pro
    messages=[
        {"role": "user", "content": prompt}
    ],
    temperature=0.7,
)

# Print the result
print(response.choices[0].message['content'])
