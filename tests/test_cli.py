"""
Tests for CLI code generation tool.

Tests the mcp-generate command and generate_servers() function that are the primary developer workflow entry points.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import argparse

from src.cli import generate_servers, generate_command, main


class TestGenerateServersFunction:
    """Test the generate_servers() Python API."""

    def test_generate_servers_with_single_server(self):
        """Test generating from single server configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers = [{"name": "test_server", "command": "echo test"}]

            # Mock the API to prevent actual MCP server spawning
            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                generate_servers(servers=servers, servers_dir=tmpdir, verbose=False)

                # Verify API was initialized
                mock_api_class.assert_called_once()
                call_args = mock_api_class.call_args[1]
                assert call_args["servers_dir"] == tmpdir

                # Verify server was added
                mock_api.add_mcp_server.assert_called_once_with(
                    name="test_server", command="echo test"
                )

                # Verify code generation was called
                mock_api.generate_libraries.assert_called_once()

    def test_generate_servers_with_multiple_servers(self):
        """Test generating from multiple server configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers = [
                {"name": "server1", "command": "echo server1"},
                {"name": "server2", "command": "echo server2"},
                {"name": "server3", "command": "echo server3"},
            ]

            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                generate_servers(servers=servers, servers_dir=tmpdir, verbose=False)

                # Verify all servers were added
                assert mock_api.add_mcp_server.call_count == 3
                calls = mock_api.add_mcp_server.call_args_list

                assert calls[0][1] == {"name": "server1", "command": "echo server1"}
                assert calls[1][1] == {"name": "server2", "command": "echo server2"}
                assert calls[2][1] == {"name": "server3", "command": "echo server3"}

    def test_generate_servers_with_invalid_config(self):
        """Test handling of invalid server configurations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers = [
                {"name": "valid_server", "command": "echo valid"},
                {"name": "missing_command"},  # Invalid - missing command
                {"command": "echo missing-name"},  # Invalid - missing name
            ]

            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                # Should not raise - invalid configs are skipped
                generate_servers(servers=servers, servers_dir=tmpdir, verbose=False)

                # Only valid server should be added
                mock_api.add_mcp_server.assert_called_once_with(
                    name="valid_server", command="echo valid"
                )

    def test_generate_servers_verbose_mode(self, capsys):
        """Test verbose output mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers = [{"name": "test", "command": "echo test"}]

            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                generate_servers(servers=servers, servers_dir=tmpdir, verbose=True)

                captured = capsys.readouterr()
                assert "MCP Server Wrapper Generator" in captured.out
                assert "Registered: test" in captured.out
                assert "Code generation complete" in captured.out

    def test_generate_servers_quiet_mode(self, capsys):
        """Test quiet mode suppresses output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            servers = [{"name": "test", "command": "echo test"}]

            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                generate_servers(servers=servers, servers_dir=tmpdir, verbose=False)

                captured = capsys.readouterr()
                assert captured.out == ""

    def test_generate_servers_custom_output_dir(self):
        """Test custom output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_dir = f"{tmpdir}/custom-servers"
            servers = [{"name": "test", "command": "echo test"}]

            with patch("src.cli.MCPApi") as mock_api_class:
                mock_api = MagicMock()
                mock_api_class.return_value = mock_api

                generate_servers(servers=servers, servers_dir=custom_dir, verbose=False)

                call_args = mock_api_class.call_args[1]
                assert call_args["servers_dir"] == custom_dir


class TestGenerateCommand:
    """Test the generate_command() CLI handler."""

    def test_generate_command_with_valid_config(self):
        """Test generate command with valid config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file
            config_path = Path(tmpdir) / "test-config.json"
            config = {
                "servers": [{"name": "test_server", "command": "echo test"}]
            }
            config_path.write_text(json.dumps(config))

            # Create args namespace
            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            with patch("src.cli.generate_servers") as mock_generate:
                result = generate_command(args)

                assert result == 0
                mock_generate.assert_called_once()
                call_args = mock_generate.call_args[1]
                assert call_args["servers"] == config["servers"]
                assert call_args["servers_dir"] == "servers"
                assert call_args["verbose"] is True  # Not quiet

    def test_generate_command_with_missing_config(self, capsys):
        """Test error handling when config file is missing."""
        args = argparse.Namespace(
            config="/nonexistent/config.json", output="servers", quiet=False, verbose=False
        )

        result = generate_command(args)

        assert result == 1
        captured = capsys.readouterr()
        assert "Error: Config file not found" in captured.err

    def test_generate_command_with_invalid_json(self):
        """Test error handling for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "invalid.json"
            config_path.write_text("{ invalid json")

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            result = generate_command(args)

            assert result == 1

    def test_generate_command_with_empty_servers(self, capsys):
        """Test error handling for config with no servers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "empty.json"
            config = {"servers": []}
            config_path.write_text(json.dumps(config))

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            result = generate_command(args)

            assert result == 1
            captured = capsys.readouterr()
            assert "No servers configured" in captured.err

    def test_generate_command_with_quiet_flag(self):
        """Test quiet flag is passed through."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=True, verbose=False
            )

            with patch("src.cli.generate_servers") as mock_generate:
                generate_command(args)

                call_args = mock_generate.call_args[1]
                assert call_args["verbose"] is False  # Quiet mode

    def test_generate_command_with_custom_output(self):
        """Test custom output directory flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            args = argparse.Namespace(
                config=str(config_path),
                output="custom-dir",
                quiet=False,
                verbose=False,
            )

            with patch("src.cli.generate_servers") as mock_generate:
                generate_command(args)

                call_args = mock_generate.call_args[1]
                assert call_args["servers_dir"] == "custom-dir"

    def test_generate_command_handles_exceptions(self):
        """Test exception handling during generation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            with patch("src.cli.generate_servers") as mock_generate:
                mock_generate.side_effect = Exception("Test error")

                result = generate_command(args)

                assert result == 1


class TestCLIMain:
    """Test the main() CLI entry point."""

    def test_main_parses_arguments(self):
        """Test that main() parses arguments correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            test_args = [str(config_path)]

            with patch("sys.argv", ["mcp-generate"] + test_args):
                with patch("src.cli.generate_command") as mock_cmd:
                    mock_cmd.return_value = 0

                    result = main()

                    assert result == 0
                    mock_cmd.assert_called_once()

                    # Verify args were parsed correctly
                    args = mock_cmd.call_args[0][0]
                    assert args.config == str(config_path)
                    assert args.output == "servers"  # Default

    def test_main_with_output_flag(self):
        """Test main() with --output flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            test_args = [str(config_path), "--output", "my-servers"]

            with patch("sys.argv", ["mcp-generate"] + test_args):
                with patch("src.cli.generate_command") as mock_cmd:
                    mock_cmd.return_value = 0

                    main()

                    args = mock_cmd.call_args[0][0]
                    assert args.output == "my-servers"

    def test_main_with_quiet_flag(self):
        """Test main() with --quiet flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            test_args = [str(config_path), "--quiet"]

            with patch("sys.argv", ["mcp-generate"] + test_args):
                with patch("src.cli.generate_command") as mock_cmd:
                    mock_cmd.return_value = 0

                    main()

                    args = mock_cmd.call_args[0][0]
                    assert args.quiet is True

    def test_main_with_verbose_flag(self):
        """Test main() with --verbose flag."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"servers": [{"name": "test", "command": "echo test"}]}
            config_path.write_text(json.dumps(config))

            test_args = [str(config_path), "--verbose"]

            with patch("sys.argv", ["mcp-generate"] + test_args):
                with patch("src.cli.generate_command") as mock_cmd:
                    mock_cmd.return_value = 0

                    main()

                    args = mock_cmd.call_args[0][0]
                    assert args.verbose is True


class TestConfigFileFormats:
    """Test various config file formats."""

    def test_config_with_all_fields(self):
        """Test config with all possible fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {
                "servers": [
                    {
                        "name": "filesystem",
                        "command": "npx -y @modelcontextprotocol/server-filesystem /tmp",
                    },
                    {
                        "name": "github",
                        "command": "npx -y @modelcontextprotocol/server-github",
                    },
                ]
            }
            config_path.write_text(json.dumps(config, indent=2))

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            with patch("src.cli.generate_servers") as mock_generate:
                result = generate_command(args)

                assert result == 0
                call_args = mock_generate.call_args[1]
                assert len(call_args["servers"]) == 2

    def test_config_missing_servers_key(self):
        """Test config file without 'servers' key."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config = {"other_key": "value"}
            config_path.write_text(json.dumps(config))

            args = argparse.Namespace(
                config=str(config_path), output="servers", quiet=False, verbose=False
            )

            result = generate_command(args)

            assert result == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
