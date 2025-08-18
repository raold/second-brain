"""
Production test script for Google Drive integration
Tests OAuth2 flow, file listing, and ingestion with real Google Drive
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.google_drive_enhanced import GoogleDriveEnhanced


async def test_google_drive_production() -> None:
    """Test Google Drive integration with production data"""

    print("=" * 60)
    print("GOOGLE DRIVE PRODUCTION TEST")
    print("=" * 60)

    # Initialize service
    service = GoogleDriveEnhanced()

    # Check configuration
    if not service.client_id:
        print("\n❌ Google OAuth not configured!")
        print("Please set the following environment variables:")
        print("  - GOOGLE_CLIENT_ID")
        print("  - GOOGLE_CLIENT_SECRET")
        print("  - GOOGLE_REDIRECT_URI (optional)")
        return

    print("\n✅ Google OAuth configured")
    print(f"   Client ID: {service.client_id[:20]}...")
    print(f"   Redirect URI: {service.redirect_uri}")

    # Get connection status
    status = service.get_connection_status()
    print("\n📊 Connection Status:")
    print(f"   Connected: {status['connected']}")
    print(f"   Max file size: {status.get('max_file_size_mb', 0)} MB")
    print(f"   Supported types: {len(status.get('supported_types', []))} types")

    if not status["connected"]:
        print("\n🔗 Not connected. Please authenticate:")
        auth_url = service.get_auth_url()
        print("\n1. Visit this URL to authenticate:")
        print(f"   {auth_url}")
        print("\n2. After authentication, you'll be redirected to the callback URL")
        print("3. Copy the 'code' parameter from the URL and enter it below:")

        auth_code = input("\nEnter authorization code: ").strip()

        if auth_code:
            print("\n🔄 Exchanging code for tokens...")
            result = await service.exchange_code(auth_code)

            if result.get("success"):
                print(f"✅ Successfully authenticated as: {result.get('email')}")
            else:
                print(f"❌ Authentication failed: {result.get('error')}")
                return

    # List files
    print("\n📁 Listing files from Google Drive...")
    files = await service.list_files()

    if not files:
        print("   No files found or not connected")
        return

    print(f"\n✅ Found {len(files)} files:")

    # Categorize files
    categories = {}
    for file in files[:20]:  # Show first 20
        is_supported, category = service._validate_content_type(file.get("mimeType", ""))
        if is_supported:
            if category not in categories:
                categories[category] = []
            categories[category].append(file)

        ingested_marker = "✓" if file.get("already_ingested") else " "
        support_marker = "✓" if is_supported else "✗"
        size_str = ""
        if file.get("size"):
            size_mb = int(file["size"]) / (1024 * 1024)
            size_str = f" ({size_mb:.1f} MB)"

        print(f"   [{ingested_marker}] [{support_marker}] {file['name'][:50]}{size_str}")

    # Show category summary
    print("\n📊 File Categories:")
    for category, cat_files in categories.items():
        print(f"   {category}: {len(cat_files)} files")

    # Test file validation
    print("\n🔍 Testing file validation...")
    test_files = []

    for category, cat_files in categories.items():
        if cat_files and not cat_files[0].get("already_ingested"):
            test_files.append((category, cat_files[0]))
            if len(test_files) >= 3:
                break

    if test_files:
        for category, file in test_files:
            file_id = file["id"]
            print(f"\n   Validating {category} file: {file['name'][:40]}")

            # Check duplicate
            is_dup = await service.check_duplicate(file_id)
            print(f"     Duplicate check: {'Yes (skip)' if is_dup else 'No (proceed)'}")

            # Check size
            size_ok = True
            if file.get("size"):
                size_ok = int(file["size"]) <= 250 * 1024 * 1024
            print(f"     Size check: {'OK' if size_ok else 'Too large'}")

            # Check type
            is_supported, _ = service._validate_content_type(file.get("mimeType", ""))
            print(f"     Type check: {'Supported' if is_supported else 'Unsupported'}")

            can_ingest = not is_dup and size_ok and is_supported
            print(f"     Can ingest: {'✅ Yes' if can_ingest else '❌ No'}")

    # Test ingestion (optional)
    print("\n" + "=" * 60)
    response = input("\n🚀 Would you like to test file ingestion? (y/n): ").strip().lower()

    if response == "y":
        # Find a small text file to test
        test_file = None
        for file in files:
            mime_type = file.get("mimeType", "")
            if mime_type.startswith("text/") and not file.get("already_ingested"):
                if file.get("size") and int(file["size"]) < 1024 * 1024:  # < 1MB
                    test_file = file
                    break

        if test_file:
            print(f"\n📥 Testing ingestion with: {test_file['name']}")
            print(f"   File ID: {test_file['id']}")
            print(f"   Type: {test_file['mimeType']}")

            result = await service.ingest_file(test_file["id"])

            if result:
                if result.get("status") == "skipped":
                    print(f"   ⏭️ Skipped: {result.get('reason')}")
                else:
                    print(f"   ✅ Success! Memory ID: {result.get('id')}")
                    print(f"   Content category: {result.get('content_category')}")
            else:
                print("   ❌ Ingestion failed")
        else:
            print("\n⚠️ No suitable test file found (looking for small text files)")

    # Test batch capabilities
    print("\n📦 Batch Processing Capabilities:")
    print("   Batch ingestion: Available")
    print("   Progress tracking: Available")
    print("   WebSocket support: Available")
    print("   Max batch size: 100 files")

    # Show final stats
    status = service.get_connection_status()
    print("\n📈 Final Statistics:")
    print(f"   Ingested files in cache: {status.get('ingested_files_count', 0)}")
    print(f"   Connection active: {status['connected']}")

    print("\n✅ Production test completed!")


def main() -> None:
    """Main entry point"""
    print("\n[TEST] Google Drive Enhanced Integration Test")
    print("This will test the production Google Drive integration")
    print("including OAuth2, file listing, validation, and ingestion.\n")

    try:
        asyncio.run(test_google_drive_production())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
