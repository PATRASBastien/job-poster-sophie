import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from pipeline.database import stats, get_jobs

s = stats()
print("Jobs by status:", dict(s["jobs"]))
print("Applications:", dict(s["applications"]))
jobs = get_jobs("new")
print(f"\nFirst 8 new jobs ({len(jobs)} total):")
for j in jobs[:8]:
    lang = f" ⚠ {j['language_req']}" if j["language_req"] else ""
    print(f"  [{j['source']:12}] {j['title'][:50]:50} @ {j['company'][:30]}{lang}")
