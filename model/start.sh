#!/bin/bash

source .env 2>/dev/null
OLLAMA_PORT=${OLLAMA_PORT:-11434}

ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama to start..."
until curl -s http://localhost:${OLLAMA_PORT}/api/tags > /dev/null; do
  sleep 1
done
echo "Ollama is ready."

# Download main model
if [ ! -f /models/gemma4.gguf ]; then
  echo "Downloading 'Gemma 4' model..."
  curl -L "https://huggingface.co/HauhauCS/Gemma4-26B-A4B-Uncensored-HauhauCS-Balanced/resolve/main/Gemma4-26B-A4B-Uncensored-HauhauCS-Balanced-Q3_K_P.gguf" -o /models/gemma4.gguf
  echo "Model 'Gemma 4' download complete."
fi

# # Download multimodal projector
# if [ ! -f /models/gemma4-mmproj.gguf ]; then
#   echo "Downloading 'Gemma 4 mmproj' model..."
#   curl -L "https://huggingface.co/HauhauCS/Gemma4-26B-A4B-Uncensored-HauhauCS-Balanced/resolve/main/mmproj-Gemma4-26B-A4B-Uncensored-HauhauCS-Balanced-f16.gguf" -o /models/gemma4-mmproj.gguf
#   echo "Model 'mmproj' download complete."
# fi

# Create model (picks up both files via Modelfile)
ollama create gemma4 -f /Modelfile

echo "Gemma 4 ready!"
wait $OLLAMA_PID