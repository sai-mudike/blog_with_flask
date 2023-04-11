from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar
from functools import wraps




app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

#login manager
login_manager=LoginManager()
login_manager.init_app(app)
login_manager.login_view='login'
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#gravatar
gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)


##CONFIGURE TABLES

## user table
class User(UserMixin,db.Model):
    __tablename__="user_info"
    id = db.Column(db.Integer, primary_key=True)
    email=db.Column(db.String(250),nullable=False,unique=True)
    password=db.Column(db.String(250),nullable=False)
    name=db.Column(db.String(50),nullable=False)
    posts=relationship('BlogPost')
    comment=relationship('Comment',backref='user')

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author_id=db.Column(db.Integer,db.ForeignKey('user_info.id'))
    comment=relationship('Comment')

class Comment(db.Model):
    __tablename__="comments"
    id=db.Column(db.Integer,primary_key=True)
    user_id=db.Column(db.Integer,db.ForeignKey('user_info.id'))
    comment=db.Column(db.Text,nullable=False)
    blog_id=db.Column(db.Integer,db.ForeignKey('blog_posts.id'))

# with app.app_context():
#     db.create_all()


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts)


@app.route('/register',methods=['POST','GET'])
def register():
    register_form=RegisterForm()
    if register_form.validate_on_submit():
        email=register_form.email.data
        password=register_form.password.data
        name=register_form.name.data
        if User.query.filter_by(email=email).first():
            flash("Email is already registered with us, Try to login")
            return redirect(url_for('login'))
        else:
            hashed_salted_pass=generate_password_hash(password,method='pbkdf2:sha256',salt_length=8)
            new_user=User(email=email,password=hashed_salted_pass,name=name)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)

            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=register_form)


@app.route('/login',methods=['POST','GET'])
def login():
    login_form=LoginForm()
    if login_form.validate_on_submit():
        user=User.query.filter_by(email=login_form.email.data).first()
        pass_entered=login_form.password.data
        if user:
            if check_password_hash(user.password,pass_entered):
                login_user(user)
                return redirect(url_for("get_all_posts"))
            else:
                flash("Password is incorrect,Try again")
                return redirect(url_for('login'))
        else:
            flash("Email doesn't exist")
            return redirect(url_for('login'))
    return render_template("login.html",form=login_form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=["POST",'GET'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    commentform=CommentForm()
    if commentform.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment")
            return redirect(url_for('login'))
        else:
            comment=commentform.comment.data
            new_comment=Comment(comment=comment,user_id=current_user.id ,blog_id=post_id)
            db.session.add(new_comment)
            db.session.commit()
            commentform=CommentForm(formdata=None)


    return render_template("post.html", post=requested_post,form=commentform)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")

#admin only function

def admin_only(f):
    @wraps(f)
    def decorative(*args,**kwargs):
        if current_user.is_authenticated:
             if current_user.id!=1:
                return abort(403)
             else:
                 return f(*args,**kwargs)
        else:
            return abort(403)
    return decorative



@app.route("/new-post",methods=['POST','GET'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user.name,
            date=date.today().strftime("%B %d, %Y"),
            author_id=current_user.id
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


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

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))

if __name__ == "__main__":
    app.run(debug=True)
#host='0.0.0.0', port=5000
