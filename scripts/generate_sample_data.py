#!/usr/bin/env python3
"""
Generate synthetic clickstream data for the analytics pipeline.

Generates:
- 100,000 click events
- 10,000 sessions
- Date range: 2024-01-01 to 2024-03-21

Uses Faker for realistic data generation.
"""

from faker import Faker
from datetime import datetime, timedelta
import random
import psycopg2
from tqdm import tqdm
import uuid

# Initialize Faker
fake = Faker()
Faker.seed(42)  # Reproducible data

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="admin",
    password="admin123",
    database="clickstream",
)
conn.autocommit = True
cursor = conn.cursor()

# Configuration
NUM_CLICKS = 100000
NUM_SESSIONS = 10000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 3, 21)

# Data pools
EVENT_TYPES = ["page_view", "click", "scroll", "purchase"]
TRAFFIC_SOURCES = ["organic", "paid", "direct", "referral"]
DEVICE_TYPES = ["desktop", "mobile", "tablet"]
BROWSERS = ["Chrome", "Firefox", "Safari", "Edge"]
OS_LIST = ["Windows", "macOS", "Linux", "iOS", "Android"]

# Sample pages for e-commerce site
PAGES = [
    "https://shop.example.com/",
    "https://shop.example.com/products",
    "https://shop.example.com/products/electronics",
    "https://shop.example.com/products/clothing",
    "https://shop.example.com/cart",
    "https://shop.example.com/checkout",
    "https://shop.example.com/account",
    "https://shop.example.com/search",
    "https://shop.example.com/blog",
    "https://shop.example.com/contact",
]


def generate_user_agent():
    """Generate realistic user agent string"""
    browser = random.choice(BROWSERS)
    os = random.choice(OS_LIST)
    version = random.randint(80, 120)
    return f"Mozilla/5.0 ({os}) {browser}/{version}.0"


def generate_ip():
    """Generate random IP address"""
    return fake.ipv4()


def generate_session_id():
    """Generate unique session ID"""
    return f"sess_{uuid.uuid4().hex[:16]}"


def random_timestamp(start, end):
    """Generate random timestamp between start and end"""
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


print("🚀 Starting synthetic data generation...")
print(f"📅 Date range: {START_DATE} to {END_DATE}")
print(f"📊 Generating {NUM_CLICKS} clicks and {NUM_SESSIONS} sessions")

# Clear existing data
print("\n🧹 Clearing existing data...")
cursor.execute("TRUNCATE clicks, sessions RESTART IDENTITY CASCADE")
print("✅ Tables truncated")

# Generate sessions first (clicks reference session_id)
print("\n📝 Generating sessions...")
sessions = []
for i in tqdm(range(NUM_SESSIONS), desc="Sessions"):
    session_id = f"sess_{i:08d}"
    user_id = random.randint(1, 10000)
    started_at = random_timestamp(START_DATE, END_DATE)

    # Session duration (0-3600 seconds)
    duration = random.randint(0, 3600)
    ended_at = started_at + timedelta(seconds=duration) if duration > 0 else None

    page_views = random.randint(1, 50)
    bounce = page_views == 1
    traffic_source = random.choice(TRAFFIC_SOURCES)
    device_type = random.choice(DEVICE_TYPES)

    sessions.append(
        (
            session_id,
            user_id,
            started_at,
            ended_at,
            duration if duration > 0 else None,
            page_views,
            bounce,
            traffic_source,
            device_type,
        )
    )

# Insert sessions in batches
batch_size = 1000
for i in range(0, len(sessions), batch_size):
    batch = sessions[i : i + batch_size]
    cursor.executemany(
        """
        INSERT INTO sessions (
            session_id, user_id, started_at, ended_at,
            duration_seconds, page_views_count, bounce,
            traffic_source, device_type
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
        batch,
    )

print(f"✅ Inserted {len(sessions)} sessions")

# Generate clicks
print("\n🖱️  Generating clicks...")
clicks = []
for i in tqdm(range(NUM_CLICKS), desc="Clicks"):
    user_id = random.randint(1, 10000)

    # Pick a random session for this user
    session_idx = random.randint(0, NUM_SESSIONS - 1)
    session_id = sessions[session_idx][0]

    page_url = random.choice(PAGES)
    event_type = random.choice(EVENT_TYPES)

    # Event timestamp within session time range
    session_start = sessions[session_idx][2]
    session_end = (
        sessions[session_idx][3] if sessions[session_idx][3] else session_start
    )

    event_timestamp = random_timestamp(session_start, session_end)

    user_agent = generate_user_agent()
    ip_address = generate_ip()
    referrer_url = random.choice(PAGES) if random.random() > 0.3 else None

    created_at = event_timestamp
    updated_at = event_timestamp + timedelta(seconds=random.randint(0, 3600))

    clicks.append(
        (
            user_id,
            session_id,
            page_url,
            event_type,
            event_timestamp,
            user_agent,
            ip_address,
            referrer_url,
            created_at,
            updated_at,
        )
    )

# Insert clicks in batches
batch_size = 5000
for i in range(0, len(clicks), batch_size):
    batch = clicks[i : i + batch_size]
    cursor.executemany(
        """
        INSERT INTO clicks (
            user_id, session_id, page_url, event_type,
            event_timestamp, user_agent, ip_address,
            referrer_url, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """,
        batch,
    )

print(f"✅ Inserted {len(clicks)} clicks")

# Verify counts
cursor.execute("SELECT COUNT(*) FROM clicks")
click_count = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM sessions")
session_count = cursor.fetchone()[0]

print("\n" + "=" * 50)
print("📊 DATA GENERATION SUMMARY")
print("=" * 50)
print(f"✅ Clicks generated:    {click_count:,}")
print(f"✅ Sessions generated:  {session_count:,}")
print(f"📅 Date range:         {START_DATE.date()} to {END_DATE.date()}")
print(f"👥 Unique users:       ~10,000")
print(f"🌐 Pages tracked:      {len(PAGES)}")
print("=" * 50)

# Show sample data
print("\n📋 Sample clicks:")
cursor.execute("""
    SELECT click_id, user_id, event_type, event_timestamp, page_url
    FROM clicks
    ORDER BY RANDOM()
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  ID:{row[0]} User:{row[1]} {row[2]:12} {row[3]} {row[4][:50]}")

print("\n📋 Sample sessions:")
cursor.execute("""
    SELECT session_id, user_id, started_at, page_views_count, traffic_source, device_type
    FROM sessions
    ORDER BY RANDOM()
    LIMIT 5
""")
for row in cursor.fetchall():
    print(f"  {row[0]} User:{row[1]} {row[2]} {row[3]} views {row[4]} {row[5]}")

cursor.close()
conn.close()

print("\n✅ Data generation complete!")
print("🎯 Ready for pipeline processing")
