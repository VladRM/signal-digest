"""Test script for topic brief hierarchical batching."""
import asyncio
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models.topic import Topic
from app.models.content_item import ContentItem
from app.models.brief import Brief
from app.services.ai.topic_brief_generator import TopicBriefGenerator
from sqlalchemy import text


async def test_topic_brief_batching():
    """Test topic brief generation with hierarchical batching."""
    db = SessionLocal()

    try:
        # Get first enabled topic
        topic = db.query(Topic).filter(Topic.enabled == True).first()

        if not topic:
            print("❌ No enabled topics found. Please create a topic first.")
            return

        print(f"\n📋 Testing topic brief for: {topic.name}")
        print(f"   Description: {topic.description or 'N/A'}")

        # Get content items for this topic (from last 48 hours)
        lookback = datetime.utcnow() - timedelta(hours=48)
        result = db.execute(text("""
            SELECT DISTINCT ci.id, ci.title, ci.published_at
            FROM content_items ci
            JOIN topic_assignments ta ON ci.id = ta.content_item_id
            WHERE ta.topic_id = :topic_id
            AND ci.published_at >= :lookback
            ORDER BY ci.published_at DESC
        """), {"topic_id": topic.id, "lookback": lookback})

        items = result.fetchall()
        content_items = db.query(ContentItem).filter(
            ContentItem.id.in_([item[0] for item in items])
        ).all()

        print(f"\n📊 Found {len(content_items)} content items for this topic")

        if len(content_items) == 0:
            print("⚠️  No content items found. Run AI processing and classification first.")
            return

        # Get or create a brief for testing
        brief = db.query(Brief).filter(Brief.date == datetime.utcnow().date()).first()
        if not brief:
            brief = Brief(
                date=datetime.utcnow().date(),
                mode="morning",
                created_at=datetime.utcnow()
            )
            db.add(brief)
            db.commit()
            db.refresh(brief)

        print(f"\n🚀 Generating topic brief (Brief ID: {brief.id})...")

        # Test the generator
        generator = TopicBriefGenerator(db)

        # Get batch size from settings
        from app.models.app_settings import AppSettings as AppSettingsModel
        from app.schemas.settings import AppSettings

        settings_record = db.query(AppSettingsModel).first()
        if settings_record:
            try:
                settings = AppSettings.model_validate(settings_record.settings_json or {})
                batch_size = settings.brief.topic_brief_batch_size
            except Exception:
                batch_size = 10
        else:
            batch_size = 10

        print(f"   Batch size: {batch_size}")
        print(f"   Items: {len(content_items)}")

        if len(content_items) > batch_size:
            print(f"   ✓ Will use hierarchical batching ({len(content_items)} > {batch_size})")
            num_batches = (len(content_items) + batch_size - 1) // batch_size
            print(f"   Expected batches: {num_batches}")
        else:
            print(f"   ✓ Will use direct generation ({len(content_items)} <= {batch_size})")

        topic_brief = await generator.generate_for_topic(
            topic=topic,
            content_items=content_items,
            brief_id=brief.id,
            timeout_seconds=120
        )

        print(f"\n✅ Topic brief generated successfully!")
        print(f"   Topic Brief ID: {topic_brief.id}")
        print(f"   Short Summary: {topic_brief.summary_short[:100]}...")
        print(f"   Full Summary: {topic_brief.summary_full[:200]}...")
        print(f"   Content References: {len(topic_brief.content_item_ids)} items")
        print(f"   Key Themes: {topic_brief.content_references.get('key_themes', [])}")
        print(f"   Significance: {topic_brief.content_references.get('significance', 'N/A')[:100]}...")

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_topic_brief_batching())
