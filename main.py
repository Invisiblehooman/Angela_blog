import werkzeug.security
from flask import Flask, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from flask import abort
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
gravatar_image = Gravatar(app=app, size=100, rating='g', default='retro', force_default=False, use_ssl=False,
                          base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Login Manager from flask import login manager
login_manager = LoginManager()
login_manager.init_app(app)
app.secret_key = '709014977d6344890bf9af06d8246266b70d498802beb43b3649bddd51fadd10'


@login_manager.user_loader
def load_user(user_id):
    # add query in order to get id from UserDetails
    return User.query.get(int(user_id))


##CONFIGURE TABLES

# noinspection PyUnresolvedReferences
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(100))

    # This will act like a List of BlogPost objects attached to each User.
    # The "author" refers to the author property in the BlogPost class.
    posts = relationship("BlogPost", back_populates="author")
    # Connecting comment table and user table with one to many relationship
    # so that it can link one user to many comments
    comments = relationship("Comment", back_populates="comment_author")


db.create_all()


# create user table in blog.db using flask sqlalchemy
# noinspection PyUnresolvedReferences
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)

    # Create Foreign Key, "users.id" the users refers to the tablename of User.
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "posts" refers to the posts property in the User class.
    author = relationship("User", back_populates="posts")

    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)

    # ***************Parent Relationship*************#
    # Now create a one to many relationship between BlogPost table and Comment table
    # This will act like a List of comments objects attached to each blogpost.
    # The "author_comment" refers to the author property in the BlogPost class.
    post_comments = relationship("Comment", back_populates="author_comment")


db.create_all()


# creating a comment table to save users comment
# noinspection PyUnresolvedReferences
class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # Create Foreign Key, "users.id" the users refers to the table name of User.
    comment_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # Create reference to the User object, the "comments" refers to the comments property in the User class.
    comment_author = relationship("User", back_populates="comments")

    # ***************Child Relationship*************#
    # Create Foreign Key, "blog_posts.id" the blog_posts refers to the table name of BlogPost.
    blogpost_comment_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    # Create reference to the BlogPost object, the "post_comments" refers to the post_comments property
    # in the User class.
    author_comment = relationship("BlogPost", back_populates="post_comments")

    text = db.Column(db.Text, nullable=False)


db.create_all()


# creating specific decorators :
# for example create admin_only decorator :
def admin_only(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # if id is not 1 then return abort with 403 error
        if current_user.id != 1:
            return abort(403)
        # otherwise, continue with route function
        return f(*args, **kwargs)

    return decorated_function


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts, loggedin=current_user.is_authenticated)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hash_and_salt_password = werkzeug.security.generate_password_hash(password=form.password.data,
                                                                          method="pbkdf2:sha256",
                                                                          salt_length=8)
        new_user = User(email=form.email.data,
                        password=hash_and_salt_password,
                        name=form.name.data
                        )
        if User.query.filter_by(email=new_user.email).first():
            flash("You have already signed with that email account. Login instead", category='danger')
            return redirect(url_for("login"))
        else:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=form, current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        # Find user by email entered.
        user = User.query.filter_by(email=email).first()

        # if no email
        if not user:
            flash("The Email doesn't exist. Try Again", category="danger")
            return redirect(url_for("login"))
        # if no password
        elif not check_password_hash(user.password, password):
            flash("Password Incorrect! Try Again.", category="danger")
            return redirect(url_for("login"))
        else:
            login_user(user)
            return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=form, current_user=current_user)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>")
def show_post(post_id):
    form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")
        new_comment = Comment(
            text=form.comment_text.data,
            comment_author=current_user,
            author_comment=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return render_template("post.html",form=form, post=requested_post, current_user=current_user)


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


@app.route("/new-post")
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
