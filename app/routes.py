from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, g, abort
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from flask_babel import _, get_locale
from app import app, db
from app.forms import LoginForm, RegistrationForm, EditProfileForm, \
    EmptyForm, PostForm, ResetPasswordRequestForm, ResetPasswordForm, EditPostForm, \
    CommentForm, EditCommentForm, ChangePasswordForm, ChangeEmailForm, DeleteAccountForm
from app.models import User, Post, Comment, post_like, Tag, Notification
from app.email import send_password_reset_email


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()
    g.locale = str(get_locale())


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, body=form.post.data, author=current_user)
        # Process tags
        if form.tags.data:
            tag_names = [t.strip().lower() for t in form.tags.data.split(',') if t.strip()]
            for name in tag_names[:5]:  # limit to 5 tags per post
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                post.tags.append(tag)
        db.session.add(post)
        db.session.commit()
        flash(_('Your post is now live!'), 'info')
        return redirect(url_for('index'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Home'), form=form,
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/explore')
@login_required
def explore():
    page = request.args.get('page', 1, type=int)
    posts = Post.query.filter(Post.is_deleted == False).order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('explore', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('explore', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('index.html', title=_('Explore'),
                           posts=posts.items, next_url=next_url,
                           prev_url=prev_url)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash(_('Invalid username or password'), 'error')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title=_('Sign In'), form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_('Congratulations, you are now a registered user!'), 'info')
        return redirect(url_for('login'))
    return render_template('register.html', title=_('Register'), form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash(
            _('Check your email for the instructions to reset your password'), 'info')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title=_('Reset Password'), form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash(_('Your password has been reset.'), 'info')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.filter(Post.is_deleted == False).order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('user', username=user.username, page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('user', username=user.username, page=posts.prev_num) \
        if posts.has_prev else None
    form = EmptyForm()
    return render_template('user.html', user=user, posts=posts.items,
                           next_url=next_url, prev_url=prev_url, form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash(_('Your changes have been saved.'), 'info')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title=_('Edit Profile'),
                           form=form)


@app.route('/follow/<username>', methods=['POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username), 'error')
            return redirect(url_for('index'))
        if user == current_user:
            flash(_('You cannot follow yourself!'), 'error')
            return redirect(url_for('user', username=username))
        current_user.follow(user)
        db.session.commit()
        _notify(user.id, current_user, 'follow')
        db.session.commit()
        flash(_('You are following %(username)s!', username=username), 'info')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash(_('User %(username)s not found.', username=username), 'error')
            return redirect(url_for('index'))
        if user == current_user:
            flash(_('You cannot unfollow yourself!'), 'error')
            return redirect(url_for('user', username=username))
        current_user.unfollow(user)
        db.session.commit()
        flash(_('You are not following %(username)s.', username=username), 'warning')
        return redirect(url_for('user', username=username))
    else:
        return redirect(url_for('index'))


def _check_post_author(post):
    """Abort 403 if current_user is not the post author."""
    if post.user_id != current_user.id:
        abort(403)


def _notify(user_id, actor, type, post_id=None, comment_id=None):
    """Create a notification if the actor is not the recipient."""
    if user_id == actor.id:
        return  # don't notify yourself
    n = Notification(user_id=user_id, actor_id=actor.id, type=type,
                     post_id=post_id, comment_id=comment_id)
    db.session.add(n)


@app.route('/edit_post/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    _check_post_author(post)
    form = EditPostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        # Update tags
        post.tags = []
        if form.tags.data:
            tag_names = [t.strip().lower() for t in form.tags.data.split(',') if t.strip()]
            for name in tag_names[:5]:
                tag = Tag.query.filter_by(name=name).first()
                if not tag:
                    tag = Tag(name=name)
                    db.session.add(tag)
                post.tags.append(tag)
        db.session.commit()
        flash(_('Your post has been updated.'), 'info')
        return redirect(url_for('post_detail', id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.body.data = post.body
        form.tags.data = ', '.join(t.name for t in post.tags)
    return render_template('edit_post.html', title=_('Edit Post'),
                           form=form, post=post)


@app.route('/delete_post/<int:id>', methods=['POST'])
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)
    _check_post_author(post)
    post.is_deleted = True
    db.session.commit()
    flash(_('Your post has been deleted.'), 'info')
    return redirect(url_for('index'))


@app.route('/post/<int:id>')
@login_required
def post_detail(id):
    post = Post.query.get_or_404(id)
    if post.is_deleted:
        abort(404)
    top_level = post.comments.filter_by(parent_id=None) \
                              .order_by(Comment.timestamp.asc()).all()
    form = CommentForm()
    return render_template('post_detail.html', title=post.title,
                           post=post, comments=top_level, form=form)


def _check_comment_author(comment):
    """Abort 403 if current_user is not the comment author."""
    if comment.user_id != current_user.id:
        abort(403)


@app.route('/post/<int:post_id>/comment', methods=['POST'])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)
    if post.is_deleted:
        abort(404)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data, author=current_user,
                          post=post, parent_id=None)
        db.session.add(comment)
        db.session.commit()
        _notify(post.user_id, current_user, 'comment', post_id=post.id, comment_id=comment.id)
        db.session.commit()
        flash(_('Your comment has been posted.'), 'info')
    return redirect(url_for('post_detail', id=post_id))


@app.route('/post/<int:post_id>/comment/<int:comment_id>/reply', methods=['POST'])
@login_required
def add_reply(post_id, comment_id):
    post = Post.query.get_or_404(post_id)
    if post.is_deleted:
        abort(404)
    parent = Comment.query.get_or_404(comment_id)
    if parent.parent_id is not None:
        abort(400)
    form = CommentForm()
    if form.validate_on_submit():
        reply = Comment(body=form.body.data, author=current_user,
                        post=post, parent_id=parent.id)
        db.session.add(reply)
        db.session.commit()
        _notify(parent.user_id, current_user, 'reply', post_id=post.id, comment_id=reply.id)
        db.session.commit()
        flash(_('Your reply has been posted.'), 'info')
    return redirect(url_for('post_detail', id=post_id))


@app.route('/comment/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_comment(id):
    comment = Comment.query.get_or_404(id)
    _check_comment_author(comment)
    form = EditCommentForm()
    if form.validate_on_submit():
        comment.body = form.body.data
        db.session.commit()
        flash(_('Your comment has been updated.'), 'info')
        return redirect(url_for('post_detail', id=comment.post_id))
    elif request.method == 'GET':
        form.body.data = comment.body
    return render_template('edit_comment.html', title=_('Edit Comment'),
                           form=form, comment=comment)


@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'title')
    posts = []
    if q:
        if search_type == 'body':
            posts = Post.query.filter(
                Post.is_deleted == False,
                Post.body.ilike(f'%{q}%')
            ).order_by(Post.timestamp.desc()).all()
        else:
            posts = Post.query.filter(
                Post.is_deleted == False,
                Post.title.ilike(f'%{q}%')
            ).order_by(Post.timestamp.desc()).all()
    return render_template('search.html', title=_('Search'),
                           posts=posts, q=q, search_type=search_type)


@app.route('/comment/<int:id>/delete', methods=['POST'])
@login_required
def delete_comment(id):
    comment = Comment.query.get_or_404(id)
    _check_comment_author(comment)
    comment.is_deleted = True
    db.session.commit()
    flash(_('Your comment has been deleted.'), 'info')
    return redirect(url_for('post_detail', id=comment.post_id))


@app.route('/post/<int:id>/like', methods=['POST'])
@login_required
def toggle_like(id):
    post = Post.query.get_or_404(id)
    if post.is_deleted:
        abort(404)
    if post.is_liked_by(current_user):
        db.session.execute(
            post_like.delete().where(
                (post_like.c.user_id == current_user.id) &
                (post_like.c.post_id == post.id)
            )
        )
        liked = False
    else:
        db.session.execute(
            post_like.insert().values(user_id=current_user.id, post_id=post.id)
        )
        liked = True
    db.session.commit()
    # Notify post author on like
    if liked:
        _notify(post.user_id, current_user, 'like', post_id=post.id)
        db.session.commit()

    # Return JSON for AJAX requests, redirect for regular form posts
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from flask import jsonify
        return jsonify({'liked': liked, 'like_count': post.like_count})

    referrer = request.referrer
    if referrer:
        return redirect(referrer)
    return redirect(url_for('post_detail', id=id))

@app.route('/account/settings', methods=['GET'])
@login_required
def account_settings():
    pw_form = ChangePasswordForm()
    email_form = ChangeEmailForm(current_user.email)
    delete_form = DeleteAccountForm()
    return render_template('account_settings.html', title=_('Account Settings'),
                           pw_form=pw_form, email_form=email_form,
                           delete_form=delete_form)


@app.route('/account/change_password', methods=['POST'])
@login_required
def change_password():
    pw_form = ChangePasswordForm()
    if pw_form.validate_on_submit():
        if not current_user.check_password(pw_form.current_password.data):
            flash(_('Current password is incorrect.'), 'error')
        else:
            current_user.set_password(pw_form.new_password.data)
            db.session.commit()
            flash(_('Your password has been updated.'), 'info')
    else:
        for field, errors in pw_form.errors.items():
            for error in errors:
                flash(error, 'error')
    return redirect(url_for('account_settings'))


@app.route('/account/change_email', methods=['POST'])
@login_required
def change_email():
    email_form = ChangeEmailForm(current_user.email)
    if email_form.validate_on_submit():
        current_user.email = email_form.email.data
        db.session.commit()
        flash(_('Your email has been updated.'), 'info')
    else:
        for field, errors in email_form.errors.items():
            for error in errors:
                flash(error, 'error')
    return redirect(url_for('account_settings'))


@app.route('/account/delete', methods=['POST'])
@login_required
def delete_account():
    delete_form = DeleteAccountForm()
    if delete_form.validate_on_submit():
        if not current_user.check_password(delete_form.password.data):
            flash(_('Incorrect password. Account not deleted.'), 'error')
            return redirect(url_for('account_settings'))
        current_user.is_active = False
        db.session.commit()
        logout_user()
        flash(_('Your account has been deactivated.'), 'info')
        return redirect(url_for('login'))
    return redirect(url_for('account_settings'))


@app.route('/account/upload_avatar', methods=['POST'])
@login_required
def upload_avatar():
    import cloudinary
    import cloudinary.uploader
    import os
    cloudinary_url = os.environ.get('CLOUDINARY_URL')
    if not cloudinary_url:
        flash(_('Cloudinary is not configured.'), 'error')
        return redirect(url_for('account_settings'))
    cloudinary.config(cloudinary_url=cloudinary_url)

    file = request.files.get('avatar')
    if not file or file.filename == '':
        flash(_('No file selected.'), 'warning')
        return redirect(url_for('account_settings'))

    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in allowed:
        flash(_('Invalid file type. Please upload an image.'), 'error')
        return redirect(url_for('account_settings'))

    result = cloudinary.uploader.upload(
        file,
        folder='blogg-sphere/avatars',
        public_id=f'user_{current_user.id}',
        overwrite=True,
        transformation=[{'width': 200, 'height': 200, 'crop': 'fill', 'gravity': 'face'}]
    )
    current_user.avatar_url = result['secure_url']
    db.session.commit()
    flash(_('Profile picture updated.'), 'info')
    return redirect(url_for('account_settings'))


@app.route('/account/remove_avatar', methods=['POST'])
@login_required
def remove_avatar():
    current_user.avatar_url = None
    db.session.commit()
    flash(_('Profile picture removed.'), 'info')
    return redirect(url_for('account_settings'))


@app.route('/tag/<name>')
@login_required
def tag(name):
    tag = Tag.query.filter_by(name=name).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = tag.posts.filter(Post.is_deleted == False) \
                     .order_by(Post.timestamp.desc()) \
                     .paginate(page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('tag', name=name, page=posts.next_num) if posts.has_next else None
    prev_url = url_for('tag', name=name, page=posts.prev_num) if posts.has_prev else None
    return render_template('tag.html', title=f'#{name}', tag=tag,
                           posts=posts.items, next_url=next_url, prev_url=prev_url)


@app.route('/trending')
@login_required
def trending():
    from sqlalchemy import func
    # Score = like_count + comment_count, all-time
    like_counts = db.session.query(
        post_like.c.post_id,
        func.count(post_like.c.user_id).label('likes')
    ).group_by(post_like.c.post_id).subquery()

    comment_counts = db.session.query(
        Comment.post_id,
        func.count(Comment.id).label('comments')
    ).filter(Comment.is_deleted == False).group_by(Comment.post_id).subquery()

    posts = db.session.query(Post).filter(Post.is_deleted == False) \
        .outerjoin(like_counts, Post.id == like_counts.c.post_id) \
        .outerjoin(comment_counts, Post.id == comment_counts.c.post_id) \
        .order_by(
            (func.coalesce(like_counts.c.likes, 0) +
             func.coalesce(comment_counts.c.comments, 0)).desc()
        ).limit(20).all()

    return render_template('trending.html', title=_('Trending'), posts=posts)


@app.route('/notifications')
@login_required
def notifications():
    notifs = current_user.notifications.order_by(
        Notification.timestamp.desc()).limit(50).all()
    # Mark all as read
    for n in notifs:
        n.is_read = True
    db.session.commit()
    return render_template('notifications.html', title=_('Notifications'), notifications=notifs)
