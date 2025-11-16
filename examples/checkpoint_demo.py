"""
Checkpoint Demo

This example demonstrates task checkpointing and resumption.
"""

import logging
from mcp_skill_framework import MCPApi

logging.basicConfig(level=logging.INFO)

# Initialize API
api = MCPApi()

# Register MCP server
api.add_mcp_server(
    name="filesystem",
    command="npx -y @modelcontextprotocol/server-filesystem /tmp"
)

# Generate APIs and start
api.generate_apis()
api.start()

try:
    # Create a checkpoint for a long-running task
    print("Creating checkpoint...")

    task_state = {
        "processed_files": ["file1.txt", "file2.txt"],
        "current_index": 2,
        "total_files": 10,
        "results": [{"name": "file1.txt", "size": 100}, {"name": "file2.txt", "size": 200}],
    }

    resume_code = """
from servers.filesystem.list_directory import execute as list_dir

# Continue processing from where we left off
remaining_files = ["file3.txt", "file4.txt", "file5.txt"]

for filename in remaining_files:
    print(f"Processing {filename}...")
    # Process file here
    processed_files.append(filename)
    current_index += 1

print(f"Processed {current_index}/{total_files} files")
return {"status": "completed", "processed": current_index}
"""

    api.create_checkpoint(
        task_id="file_processing_20251116",
        state=task_state,
        code=resume_code,
        description="Process all files in directory with progress tracking"
    )

    print("Checkpoint created successfully!")

    # List checkpoints
    print("\nAvailable checkpoints:")
    checkpoints = api.checkpoint_manager.list_checkpoints()
    for cp in checkpoints:
        print(f"  - {cp['task_id']}: {cp['description']}")

    # Resume from checkpoint
    print("\nResuming checkpoint...")
    result = api.resume_checkpoint("file_processing_20251116")
    print(f"Resume result: {result}")

finally:
    api.stop()

print("\nDone!")
