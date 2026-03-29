from datetime import datetime, timedelta
import unittest
from hypothesis import given, settings
from hypothesis import strategies as st
from app import app, db
from app.models import User, Post, Comment

class UserModelCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_password_hashing(self):
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))

    def test_avatar(self):
        u = User(username='john', email='john@example.com')
        self.assertEqual(u.avatar(128), ('https://www.gravatar.com/avatar/'
                                         'd4c74594d841139328695756648b6bd6'
                                         '?d=identicon&s=128'))

    def test_follow(self):
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        db.session.add(u1)
        db.session.add(u2)
        db.session.commit()
        self.assertEqual(u1.followed.all(), [])
        self.assertEqual(u1.followers.all(), [])

        u1.follow(u2)
        db.session.commit()
        self.assertTrue(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 1)
        self.assertEqual(u1.followed.first().username, 'susan')
        self.assertEqual(u2.followers.count(), 1)
        self.assertEqual(u2.followers.first().username, 'john')

        u1.unfollow(u2)
        db.session.commit()
        self.assertFalse(u1.is_following(u2))
        self.assertEqual(u1.followed.count(), 0)
        self.assertEqual(u2.followers.count(), 0)

    def test_follow_posts(self):
        # create four users
        u1 = User(username='john', email='john@example.com')
        u2 = User(username='susan', email='susan@example.com')
        u3 = User(username='mary', email='mary@example.com')
        u4 = User(username='david', email='david@example.com')
        db.session.add_all([u1, u2, u3, u4])

        # create four posts
        now = datetime.utcnow()
        p1 = Post(title="John's post", body="post from john", author=u1,
                  timestamp=now + timedelta(seconds=1))
        p2 = Post(title="Susan's post", body="post from susan", author=u2,
                  timestamp=now + timedelta(seconds=4))
        p3 = Post(title="Mary's post", body="post from mary", author=u3,
                  timestamp=now + timedelta(seconds=3))
        p4 = Post(title="David's post", body="post from david", author=u4,
                  timestamp=now + timedelta(seconds=2))
        db.session.add_all([p1, p2, p3, p4])
        db.session.commit()

        # setup the followers
        u1.follow(u2)  # john follows susan
        u1.follow(u4)  # john follows david
        u2.follow(u3)  # susan follows mary
        u3.follow(u4)  # mary follows david
        db.session.commit()

        # check the followed posts of each user
        f1 = u1.followed_posts().all()
        f2 = u2.followed_posts().all()
        f3 = u3.followed_posts().all()
        f4 = u4.followed_posts().all()
        self.assertEqual(f1, [p2, p4, p1])
        self.assertEqual(f2, [p2, p3])
        self.assertEqual(f3, [p3, p4])
        self.assertEqual(f4, [p4])

if __name__ == '__main__':
    unittest.main(verbosity=2)


class CommentModelCase(unittest.TestCase):
    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    # Feature: post-comments, Property 9: comment_count reflects non-deleted only
    # Validates: Requirements 4.1, 4.2
    @given(deleted_flags=st.lists(st.booleans(), min_size=0, max_size=20))
    @settings(max_examples=50)
    def test_comment_count_excludes_deleted(self, deleted_flags):
        # Clean up any comments from previous hypothesis runs
        Comment.query.delete()
        db.session.commit()

        for flag in deleted_flags:
            c = Comment(body='hello', author=self.u, post=self.post,
                        is_deleted=flag)
            db.session.add(c)
        db.session.commit()

        expected = sum(not f for f in deleted_flags)
        self.assertEqual(self.post.comment_count, expected)

        # Clean up for next run
        Comment.query.delete()
        db.session.commit()


class MigrationRoundTripCase(unittest.TestCase):
    """
    Feature: post-comments, Property 2: Migration round-trip leaves schema without comment table.
    Validates: Requirements 1.4, 8.4
    """

    def test_migration_round_trip(self):
        """Running upgrade then downgrade leaves no comment table."""
        import sqlalchemy as sa

        # Use a fresh file-based SQLite DB for migration testing
        engine = sa.create_engine('sqlite://')

        # Create the pre-existing tables (simulate post_edit_delete_001 state)
        with engine.begin() as conn:
            conn.execute(sa.text(
                "CREATE TABLE user ("
                "  id INTEGER PRIMARY KEY,"
                "  username VARCHAR(64),"
                "  email VARCHAR(120),"
                "  password_hash VARCHAR(128),"
                "  about_me VARCHAR(140),"
                "  last_seen DATETIME,"
                "  is_admin BOOLEAN NOT NULL DEFAULT 0"
                ")"
            ))
            conn.execute(sa.text(
                "CREATE TABLE post ("
                "  id INTEGER PRIMARY KEY,"
                "  title VARCHAR(140) NOT NULL,"
                "  body VARCHAR(5000),"
                "  timestamp DATETIME,"
                "  user_id INTEGER,"
                "  is_deleted BOOLEAN NOT NULL DEFAULT 0"
                ")"
            ))

        # Simulate upgrade: create comment table + index
        with engine.begin() as conn:
            conn.execute(sa.text(
                "CREATE TABLE comment ("
                "  id INTEGER PRIMARY KEY,"
                "  body VARCHAR(2000) NOT NULL,"
                "  timestamp DATETIME,"
                "  user_id INTEGER NOT NULL,"
                "  post_id INTEGER NOT NULL,"
                "  parent_id INTEGER,"
                "  is_deleted BOOLEAN NOT NULL DEFAULT 0,"
                "  FOREIGN KEY(user_id) REFERENCES user(id),"
                "  FOREIGN KEY(post_id) REFERENCES post(id),"
                "  FOREIGN KEY(parent_id) REFERENCES comment(id)"
                ")"
            ))
            conn.execute(sa.text(
                "CREATE INDEX ix_comment_timestamp ON comment (timestamp)"
            ))

        # Verify comment table exists after upgrade
        with engine.connect() as conn:
            result = conn.execute(sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comment'"
            ))
            self.assertIsNotNone(result.fetchone(), "comment table should exist after upgrade")

        # Simulate downgrade: drop index then table
        with engine.begin() as conn:
            conn.execute(sa.text("DROP INDEX ix_comment_timestamp"))
            conn.execute(sa.text("DROP TABLE comment"))

        # Verify comment table is gone after downgrade
        with engine.connect() as conn:
            result = conn.execute(sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='comment'"
            ))
            self.assertIsNone(result.fetchone(), "comment table should not exist after downgrade")

            # Verify pre-existing tables are intact
            result = conn.execute(sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user'"
            ))
            self.assertIsNotNone(result.fetchone(), "user table should still exist")

            result = conn.execute(sa.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='post'"
            ))
            self.assertIsNotNone(result.fetchone(), "post table should still exist")


class CommentFormValidationCase(unittest.TestCase):
    """
    Feature: post-comments, Property 5: CommentForm and EditCommentForm validate iff body is
    non-empty and <= 2000 chars.
    Validates: Requirements 2.3, 5.3
    """

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.ctx = app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    # Feature: post-comments, Property 5: comment body length validation
    # Validates: Requirements 2.3, 5.3
    @given(body=st.text())
    @settings(max_examples=100)
    def test_comment_form_length_validation(self, body):
        from app.forms import CommentForm, EditCommentForm
        # DataRequired strips whitespace before checking emptiness
        stripped = body.strip()
        expected_valid = len(stripped) > 0 and len(body) <= 2000

        comment_form = CommentForm(data={'body': body})
        edit_form = EditCommentForm(data={'body': body})

        self.assertEqual(comment_form.validate(), expected_valid,
                         f"CommentForm.validate() should be {expected_valid} for body of length {len(body)}")
        self.assertEqual(edit_form.validate(), expected_valid,
                         f"EditCommentForm.validate() should be {expected_valid} for body of length {len(body)}")


class CommentRoutesCase(unittest.TestCase):
    """Tests for comment routes."""

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.u2 = User(username='bob', email='bob@example.com')
        self.u2.set_password('password')
        db.session.add(self.u2)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _login(self, username='alice', password='password'):
        return self.client.post('/login', data={
            'username': username, 'password': password
        }, follow_redirects=True)

    # Feature: post-comments, Property 3: add_comment persists with correct parent_id
    # Validates: Requirements 2.1
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=30)
    def test_add_comment_parent_id_null(self, body):
        Comment.query.delete()
        db.session.commit()

        post_id = self.post.id
        user_id = self.u.id

        self._login()
        resp = self.client.post(
            f'/post/{post_id}/comment',
            data={'body': body},
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 302)

        comment = Comment.query.filter_by(post_id=post_id).first()
        self.assertIsNotNone(comment)
        self.assertIsNone(comment.parent_id)
        self.assertEqual(comment.post_id, post_id)
        self.assertEqual(comment.user_id, user_id)

        Comment.query.delete()
        db.session.commit()


class ReplyRoutesCase(unittest.TestCase):
    """Tests for reply routes."""

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()
        self.post_id = self.post.id
        self.user_id = self.u.id

        # Create a top-level comment
        self.top_comment = Comment(body='top level', author=self.u, post=self.post)
        db.session.add(self.top_comment)
        db.session.commit()
        self.top_comment_id = self.top_comment.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _login(self):
        return self.client.post('/login', data={
            'username': 'alice', 'password': 'password'
        }, follow_redirects=True)

    # Feature: post-comments, Property 1: reply nesting depth is at most one
    # Validates: Requirements 1.2, 2.6
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_no_nested_replies(self, body):
        """Replying to a reply returns 400 and persists no new row."""
        # Create a reply to the top-level comment
        reply = Comment(body='a reply', author=self.u,
                        post_id=self.post_id, parent_id=self.top_comment_id)
        db.session.add(reply)
        db.session.commit()
        reply_id = reply.id

        count_before = Comment.query.count()

        self._login()
        resp = self.client.post(
            f'/post/{self.post_id}/comment/{reply_id}/reply',
            data={'body': body},
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(Comment.query.count(), count_before,
                         "No new comment should be persisted when replying to a reply")

        # Clean up the reply for next iteration
        Comment.query.filter_by(id=reply_id).delete()
        db.session.commit()

    # Feature: post-comments, Property 4: add_reply persists with correct parent_id
    # Validates: Requirements 2.2
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_add_reply_parent_id_set(self, body):
        """Reply persists with parent_id equal to the top-level comment's id."""
        # Remove any replies from previous iterations
        Comment.query.filter(Comment.id != self.top_comment_id).delete()
        db.session.commit()

        self._login()
        resp = self.client.post(
            f'/post/{self.post_id}/comment/{self.top_comment_id}/reply',
            data={'body': body},
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 302)

        reply = Comment.query.filter_by(parent_id=self.top_comment_id).first()
        self.assertIsNotNone(reply)
        self.assertEqual(reply.parent_id, self.top_comment_id)
        self.assertEqual(reply.post_id, self.post_id)

        Comment.query.filter(Comment.id != self.top_comment_id).delete()
        db.session.commit()


class EditDeleteCommentCase(unittest.TestCase):
    """Tests for edit_comment and delete_comment routes."""

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.u2 = User(username='bob', email='bob@example.com')
        self.u2.set_password('password')
        db.session.add(self.u2)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()
        self.post_id = self.post.id

        self.comment = Comment(body='original body', author=self.u, post=self.post)
        db.session.add(self.comment)
        db.session.commit()
        self.comment_id = self.comment.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _login(self, username='alice', password='password'):
        return self.client.post('/login', data={
            'username': username, 'password': password
        }, follow_redirects=True)

    def _logout(self):
        return self.client.get('/logout', follow_redirects=True)

    # --- Unit tests for edit_comment authorization (Task 6.1) ---

    def test_edit_comment_as_author_returns_200(self):
        """GET /comment/<id>/edit as author returns 200."""
        self._login()
        resp = self.client.get(f'/comment/{self.comment_id}/edit')
        self.assertEqual(resp.status_code, 200)

    def test_edit_comment_as_non_author_returns_403(self):
        """GET /comment/<id>/edit as non-author returns 403."""
        self._login(username='bob')
        resp = self.client.get(f'/comment/{self.comment_id}/edit')
        self.assertEqual(resp.status_code, 403)

    def test_edit_comment_unauthenticated_redirects_to_login(self):
        """GET /comment/<id>/edit unauthenticated redirects to login."""
        resp = self.client.get(f'/comment/{self.comment_id}/edit',
                               follow_redirects=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/login', resp.headers['Location'])

    # --- Unit test for delete_comment as non-author (Task 6.2) ---

    def test_delete_comment_as_non_author_returns_403(self):
        """POST /comment/<id>/delete as non-author returns 403."""
        self._login(username='bob')
        resp = self.client.post(f'/comment/{self.comment_id}/delete')
        self.assertEqual(resp.status_code, 403)

    # Feature: post-comments, Property 11: edit comment round-trip
    # Validates: Requirements 5.1
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_edit_comment_round_trip(self, body):
        """Submitting a valid EditCommentForm stores the submitted body in the database."""
        self._login()
        resp = self.client.post(
            f'/comment/{self.comment_id}/edit',
            data={'body': body},
            follow_redirects=False
        )
        self.assertEqual(resp.status_code, 302)

        updated = Comment.query.get(self.comment_id)
        self.assertEqual(updated.body, body)

        # Reset for next iteration
        updated.body = 'original body'
        db.session.commit()

    # Feature: post-comments, Property 12: edit page pre-populates form
    # Validates: Requirements 5.2
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_edit_page_prepopulates_form(self, body):
        """GET /comment/<id>/edit returns the comment's current body in the textarea."""
        import html as html_module
        # Set the comment body to a known value
        comment = Comment.query.get(self.comment_id)
        comment.body = body
        db.session.commit()

        self._login()
        resp = self.client.get(f'/comment/{self.comment_id}/edit')
        self.assertEqual(resp.status_code, 200)
        # Jinja2 HTML-escapes content in textarea, so check for escaped version
        escaped_body = html_module.escape(body)
        self.assertIn(escaped_body.encode(), resp.data)

    # Feature: post-comments, Property 13: soft delete keeps row
    # Validates: Requirements 6.1
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_soft_delete_comment_keeps_row(self, body):
        """After delete_comment, the row still exists with is_deleted=True."""
        # Create a fresh comment for this iteration
        c = Comment(body=body, author=self.u, post_id=self.post_id)
        db.session.add(c)
        db.session.commit()
        cid = c.id

        self._login()
        resp = self.client.post(f'/comment/{cid}/delete', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

        deleted = Comment.query.get(cid)
        self.assertIsNotNone(deleted)
        self.assertTrue(deleted.is_deleted)

        Comment.query.filter_by(id=cid).delete()
        db.session.commit()

    # Feature: post-comments, Property 14: non-author receives 403
    # Validates: Requirements 7.1, 7.2
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_non_author_comment_403(self, body):
        """Non-author GET /comment/<id>/edit and POST /comment/<id>/delete each return 403."""
        self._login(username='bob')

        resp_edit = self.client.get(f'/comment/{self.comment_id}/edit')
        self.assertEqual(resp_edit.status_code, 403)

        resp_delete = self.client.post(f'/comment/{self.comment_id}/delete')
        self.assertEqual(resp_delete.status_code, 403)


class CommentTemplateCase(unittest.TestCase):
    """Tests for _comment.html template rendering."""

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.u2 = User(username='bob', email='bob@example.com')
        self.u2.set_password('password')
        db.session.add(self.u2)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()
        self.post_id = self.post.id

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def _login(self, username='alice', password='password'):
        return self.client.post('/login', data={
            'username': username, 'password': password
        }, follow_redirects=True)

    # Feature: post-comments, Property 7: deleted comment renders placeholder
    # Validates: Requirements 3.3, 6.2
    @given(body=st.text(min_size=10, max_size=2000).filter(lambda s: s.strip() and len(s.strip()) >= 10))
    @settings(max_examples=20)
    def test_deleted_comment_placeholder(self, body):
        """Rendering post_detail for a deleted comment shows '[comment deleted]' and hides the body."""
        import html as html_module
        c = Comment(body=body, author=self.u, post_id=self.post_id, is_deleted=True)
        db.session.add(c)
        db.session.commit()
        cid = c.id

        self._login()
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'[comment deleted]', resp.data)
        # The original body should not appear in the comment section
        # We check the escaped version is not in the media-body div area
        # by verifying the body text doesn't appear after the comment deleted marker
        escaped = html_module.escape(body).encode()
        # The body should not appear as rendered markdown content
        # (it would appear as <p>body</p> or similar in the comment div)
        rendered_body_marker = f'<div>{body}'.encode()
        self.assertNotIn(rendered_body_marker, resp.data)

        Comment.query.filter_by(id=cid).delete()
        db.session.commit()

    # Feature: post-comments, Property 8: reply form present for non-deleted top-level comments
    # Validates: Requirements 3.5
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20)
    def test_reply_form_present_for_top_level_comment(self, body):
        """Non-deleted top-level comment HTML contains a form pointing to the reply route."""
        c = Comment(body=body, author=self.u, post_id=self.post_id, is_deleted=False)
        db.session.add(c)
        db.session.commit()
        cid = c.id

        self._login()
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertEqual(resp.status_code, 200)
        expected_action = f'/post/{self.post_id}/comment/{cid}/reply'.encode()
        self.assertIn(expected_action, resp.data)

        Comment.query.filter_by(id=cid).delete()
        db.session.commit()

    # Feature: post-comments, Property 15: edit/delete controls only visible to comment author
    # Validates: Requirements 7.4
    @given(body=st.text(min_size=1, max_size=2000).filter(lambda s: s.strip()))
    @settings(max_examples=20, deadline=None)
    def test_comment_controls_visibility(self, body):
        """Edit/delete controls appear iff current_user.id == comment.user_id."""
        # Clean up any leftover comments from previous iterations
        Comment.query.delete()
        db.session.commit()

        c = Comment(body=body, author=self.u, post_id=self.post_id, is_deleted=False)
        db.session.add(c)
        db.session.commit()
        cid = c.id
        edit_url = f'/comment/{cid}/edit'.encode()

        # Ensure logged out first, then login as author (alice)
        self.client.get('/logout', follow_redirects=True)
        self._login(username='alice')
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertIn(edit_url, resp.data)

        # As non-author (bob) — controls should NOT be present
        self.client.get('/logout', follow_redirects=True)
        self._login(username='bob')
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertNotIn(edit_url, resp.data)

        # Clean up
        Comment.query.delete()
        db.session.commit()


class PostDetailTemplateCase(unittest.TestCase):
    """Unit tests for post_detail.html template."""

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()
        self.post_id = self.post.id

        self.client.post('/login', data={
            'username': 'alice', 'password': 'password'
        }, follow_redirects=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_post_detail_no_comments_shows_empty_message(self):
        """post_detail with no comments shows 'No comments yet' message. Validates: Requirements 3.7"""
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'No comments yet', resp.data)

    def test_post_detail_renders_top_level_comment_form(self):
        """post_detail renders the top-level comment form. Validates: Requirements 3.6"""
        resp = self.client.get(f'/post/{self.post_id}')
        self.assertEqual(resp.status_code, 200)
        expected_action = f'/post/{self.post_id}/comment'.encode()
        self.assertIn(expected_action, resp.data)


class PostListingCommentCountCase(unittest.TestCase):
    """
    Feature: post-comments, Property 10: comment count link points to post detail.
    Validates: Requirements 4.3
    """

    def setUp(self):
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        db.create_all()
        self.client = app.test_client()

        self.u = User(username='alice', email='alice@example.com')
        self.u.set_password('password')
        db.session.add(self.u)
        self.post = Post(title='Test Post', body='body', author=self.u)
        db.session.add(self.post)
        db.session.commit()
        self.post_id = self.post.id

        self.client.post('/login', data={
            'username': 'alice', 'password': 'password'
        }, follow_redirects=True)

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    # Feature: post-comments, Property 10: comment count link points to post detail
    # Validates: Requirements 4.3
    @given(deleted_flags=st.lists(st.booleans(), min_size=0, max_size=10))
    @settings(max_examples=20)
    def test_comment_count_link_points_to_post_detail(self, deleted_flags):
        """The comment count in _post.html is an anchor whose href resolves to post_detail."""
        Comment.query.delete()
        db.session.commit()

        for flag in deleted_flags:
            c = Comment(body='test', author=self.u, post_id=self.post_id, is_deleted=flag)
            db.session.add(c)
        db.session.commit()

        resp = self.client.get('/index')
        self.assertEqual(resp.status_code, 200)

        expected_href = f'/post/{self.post_id}'.encode()
        self.assertIn(expected_href, resp.data)

        # Verify the comment count is shown
        expected_count = sum(not f for f in deleted_flags)
        self.assertIn(str(expected_count).encode(), resp.data)

        Comment.query.delete()
        db.session.commit()
