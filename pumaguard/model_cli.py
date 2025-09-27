"""
CLI commands for managing models.
"""

import argparse
import logging

from pumaguard.model_downloader import (
    clear_model_cache,
    ensure_model_available,
    get_models_directory,
    list_available_models,
)

logger = logging.getLogger('PumaGuard')

def main():
    """
    Main entry point.
    """
    parser = argparse.ArgumentParser(description="PumaGuard Model Management")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Download command
    download_parser = subparsers.add_parser(
        "download", help="Download a specific model"
    )
    download_parser.add_argument("model", help="Model name to download")

    # List command
    subparsers.add_parser("list", help="List available models")

    # Clear command
    subparsers.add_parser("clear", help="Clear model cache")

    # Info command
    subparsers.add_parser("info", help="Show model cache location and size")

    args = parser.parse_args()

    if args.command == "download":
        try:
            path = ensure_model_available(args.model)
            print(f"Model downloaded to: {path}")
        except (ValueError, RuntimeError) as e:
            print(f"Error downloading model: {e}")
        except Exception:
            logger.error('uncaught exception')
            raise

    elif args.command == "list":
        models = list_available_models()
        print("Available models:")
        for name, url in models.items():
            print(f"  {name}: {url}")

    elif args.command == "clear":
        clear_model_cache()
        print("Model cache cleared")

    elif args.command == "info":
        models_dir = get_models_directory()
        print(f"Models directory: {models_dir}")
        if models_dir.exists():
            total_size = sum(
                f.stat().st_size for f in models_dir.rglob("*") if f.is_file()
            )
            print(f"Cache size: {total_size / (1024*1024):.1f} MB")
        else:
            print("No models cached")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
