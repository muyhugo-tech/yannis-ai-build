import sqlite3
db = r'C:\dev\yannis-ai-build\labeling\labels.db'
c = sqlite3.connect(db)
print("sample labeled_at values + label_id, for the 5 relabeled inquiries:")
rows = c.execute("""
  select inquiry_id, label_id, labeled_at, batch_id
  from labels
  where inquiry_id in (
    select inquiry_id from labels group by inquiry_id having count(*) > 1
  )
  order by inquiry_id, labeled_at
""")
for iq, lid, lat, batch in rows:
    print(f"  {iq}  id={lid}  labeled_at={lat!r}  batch={batch!r}")
