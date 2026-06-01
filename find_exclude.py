import sqlite3
db = r'C:\dev\yannis-ai-build\labeling\labels.db'
c = sqlite3.connect(db)
print("rows mentioning EXCLUDE anywhere:")
for col in ('edge_case_reason','friction_points','unresolved_fields','decision_reasoning'):
    hits = list(c.execute(
        f"select inquiry_id, {col} from labels where {col} like '%EXCLUDE%'"))
    if hits:
        print(f"\n--- found in column: {col} ---")
        for iq, val in hits:
            print(f"  {iq}: {val!r}")
print("\ntotal label rows:", c.execute("select count(*) from labels").fetchone()[0])
print("distinct inquiries:", c.execute("select count(distinct inquiry_id) from labels").fetchone()[0])
