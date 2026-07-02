import os
import json

log_path = "/home/chakradhar/.gemini/antigravity-cli/brain/0e591717-6dba-41d4-9167-895a45f13e06/.system_generated/logs/transcript_full.jsonl"
output_path = "/home/chakradhar/Projects/Data/ChatKgp/chat.md"

if not os.path.exists(log_path):
    print(f"Error: Transcript log file not found at: {log_path}")
    exit(1)

chat_history = []

print("Parsing conversation transcripts...")
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        if not line.strip():
            continue
        try:
            step = json.loads(line)
            step_type = step.get("type")
            source = step.get("source")
            content = step.get("content", "")
            
            # Extract user prompts
            if step_type == "USER_INPUT" and source == "USER_EXPLICIT":
                # Avoid logging the checkpoint summary metadata message as-is to keep history clean
                if "{{ CHECKPOINT" in content:
                    # Clean checkpoint wrapping, extract the core user message if any, 
                    # or summarize that it is a session checkpoint restore.
                    chat_history.append({
                        "role": "SYSTEM_NOTE",
                        "content": "*[Session Context Restored via Checkpoint]*"
                    })
                else:
                    chat_history.append({
                        "role": "USER",
                        "content": content
                    })
            
            # Extract assistant responses
            elif step_type == "PLANNER_RESPONSE" and source == "MODEL":
                if content.strip():
                    chat_history.append({
                        "role": "ASSISTANT",
                        "content": content
                    })
        except Exception as e:
            print(f"Warning: Failed to parse step: {e}")

# Build Markdown content
md_lines = [
    "# KGP Insight: Conversation Log\n",
    "This document preserves the complete chronological history of the pair-programming session from start to end.\n",
    "---"
]

for entry in chat_history:
    role = entry["role"]
    content = entry["content"].strip()
    
    if role == "USER":
        md_lines.append(f"\n### 👤 USER\n\n{content}\n")
        md_lines.append("\n---")
    elif role == "ASSISTANT":
        md_lines.append(f"\n### 🤖 KGP INSIGHT ASSISTANT\n\n{content}\n")
        md_lines.append("\n---")
    elif role == "SYSTEM_NOTE":
        md_lines.append(f"\n> **Note:** {content}\n")
        md_lines.append("\n---")

# Save file
with open(output_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines))

print(f"✔ Successfully saved complete chat log to: {output_path}")
