#!/bin/bash
# Generate MCP wrapper libraries from calculator server

echo "🔧 Generating MCP wrapper libraries..."
echo ""

# Run the mcp-generate CLI tool
python -m src.cli mcp-servers.json --output servers

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ MCP wrappers generated successfully!"
    echo "📁 Check the servers/ directory for generated code"
    echo ""
    echo "Generated tools:"
    ls -1 servers/calculator/ 2>/dev/null | grep -v __pycache__ | grep -v __init__.py
else
    echo ""
    echo "❌ Failed to generate MCP wrappers"
    exit 1
fi
