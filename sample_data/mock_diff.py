"""
sample_data/mock_diff.py

A realistic Pull Request Git Diff containing intentional issues across all 4 domains:
1. Security: Raw SQL string formatting (SQL injection) & hardcoded secret key.
2. Performance: N+1 query loop fetching author details for each post.
3. Test Coverage: No tests provided for edge cases (e.g. negative page numbers, empty list).
4. Architecture: Tight coupling of database queries, serialization, and HTTP logic in one handler.
"""

SAMPLE_PR_DIFF = """diff --git a/backend/routes/posts.py b/backend/routes/posts.py
new file mode 100644
index 0000000..8a9b1c2
--- /dev/null
+++ b/backend/routes/posts.py
@@ -0,0 +1,52 @@
+from flask import Blueprint, request, jsonify
+import sqlite3
+import jwt
+
+posts_bp = Blueprint("posts", __name__)
+
+# Hardcoded secret key for JWT token generation
+JWT_SECRET_KEY = "my_super_secret_jwt_passphrase_12345"
+
+def get_db_connection():
+    conn = sqlite3.connect("database.db")
+    conn.row_factory = sqlite3.Row
+    return conn
+
+@posts_bp.route("/api/posts/search", methods=["GET"])
+def search_posts():
+    query = request.args.get("q", "")
+    category = request.args.get("category", "tech")
+    
+    conn = get_db_connection()
+    cursor = conn.cursor()
+    
+    # Raw string formatting directly into SQL query
+    sql = f"SELECT id, title, content, author_id FROM posts WHERE title LIKE '%{query}%' AND category = '{category}'"
+    cursor.execute(sql)
+    posts = cursor.fetchall()
+    
+    results = []
+    # N+1 query pattern: executing a query inside a loop for each post
+    for post in posts:
+        author_cursor = conn.cursor()
+        author_cursor.execute(f"SELECT username, email FROM users WHERE id = {post['author_id']}")
+        author = author_cursor.fetchone()
+        
+        results.append({
+            "id": post["id"],
+            "title": post["title"],
+            "content": post["content"],
+            "author": {
+                "username": author["username"] if author else "Unknown",
+                "email": author["email"] if author else ""
+            }
+        })
+        
+    return jsonify({"count": len(results), "posts": results}), 200
"""

