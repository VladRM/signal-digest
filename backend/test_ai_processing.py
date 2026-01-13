"""Test script for AI processing with video extraction."""
import asyncio
from app.database import SessionLocal
from app.services.ai.orchestrator import run_ai_processing
from app.models.run import Run
from sqlalchemy import text


async def test_ai_processing():
    """Test AI processing with the new video extraction workflow."""
    db = SessionLocal()

    try:
        # Check for unprocessed items
        result = db.execute(text("""
            SELECT ci.id, ci.title, ci.url, e.connector_type as connector_type
            FROM content_items ci
            JOIN endpoints e ON ci.endpoint_id = e.id
            LEFT JOIN ai_extractions ae ON ci.id = ae.content_item_id
            WHERE ae.id IS NULL
            ORDER BY ci.published_at DESC
            LIMIT 5
        """))

        items = result.fetchall()

        if not items:
            print("✓ No unprocessed items found")
            print("  To test, first run ingestion to get content items")
            return

        print(f"\n📊 Found {len(items)} unprocessed items:")
        for item in items:
            print(f"  - ID {item[0]}: {item[1][:50]}...")
            print(f"    Type: {item[3]}, URL: {item[2][:60]}...")

        print("\n🚀 Starting AI processing...")
        run = await run_ai_processing(db)

        print(f"\n✓ AI Processing completed!")
        print(f"  Run ID: {run.id}")
        print(f"  Status: {run.status.value}")
        print(f"  Stats: {run.stats_json}")

        # Check what extractions were created
        result = db.execute(text("""
            SELECT ae.id, ae.content_item_id, ae.prompt_name, ae.model_name
            FROM ai_extractions ae
            JOIN content_items ci ON ae.content_item_id = ci.id
            ORDER BY ae.created_at DESC
            LIMIT 5
        """))

        extractions = result.fetchall()
        print(f"\n📝 Recent extractions:")
        for ext in extractions:
            print(f"  - Extraction {ext[0]}: Item {ext[1]}, Prompt: {ext[2]}, Model: {ext[3]}")

        # Check video extractions specifically
        result = db.execute(text("""
            SELECT COUNT(*)
            FROM ai_extractions
            WHERE prompt_name = 'video_extraction'
        """))
        video_count = result.scalar()
        print(f"\n📹 Video extractions: {video_count}")

        # Check topic assignments
        result = db.execute(text("""
            SELECT COUNT(DISTINCT content_item_id)
            FROM topic_assignments
        """))
        classified_count = result.scalar()
        print(f"🏷️  Classified items: {classified_count}")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_ai_processing())
